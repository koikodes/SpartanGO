"""SpartanGO API.

Run locally:   uvicorn app.main:app --reload --env-file .env --host 0.0.0.0 --port 8000
Docs:          http://localhost:8000/docs
"""
from typing import Optional
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from . import alerts as alert_svc
from . import db, push
from .config import settings
from .dispatch import choose_vehicle
from .geo import eta_seconds, scheduled_etas
from .models import (
    AlertIn, AlertOut, AlertType, Arrival, LoginIn, PassOut, PassVerifyIn, PassVerifyOut, PushTokenIn,
    RideRequestIn, RideRequestOut, RideStatus, RideStatusUpdate, Role, Route, SignupIn, TokenOut,
    TrackerPositionIn, UserOut, Vehicle,
)
from .providers import get_provider
from .providers import phone as phone_tracker
from .security import (
    check_pass, create_access_token, current_user, hash_password, issue_pass,
    require_role, verify_password,
)

ROUTES: list[Route] = [
    Route(**r) for r in json.loads((Path(__file__).parent / "data" / "routes.json").read_text())["routes"]
]
ROUTES_BY_ID = {r.id: r for r in ROUTES}


def seed_demo_accounts() -> None:
    """Demo driver/admin accounts for hosted demos (SEED_DEMO_ACCOUNTS=true). Passwords come from
    the environment so they are never in the repo."""
    import os
    demo = [
        ("driver@nsu.edu", "Demo Driver", "driver", os.getenv("DEMO_DRIVER_PASSWORD")),
        ("admin@nsu.edu", "Demo Admin", "admin", os.getenv("DEMO_ADMIN_PASSWORD")),
    ]
    with db.connect() as c:
        for email, name, role, pw in demo:
            if pw and not c.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                c.execute("INSERT INTO users (email, name, student_id, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
                          (email, name, "DEMO", hash_password(pw), role, db.now_iso()))


@asynccontextmanager
async def lifespan(_app):
    db.init()
    if settings.seed_demo_accounts:
        seed_demo_accounts()
    yield


app = FastAPI(title="SpartanGO API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

provider = get_provider(ROUTES)
_vehicle_cache: dict = {"at": 0.0, "data": []}
VEHICLE_CACHE_SECONDS = 3  # don't hammer the tracker vendor on every app poll


def _fresh(v: Vehicle) -> bool:
    updated = v.updated_at if v.updated_at.tzinfo else v.updated_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - updated).total_seconds() <= settings.stale_after_seconds


async def live_vehicles() -> list[Vehicle]:
    if time.time() - _vehicle_cache["at"] > VEHICLE_CACHE_SECONDS:
        try:
            _vehicle_cache["data"] = await provider.get_vehicles()
            _vehicle_cache["at"] = time.time()
        except Exception as exc:  # tracker down: serve last known positions instead of failing
            if not _vehicle_cache["data"]:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Tracker unavailable: {exc}")
    # Never show a shuttle as live once its position is older than the stale cutoff.
    return [v for v in _vehicle_cache["data"] if _fresh(v)]


def _invalidate_vehicle_cache() -> None:
    _vehicle_cache["at"] = 0.0


def _route_or_404(route_id: str) -> Route:
    route = ROUTES_BY_ID.get(route_id)
    if not route:
        raise HTTPException(404, "Route not found")
    return route


def _active_alerts() -> list[AlertOut]:
    return alert_svc.list_alerts()


# ---------------- public: routes, live shuttles, arrivals ----------------

@app.get("/health")
def health():
    return {"ok": True, "tracker": settings.tracker_provider}


@app.get("/routes", response_model=list[Route])
def list_routes():
    return alert_svc.apply_to_routes(ROUTES, _active_alerts())


@app.get("/routes/{route_id}", response_model=Route)
def get_route(route_id: str):
    _route_or_404(route_id)
    return next(r for r in alert_svc.apply_to_routes(ROUTES, _active_alerts()) if r.id == route_id)


@app.get("/vehicles", response_model=list[Vehicle])
async def list_vehicles(route_id: Optional[str] = None):
    vehicles = await live_vehicles()
    return [v for v in vehicles if route_id is None or v.route_id == route_id]


