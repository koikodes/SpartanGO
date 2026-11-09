"""Tracker mode, automatic assignment, timing-table and scheduled ETAs, service alerts."""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app import db, main, push, security
from app.dispatch import choose_vehicle
from app.geo import eta_seconds, scheduled_etas
from app.main import ROUTES_BY_ID, app
from app.models import Vehicle
from app.providers import phone
from app.providers.phone import PhoneProvider
from tests.test_api import login, make_user, signup


class Empty:
    async def get_vehicles(self):
        return []


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db.configure(str(tmp_path / "test.db"))
    security._used_tokens.clear()
    phone.clear()
    main._invalidate_vehicle_cache()
    sent = []
    monkeypatch.setattr(push, "send", lambda tokens, title, body, data=None: sent.append((tokens, title, body)))
    with TestClient(app) as c:
        c.sent = sent
        yield c
    main._invalidate_vehicle_cache()


def staff(client, role):
    make_user(f"{role}@nsu.edu", role)
    return login(client, f"{role}@nsu.edu")


LIB = ROUTES_BY_ID["campus-loop"].stops[1]


# ---------- tracker mode ----------

def test_tracker_mode_shows_real_shuttle_and_hides_it_when_stopped(client, monkeypatch):
    monkeypatch.setattr(main, "provider", PhoneProvider())
    driver, student = staff(client, "driver"), signup(client)
    fix = {"vehicle_id": "Shuttle 2", "route_id": "campus-loop", "lat": LIB.lat, "lng": LIB.lng, "speed_mps": 5}
    assert client.post("/tracker/position", json=fix, headers=student).status_code == 403  # students can't fake a shuttle
    assert client.post("/tracker/position", json=fix, headers=driver).status_code == 204
    vehicles = client.get("/vehicles").json()
    assert [(v["id"], v["source"]) for v in vehicles] == [("Shuttle 2", "live")]
    arr = client.get("/routes/campus-loop/stops/library/arrivals").json()
    assert arr[0]["kind"] == "live" and arr[0]["eta_seconds"] == 0
    assert client.delete("/tracker/position/Shuttle 2", headers=driver).status_code == 204
    assert client.get("/vehicles").json() == []


def test_stale_tracker_positions_disappear():
    phone.clear()
    v = phone.vehicle_from_fix("S1", "campus-loop", LIB.lat, LIB.lng, None, None)
    phone.report(v, now=1000)
    assert asyncio.run(PhoneProvider(120, clock=lambda: 1100).get_vehicles())
    assert asyncio.run(PhoneProvider(120, clock=lambda: 1200).get_vehicles()) == []


def test_tracker_rejects_bad_input(client):
    driver = staff(client, "driver")
    bad = {"vehicle_id": "<script>", "route_id": "campus-loop", "lat": 36.8, "lng": -76.2}
    assert client.post("/tracker/position", json=bad, headers=driver).status_code == 422
    assert client.post("/tracker/position", json={**bad, "vehicle_id": "S1", "route_id": "nope"}, headers=driver).status_code == 404


# ---------- automatic assignment ----------

def _at(stop, vid="v1", route="campus-loop"):
    return Vehicle(id=vid, route_id=route, lat=stop.lat, lng=stop.lng, updated_at=datetime.now(timezone.utc))


def test_choose_vehicle_picks_soonest_with_a_seat():
    loop = ROUTES_BY_ID["campus-loop"]
    near, far = _at(loop.stops[0], "near"), _at(loop.stops[3], "far")  # stop 0 is one leg before the library
    assert choose_vehicle(loop, "library", [far, near], {}, 20, 6.7)[0].id == "near"
    assert choose_vehicle(loop, "library", [far, near], {"near": 20}, 20, 6.7)[0].id == "far"  # near is full
    assert choose_vehicle(loop, "library", [far, near], {"near": 20, "far": 20}, 20, 6.7) is None


def test_ride_waits_then_gets_assigned_when_a_shuttle_appears(client, monkeypatch):
    monkeypatch.setattr(main, "provider", PhoneProvider())
    student, driver = signup(client), staff(client, "driver")
    body = {"route_id": "campus-loop", "pickup_stop_id": "library", "dropoff_stop_id": "west-campus"}
    ride = client.post("/rides", json=body, headers=student).json()
    assert ride["status"] == "pending" and ride["vehicle_id"] is None
    client.post("/tracker/position", json={"vehicle_id": "Shuttle 1", "route_id": "campus-loop",
                                           "lat": LIB.lat, "lng": LIB.lng}, headers=driver)
    mine = client.get("/rides/mine", headers=student).json()[0]
    assert mine["status"] == "accepted" and mine["vehicle_id"] == "Shuttle 1" and mine["pickup_eta_seconds"] == 0


def test_shared_rides_go_to_the_same_shuttle(client, monkeypatch):
    monkeypatch.setattr(main, "provider", PhoneProvider())
    driver = staff(client, "driver")
    client.post("/tracker/position", json={"vehicle_id": "Shuttle 1", "route_id": "campus-loop",
                                           "lat": LIB.lat, "lng": LIB.lng}, headers=driver)
    body = {"route_id": "campus-loop", "pickup_stop_id": "library", "dropoff_stop_id": "west-campus"}
    a = client.post("/rides", json=body, headers=signup(client, "a@nsu.edu")).json()
    b = client.post("/rides", json=body, headers=signup(client, "b@nsu.edu")).json()
    assert a["vehicle_id"] == b["vehicle_id"] == "Shuttle 1"
    assert len(client.get("/rides/queue", params={"vehicle_id": "Shuttle 1"}, headers=driver).json()) == 2


