"""SpartanGO API.

Run locally:   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Docs:          http://localhost:8000/docs
"""
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import settings
from .geo import eta_seconds
from .models import (
    Arrival, LoginIn, PassOut, PassVerifyIn, PassVerifyOut, RideRequestIn, RideRequestOut,
    RideStatus, RideStatusUpdate, Role, Route, SignupIn, TokenOut, UserOut, Vehicle,
)
from .providers import get_provider
from .security import (
    check_pass, create_access_token, current_user, hash_password, issue_pass,
    require_role, verify_password,
)

ROUTES: list[Route] = [
    Route(**r) for r in json.loads((Path(__file__).parent / "data" / "routes.json").read_text())["routes"]
]
ROUTES_BY_ID = {r.id: r for r in ROUTES}

@asynccontextmanager
async def lifespan(_app):
    db.init()
    yield


app = FastAPI(title="SpartanGO API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

provider = get_provider(ROUTES)
_vehicle_cache: dict = {"at": 0.0, "data": []}
VEHICLE_CACHE_SECONDS = 3  # don't hammer the tracker vendor on every app poll


async def live_vehicles() -> list[Vehicle]:
    if time.time() - _vehicle_cache["at"] > VEHICLE_CACHE_SECONDS:
        try:
            _vehicle_cache["data"] = await provider.get_vehicles()
            _vehicle_cache["at"] = time.time()
        except Exception as exc:  # tracker down: serve last known positions instead of failing
            if not _vehicle_cache["data"]:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Tracker unavailable: {exc}")
    return _vehicle_cache["data"]


def _route_or_404(route_id: str) -> Route:
    route = ROUTES_BY_ID.get(route_id)
    if not route:
        raise HTTPException(404, "Route not found")
    return route


# ---------------- public: routes, live shuttles, arrivals ----------------

@app.get("/health")
def health():
    return {"ok": True, "tracker": settings.tracker_provider}


@app.get("/routes", response_model=list[Route])
def list_routes():
    return ROUTES


@app.get("/routes/{route_id}", response_model=Route)
def get_route(route_id: str):
    return _route_or_404(route_id)


@app.get("/vehicles", response_model=list[Vehicle])
async def list_vehicles(route_id: str | None = None):
    vehicles = await live_vehicles()
    return [v for v in vehicles if route_id is None or v.route_id == route_id]


@app.get("/routes/{route_id}/stops/{stop_id}/arrivals", response_model=list[Arrival])
async def stop_arrivals(route_id: str, stop_id: str, limit: int = Query(3, ge=1, le=10)):
    route = _route_or_404(route_id)
    if stop_id not in {s.id for s in route.stops}:
        raise HTTPException(404, "Stop not on this route")
    arrivals = []
    for v in await live_vehicles():
        if v.route_id != route_id:
            continue
        eta = eta_seconds(route, v, stop_id, settings.avg_shuttle_speed_mps)
        if eta is not None:
            arrivals.append(Arrival(stop_id=stop_id, route_id=route_id, vehicle_id=v.id, eta_seconds=eta))
    return sorted(arrivals, key=lambda a: a.eta_seconds)[:limit]


# ---------------- accounts ----------------

@app.post("/auth/signup", response_model=TokenOut, status_code=201)
def signup(body: SignupIn):
    domain = body.email.split("@")[1].lower()
    if domain not in settings.allowed_email_domains:
        raise HTTPException(400, "Use your NSU email address")
    with db.connect() as c:
        if c.execute("SELECT 1 FROM users WHERE email = ?", (body.email.lower(),)).fetchone():
            raise HTTPException(409, "An account with that email already exists")
        cur = c.execute(
            "INSERT INTO users (email, name, student_id, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
            (body.email.lower(), body.name, body.student_id, hash_password(body.password), Role.student.value, db.now_iso()),
        )
        user_id = cur.lastrowid
    return TokenOut(access_token=create_access_token(user_id, Role.student.value), role=Role.student)


@app.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn):
    with db.connect() as c:
        row = c.execute("SELECT id, password_hash, role, active FROM users WHERE email = ?", (body.email.lower(),)).fetchone()
    if not row or not row["active"] or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect")  # same message either way: no account enumeration
    return TokenOut(access_token=create_access_token(row["id"], row["role"]), role=row["role"])


@app.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(current_user)):
    return user


# ---------------- ride requests ----------------