@app.get("/routes/{route_id}/stops/{stop_id}/arrivals", response_model=list[Arrival])
async def stop_arrivals(route_id: str, stop_id: str, limit: int = Query(3, ge=1, le=10)):
    route = _route_or_404(route_id)
    if stop_id not in {s.id for s in route.stops}:
        raise HTTPException(404, "Stop not on this route")
    if alert_svc.no_service_for(route_id, _active_alerts()):
        return []  # the app shows the alert instead of times
    arrivals = []
    for v in await live_vehicles():
        if v.route_id != route_id:
            continue
        eta = eta_seconds(route, v, stop_id, settings.avg_shuttle_speed_mps)
        if eta is not None:
            arrivals.append(Arrival(stop_id=stop_id, route_id=route_id, vehicle_id=v.id, eta_seconds=eta,
                                    kind="live" if v.source == "live" else "simulated"))
    if not arrivals and route.schedule:
        # No shuttle reporting right now: fall back to the official timetable, clearly labeled.
        now_local = datetime.now(ZoneInfo(settings.timezone))
        for eta in scheduled_etas(route, stop_id, now_local, settings.avg_shuttle_speed_mps, limit):
            arrivals.append(Arrival(stop_id=stop_id, route_id=route_id, vehicle_id=None, eta_seconds=eta, kind="scheduled"))
    return sorted(arrivals, key=lambda a: a.eta_seconds)[:limit]


# ---------------- tracker mode (real shuttle positions from a phone) ----------------

@app.post("/tracker/position", status_code=204)
def tracker_position(body: TrackerPositionIn, _: UserOut = Depends(require_role(Role.driver, Role.admin))):
    """A driver's phone (or a teammate riding the shuttle) reports its GPS fix. Kept in memory only."""
    _route_or_404(body.route_id)
    phone_tracker.report(phone_tracker.vehicle_from_fix(body.vehicle_id, body.route_id, body.lat, body.lng,
                                                        body.speed_mps, body.heading))
    _invalidate_vehicle_cache()


@app.delete("/tracker/position/{vehicle_id}", status_code=204)
def tracker_stop(vehicle_id: str, _: UserOut = Depends(require_role(Role.driver, Role.admin))):
    """Tracker mode turned off: the shuttle disappears from the map right away."""
    phone_tracker.stop(vehicle_id)
    _invalidate_vehicle_cache()


# ---------------- service alerts ----------------

@app.get("/alerts", response_model=list[AlertOut])
def get_alerts(include_upcoming: bool = False):
    """Active service alerts (stop moved, no service, delays). Public, like a posted notice."""
    return alert_svc.list_alerts(include_upcoming=include_upcoming)


@app.get("/alerts/all", response_model=list[AlertOut])
def get_all_alerts(_: UserOut = Depends(require_role(Role.admin))):
    return alert_svc.list_alerts(include_upcoming=True, include_ended=True)


@app.post("/alerts", response_model=AlertOut, status_code=201)
def create_alert(body: AlertIn, background: BackgroundTasks, user: UserOut = Depends(require_role(Role.admin))):
    for rid in body.route_ids:
        _route_or_404(rid)
    if body.stop_id:
        routes = [ROUTES_BY_ID[r] for r in body.route_ids] if body.route_ids else ROUTES
        if not any(body.stop_id in {s.id for s in r.stops} for r in routes):
            raise HTTPException(400, "That stop isn't on the selected routes")
    if body.type == AlertType.stop_moved:
        if not body.stop_id or body.moved_to_lat is None or body.moved_to_lng is None or not body.moved_to_name:
            raise HTTPException(400, "A moved stop needs the stop and its temporary name and location")
    now = datetime.now(timezone.utc)
    starts = body.starts_at or now
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=timezone.utc)
    ends = body.ends_at
    if ends is not None and ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    if ends is not None and ends <= starts:
        raise HTTPException(400, "The end time must be after the start time")
    with db.connect() as c:
        cur = c.execute(
            "INSERT INTO service_alerts (type, title, message, route_ids, stop_id, moved_to_name, moved_to_lat, moved_to_lng,"
            " starts_at, ends_at, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (body.type.value, body.title, body.message, json.dumps(body.route_ids), body.stop_id, body.moved_to_name,
             body.moved_to_lat, body.moved_to_lng, starts.isoformat(), ends.isoformat() if ends else None, user.id, now.isoformat()),
        )
        row = c.execute("SELECT * FROM service_alerts WHERE id = ?", (cur.lastrowid,)).fetchone()
    alert = alert_svc._row_to_alert(row, now)
    if body.notify:
        background.add_task(push.to_everyone, body.title, body.message, {"alert_id": alert.id, "type": body.type.value})
    return alert


@app.post("/alerts/{alert_id}/end", response_model=AlertOut)
def end_alert(alert_id: int, _: UserOut = Depends(require_role(Role.admin))):
    now = datetime.now(timezone.utc)
    with db.connect() as c:
        row = c.execute("SELECT * FROM service_alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Alert not found")
        c.execute("UPDATE service_alerts SET ends_at = ? WHERE id = ?", (now.isoformat(), alert_id))
        row = c.execute("SELECT * FROM service_alerts WHERE id = ?", (alert_id,)).fetchone()
    return alert_svc._row_to_alert(row, now)