# ---------- arrival times ----------

def test_timing_table_eta_adds_dwell_at_each_stop():
    loop = ROUTES_BY_ID["campus-loop"]
    at_first = _at(loop.stops[0])
    seg, dwell = loop.segment_seconds, loop.dwell_seconds
    assert eta_seconds(loop, at_first, loop.stops[1].id, 6.7) == seg[0]
    assert eta_seconds(loop, at_first, loop.stops[2].id, 6.7) == seg[0] + dwell + seg[1]


def test_scheduled_etas_follow_the_timetable():
    loop = ROUTES_BY_ID["campus-loop"]
    monday_6am = datetime(2026, 11, 9, 6, 0, tzinfo=ZoneInfo("America/New_York"))
    etas = scheduled_etas(loop, loop.stops[0].id, monday_6am, 6.7, limit=3)
    assert etas == [3600, 3600 + 15 * 60, 3600 + 30 * 60]  # first trip 07:00, then every 15 min


def test_arrivals_fall_back_to_schedule_when_no_shuttle_reports(client, monkeypatch):
    monkeypatch.setattr(main, "provider", Empty())
    arr = client.get("/routes/campus-loop/stops/library/arrivals").json()
    assert arr and all(a["kind"] == "scheduled" and a["vehicle_id"] is None for a in arr)


# ---------- service alerts ----------

def test_only_admins_post_alerts(client):
    alert = {"type": "announcement", "title": "Hi", "message": "Test"}
    assert client.post("/alerts", json=alert).status_code == 401
    assert client.post("/alerts", json=alert, headers=signup(client)).status_code == 403
    assert client.post("/alerts", json=alert, headers=staff(client, "driver")).status_code == 403
    assert client.post("/alerts", json=alert, headers=staff(client, "admin")).status_code == 201


def test_no_service_alert_blocks_rides_and_arrivals_then_ends(client):
    admin, student = staff(client, "admin"), signup(client)
    a = client.post("/alerts", json={"type": "no_service", "title": "Thanksgiving Break",
                                     "message": "No shuttles Thu-Fri.", "route_ids": ["campus-loop"]}, headers=admin).json()
    assert a["active"] and [x["id"] for x in client.get("/alerts").json()] == [a["id"]]
    body = {"route_id": "campus-loop", "pickup_stop_id": "library", "dropoff_stop_id": "west-campus"}
    r = client.post("/rides", json=body, headers=student)
    assert r.status_code == 409 and "Thanksgiving" in r.json()["detail"]
    assert client.get("/routes/campus-loop/stops/library/arrivals").json() == []
    assert client.get("/routes/campus-loop").json()["service_paused"] == "Thanksgiving Break"
    assert client.get("/routes/campus-connector").json()["service_paused"] is None  # other routes unaffected
    assert client.post(f"/alerts/{a['id']}/end", headers=admin).json()["active"] is False
    assert client.post("/rides", json=body, headers=student).status_code == 201


def test_stop_moved_alert_shows_temporary_location(client):
    admin = staff(client, "admin")
    base = {"type": "stop_moved", "title": "Library stop moved", "message": "Event tonight.", "stop_id": "library"}
    assert client.post("/alerts", json=base, headers=admin).status_code == 400  # needs the new location
    moved = {**base, "moved_to_name": "Student Center (front)", "moved_to_lat": 36.8488, "moved_to_lng": -76.2610,
             "ends_at": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()}
    assert client.post("/alerts", json=moved, headers=admin).status_code == 201
    lib = next(s for s in client.get("/routes/campus-loop").json()["stops"] if s["id"] == "library")
    assert lib["temporary"]["name"] == "Student Center (front)"


def test_scheduled_alert_is_upcoming_until_it_starts(client):
    admin = staff(client, "admin")
    start = datetime.now(timezone.utc) + timedelta(days=2)
    client.post("/alerts", json={"type": "no_service", "title": "Holiday", "message": "No service.",
                                 "starts_at": start.isoformat(), "ends_at": (start + timedelta(days=1)).isoformat()}, headers=admin)
    assert client.get("/alerts").json() == []
    upcoming = client.get("/alerts", params={"include_upcoming": True}).json()
    assert len(upcoming) == 1 and upcoming[0]["active"] is False


def test_alert_sends_push_to_registered_phones(client):
    student, admin = signup(client), staff(client, "admin")
    assert client.post("/me/push-token", json={"token": "not-a-token"}, headers=student).status_code == 422
    assert client.post("/me/push-token", json={"token": "ExponentPushToken[abc123]"}, headers=student).status_code == 204
    client.post("/alerts", json={"type": "delay", "title": "Delays", "message": "Road work on Brooks Ave."}, headers=admin)
    assert client.sent and client.sent[-1][0] == ["ExponentPushToken[abc123]"] and client.sent[-1][1] == "Delays"