def _ride_out(row) -> RideRequestOut:
    return RideRequestOut(**dict(row))


@app.post("/rides", response_model=RideRequestOut, status_code=201)
def request_ride(body: RideRequestIn, user: UserOut = Depends(require_role(Role.student))):
    route = _route_or_404(body.route_id)
    stop_ids = {s.id for s in route.stops}
    if body.pickup_stop_id not in stop_ids or body.dropoff_stop_id not in stop_ids:
        raise HTTPException(400, "Pickup and drop-off must be stops on this route")
    if body.pickup_stop_id == body.dropoff_stop_id:
        raise HTTPException(400, "Pickup and drop-off must be different")
    with db.connect() as c:
        open_ride = c.execute(
            "SELECT 1 FROM ride_requests WHERE user_id = ? AND status IN ('pending','accepted')", (user.id,)
        ).fetchone()
        if open_ride:
            raise HTTPException(409, "You already have an open ride request")
        cur = c.execute(
            "INSERT INTO ride_requests (user_id, route_id, pickup_stop_id, dropoff_stop_id, note, created_at) VALUES (?,?,?,?,?,?)",
            (user.id, body.route_id, body.pickup_stop_id, body.dropoff_stop_id, body.note, db.now_iso()),
        )
        row = c.execute("SELECT * FROM ride_requests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _ride_out(row)


@app.get("/rides/mine", response_model=list[RideRequestOut])
def my_rides(user: UserOut = Depends(current_user)):
    with db.connect() as c:
        rows = c.execute("SELECT * FROM ride_requests WHERE user_id = ? ORDER BY id DESC LIMIT 20", (user.id,)).fetchall()
    return [_ride_out(r) for r in rows]


@app.get("/rides/queue", response_model=list[RideRequestOut])
def ride_queue(route_id: str | None = None, _: UserOut = Depends(require_role(Role.driver, Role.admin))):
    q = "SELECT * FROM ride_requests WHERE status IN ('pending','accepted')"
    args: tuple = ()
    if route_id:
        q += " AND route_id = ?"
        args = (route_id,)
    with db.connect() as c:
        rows = c.execute(q + " ORDER BY id", args).fetchall()
    return [_ride_out(r) for r in rows]


ALLOWED_TRANSITIONS = {
    RideStatus.pending: {RideStatus.accepted, RideStatus.cancelled},
    RideStatus.accepted: {RideStatus.picked_up, RideStatus.cancelled},
    RideStatus.picked_up: {RideStatus.completed},
}


@app.patch("/rides/{ride_id}", response_model=RideRequestOut)
def update_ride(ride_id: int, body: RideStatusUpdate, user: UserOut = Depends(current_user)):
    with db.connect() as c:
        row = c.execute("SELECT * FROM ride_requests WHERE id = ?", (ride_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Ride not found")
        if user.role == Role.student:
            # students may only cancel their own request
            if row["user_id"] != user.id or body.status != RideStatus.cancelled:
                raise HTTPException(403, "You can only cancel your own ride")
        if body.status not in ALLOWED_TRANSITIONS.get(RideStatus(row["status"]), set()):
            raise HTTPException(400, f"Can't go from {row['status']} to {body.status.value}")
        c.execute("UPDATE ride_requests SET status = ? WHERE id = ?", (body.status.value, ride_id))
        row = c.execute("SELECT * FROM ride_requests WHERE id = ?", (ride_id,)).fetchone()
    return _ride_out(row)


# ---------------- QR ride pass ----------------

@app.get("/pass", response_model=PassOut)
def get_pass(user: UserOut = Depends(require_role(Role.student))):
    token, expires_in = issue_pass(user.id)
    return PassOut(token=token, expires_in=expires_in)


@app.post("/pass/verify", response_model=PassVerifyOut)
def verify_pass(body: PassVerifyIn, _: UserOut = Depends(require_role(Role.driver, Role.admin))):
    user_id, reason = check_pass(body.token)
    if user_id is None:
        return PassVerifyOut(valid=False, reason=reason)
    with db.connect() as c:
        row = c.execute("SELECT name, active FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not row["active"]:
            return PassVerifyOut(valid=False, reason="Account not active")
        c.execute("INSERT INTO boardings (user_id, vehicle_id, boarded_at) VALUES (?,?,?)", (user_id, body.vehicle_id, db.now_iso()))
    return PassVerifyOut(valid=True, name=row["name"])