# ---------------- accounts ----------------

@app.post("/auth/signup", response_model=TokenOut, status_code=201)
def signup(body: SignupIn):
    domain = body.email.split("@")[1].lower()
    if domain not in settings.allowed_email_domains:
        raise HTTPException(400, "Use your NSU email address")
    if body.accepted_terms_version != settings.terms_version:
        raise HTTPException(400, "Please review and accept the current Terms and Conditions")
    with db.connect() as c:
        if c.execute("SELECT 1 FROM users WHERE email = ?", (body.email.lower(),)).fetchone():
            raise HTTPException(409, "An account with that email already exists")
        cur = c.execute(
            "INSERT INTO users (email, name, student_id, password_hash, role, terms_version, terms_accepted_at, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (body.email.lower(), body.name, body.student_id, hash_password(body.password), Role.student.value,
             body.accepted_terms_version, db.now_iso(), db.now_iso()),
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


@app.post("/me/push-token", status_code=204)
def register_push_token(body: PushTokenIn, user: UserOut = Depends(current_user)):
    with db.connect() as c:
        c.execute("INSERT OR REPLACE INTO push_tokens (token, user_id, created_at) VALUES (?,?,?)",
                  (body.token, user.id, db.now_iso()))


# ---------------- ride requests (automatic shuttle assignment) ----------------

OPEN_STATUSES = ("pending", "accepted", "picked_up")


def _riders_on(c) -> dict[str, int]:
    rows = c.execute("SELECT vehicle_id, COUNT(*) AS n FROM ride_requests WHERE status IN ('accepted','picked_up')"
                     " AND vehicle_id IS NOT NULL GROUP BY vehicle_id").fetchall()
    return {r["vehicle_id"]: r["n"] for r in rows}


def _assign(c, ride_id: int, route: Route, pickup_stop_id: str, vehicles: list[Vehicle]) -> Optional[str]:
    choice = choose_vehicle(route, pickup_stop_id, vehicles, _riders_on(c), settings.shuttle_capacity,
                            settings.avg_shuttle_speed_mps)
    if not choice:
        return None
    vehicle, _eta = choice
    c.execute("UPDATE ride_requests SET status = 'accepted', vehicle_id = ?, assigned_at = ? WHERE id = ?",
              (vehicle.id, db.now_iso(), ride_id))
    return vehicle.id


async def _assign_waiting(background: Optional[BackgroundTasks] = None, user_id: Optional[int] = None) -> None:
    """Give a shuttle to rides still waiting (e.g. no shuttle was running when they asked),
    and move rides whose shuttle stopped reporting before pickup to another shuttle."""
    vehicles = await live_vehicles()
    live_ids = {v.id for v in vehicles}
    q = "SELECT * FROM ride_requests WHERE (status = 'pending' OR (status = 'accepted' AND (vehicle_id IS NULL OR vehicle_id NOT IN ({})))) "
    q = q.format(",".join("?" * len(live_ids)) or "''")
    args: list = list(live_ids)
    if user_id is not None:
        q += " AND user_id = ?"
        args.append(user_id)
    with db.connect() as c:
        for row in c.execute(q, args).fetchall():
            route = ROUTES_BY_ID.get(row["route_id"])
            if not route or alert_svc.no_service_for(route.id, _active_alerts()):
                continue
            assigned = _assign(c, row["id"], route, row["pickup_stop_id"], vehicles)
            if assigned and background is not None and row["status"] == "pending":
                background.add_task(push.to_user, row["user_id"], "Your shuttle is on the way",
                                    f"Shuttle {assigned} is heading to your pickup stop.", {"ride_id": row["id"]})


async def _ride_out(row, vehicles: Optional[list[Vehicle]] = None) -> RideRequestOut:
    out = RideRequestOut(**{k: row[k] for k in row.keys() if k != "assigned_at"})
    if out.vehicle_id and out.status in (RideStatus.accepted, RideStatus.picked_up):
        vehicles = vehicles if vehicles is not None else await live_vehicles()
        v = next((x for x in vehicles if x.id == out.vehicle_id), None)
        if v:
            out.vehicle = v
            if out.status == RideStatus.accepted:
                route = ROUTES_BY_ID.get(out.route_id)
                if route:
                    out.pickup_eta_seconds = eta_seconds(route, v, out.pickup_stop_id, settings.avg_shuttle_speed_mps)
    return out


