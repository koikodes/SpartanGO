import pytest
from fastapi.testclient import TestClient

from app import db, security
from app.config import settings
from app.geo import eta_seconds
from app.main import ROUTES_BY_ID, app
from app.models import Vehicle


@pytest.fixture()
def client(tmp_path):
    db.configure(str(tmp_path / "test.db"))
    security._used_tokens.clear()
    with TestClient(app) as c:
        yield c


def make_user(email, role):
    with db.connect() as c:
        c.execute(
            "INSERT INTO users (email, name, student_id, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
            (email, role.title(), "X1", security.hash_password("password123"), role, db.now_iso()),
        )


def signup(client, email="koi@spartans.nsu.edu"):
    r = client.post("/auth/signup", json={"email": email, "password": "password123", "name": "Koi", "student_id": "123456",
                                          "accepted_terms_version": settings.terms_version})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def login(client, email):
    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_routes_and_vehicles(client):
    routes = client.get("/routes").json()
    assert {r["id"] for r in routes} == {"campus-loop", "campus-connector"}
    vehicles = client.get("/vehicles", params={"route_id": "campus-loop"}).json()
    assert len(vehicles) == 2 and all(v["route_id"] == "campus-loop" for v in vehicles)


def test_arrivals_sorted(client):
    arr = client.get("/routes/campus-loop/stops/library/arrivals").json()
    assert arr and arr == sorted(arr, key=lambda a: a["eta_seconds"])


def test_eta_on_loop_wraps_and_one_way_returns_none():
    loop = ROUTES_BY_ID["campus-loop"]
    s0, s1 = loop.stops[0], loop.stops[1]
    at_stop1 = Vehicle(id="v", route_id=loop.id, lat=s1.lat, lng=s1.lng, updated_at="2026-01-01T00:00:00Z")
    assert eta_seconds(loop, at_stop1, s1.id, 6.7) == 0
    assert eta_seconds(loop, at_stop1, s0.id, 6.7) > 0  # must go around the loop
    line = ROUTES_BY_ID["campus-connector"]
    at_end = Vehicle(id="v", route_id=line.id, lat=line.stops[-1].lat, lng=line.stops[-1].lng, updated_at="2026-01-01T00:00:00Z")
    assert eta_seconds(line, at_end, line.stops[0].id, 6.7) is None


def test_signup_requires_nsu_email(client):
    r = client.post("/auth/signup", json={"email": "x@gmail.com", "password": "password123", "name": "X", "student_id": "1234",
                                          "accepted_terms_version": settings.terms_version})
    assert r.status_code == 400


def test_signup_requires_current_terms(client):
    base = {"email": "t@spartans.nsu.edu", "password": "password123", "name": "T", "student_id": "1234"}
    assert client.post("/auth/signup", json=base).status_code == 422                                      # not accepted
    assert client.post("/auth/signup", json={**base, "accepted_terms_version": "2000-01-01"}).status_code == 400  # outdated
    assert client.post("/auth/signup", json={**base, "accepted_terms_version": settings.terms_version}).status_code == 201
    with db.connect() as c:
        row = c.execute("SELECT terms_version, terms_accepted_at FROM users WHERE email = ?", (base["email"],)).fetchone()
    assert row["terms_version"] == settings.terms_version and row["terms_accepted_at"]


def test_login_wrong_password_generic_error(client):
    signup(client)
    r = client.post("/auth/login", json={"email": "koi@spartans.nsu.edu", "password": "nope-nope"})
    assert r.status_code == 401
    r2 = client.post("/auth/login", json={"email": "nobody@nsu.edu", "password": "nope-nope"})
    assert r2.json() == r.json()


def test_ride_request_flow(client):
    student = signup(client)
    make_user("driver@nsu.edu", "driver")
    driver = login(client, "driver@nsu.edu")

    body = {"route_id": "campus-loop", "pickup_stop_id": "library", "dropoff_stop_id": "west-campus"}
    ride = client.post("/rides", json=body, headers=student).json()
    assert ride["status"] == "pending"
    assert client.post("/rides", json=body, headers=student).status_code == 409  # one open ride at a time

    # students can't see the driver queue or accept rides
    assert client.get("/rides/queue", headers=student).status_code == 403
    assert client.patch(f"/rides/{ride['id']}", json={"status": "accepted"}, headers=student).status_code == 403

    assert len(client.get("/rides/queue", headers=driver).json()) == 1
    for s in ["accepted", "picked_up", "completed"]:
        assert client.patch(f"/rides/{ride['id']}", json={"status": s}, headers=driver).json()["status"] == s
    assert client.patch(f"/rides/{ride['id']}", json={"status": "pending"}, headers=driver).status_code == 400


def test_qr_pass_valid_once_and_tamper_proof(client):
    student = signup(client)
    make_user("driver@nsu.edu", "driver")
    driver = login(client, "driver@nsu.edu")

    token = client.get("/pass", headers=student).json()["token"]
    assert client.post("/pass/verify", json={"token": token}, headers=driver).json() == {"valid": True, "name": "Koi", "reason": None}
    again = client.post("/pass/verify", json={"token": token}, headers=driver).json()
    assert again["valid"] is False and "already" in again["reason"]

    uid, window, sig = client.get("/pass", headers=student).json()["token"].split(".")
    forged = f"{int(uid) + 1}.{window}.{sig}"
    assert client.post("/pass/verify", json={"token": forged}, headers=driver).json()["valid"] is False
    assert client.post("/pass/verify", json={"token": token}, headers=student).status_code == 403


def test_pass_expires():
    token, _ = security.issue_pass(7, now=1_000_000)
    assert security.check_pass(token, now=1_000_000 + 300)[1].startswith("Pass expired")