@app.post("/rides", response_model=RideRequestOut, status_code=201)
async def request_ride(body: RideRequestIn, background: BackgroundTasks, user: UserOut = Depends(require_role(Role.student))):
    route = _route_or_404(body.route_id)
    stop_ids = {s.id for s in route.stops}
    if body.pickup_stop_id not in stop_ids or body.dropoff_stop_id not in stop_ids:
        raise HTTPException(400, "Pickup and drop-off must be stops on this route")
    if body.pickup_stop_id == body.dropoff_stop_id:
        raise HTTPException(400, "Pickup and drop-off must be different")
    paused = alert_svc.no_service_for(route.id, _active_alerts())
    if paused:
        raise HTTPException(409, f"No shuttle service right now: {paused.title}")
    vehicles = await live_vehicles()
    with db.connect() as c:
        open_ride = c.execute(
            f"SELECT 1 FROM ride_requests WHERE user_id = ? AND status IN {OPEN_STATUSES}", (user.id,)
        ).fetchone()
        if open_ride:
            raise HTTPException(409, "You already have an open ride request")
        cur = c.execute(
            "INSERT INTO ride_requests (user_id, route_id, pickup_stop_id, dropoff_stop_id, note, created_at) VALUES (?,?,?,?,?,?)",
            (user.id, body.route_id, body.pickup_stop_id, body.dropoff_stop_id, body.note, db.now_iso()),
        )
        _assign(c, cur.lastrowid, route, body.pickup_stop_id, vehicles)
        row = c.execute("SELECT * FROM ride_requests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return await _ride_out(row, vehicles)


@app.get("/rides/mine", response_model=list[RideRequestOut])
async def my_rides(background: BackgroundTasks, user: UserOut = Depends(current_user)):
    await _assign_waiting(background, user_id=user.id)
    vehicles = await live_vehicles()
    with db.connect() as c:
        rows = c.execute("SELECT * FROM ride_requests WHERE user_id = ? ORDER BY id DESC LIMIT 20", (user.id,)).fetchall()
    return [await _ride_out(r, vehicles) for r in rows]


@app.get("/rides/queue", response_model=list[RideRequestOut])
async def ride_queue(background: BackgroundTasks, route_id: Optional[str] = None, vehicle_id: Optional[str] = None,
                     _: UserOut = Depends(require_role(Role.driver, Role.admin))):
    """Drivers pass their shuttle's vehicle_id to see riders assigned to them, plus riders
    on their route still waiting for a shuttle."""
    await _assign_waiting(background)
    q = "SELECT * FROM ride_requests WHERE status IN ('pending','accepted','picked_up')"
    args: list = []
    if route_id:
        q += " AND route_id = ?"
        args.append(route_id)
    if vehicle_id:
        q += " AND (vehicle_id = ? OR (status = 'pending' AND vehicle_id IS NULL))"
        args.append(vehicle_id)
    vehicles = await live_vehicles()
    with db.connect() as c:
        rows = c.execute(q + " ORDER BY id", args).fetchall()
    return [await _ride_out(r, vehicles) for r in rows]


ALLOWED_TRANSITIONS = {
    RideStatus.pending: {RideStatus.accepted, RideStatus.cancelled},
    RideStatus.accepted: {RideStatus.picked_up, RideStatus.cancelled},
    RideStatus.picked_up: {RideStatus.completed},
}

STATUS_PUSH = {
    RideStatus.accepted: ("Your shuttle is on the way", "A shuttle is heading to your pickup stop."),
    RideStatus.cancelled: ("Ride cancelled", "Your ride request was cancelled."),
}


@app.patch("/rides/{ride_id}", response_model=RideRequestOut)
async def update_ride(ride_id: int, body: RideStatusUpdate, background: BackgroundTasks, user: UserOut = Depends(current_user)):
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
        vehicle_id = row["vehicle_id"]
        if body.status == RideStatus.accepted and body.vehicle_id:
            vehicle_id = body.vehicle_id  # a driver taking a waiting rider onto their shuttle
        c.execute("UPDATE ride_requests SET status = ?, vehicle_id = ? WHERE id = ?", (body.status.value, vehicle_id, ride_id))
        row = c.execute("SELECT * FROM ride_requests WHERE id = ?", (ride_id,)).fetchone()
    if user.role != Role.student and body.status in STATUS_PUSH:
        title, msg = STATUS_PUSH[body.status]
        background.add_task(push.to_user, row["user_id"], title, msg, {"ride_id": ride_id})
    return await _ride_out(row)


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
