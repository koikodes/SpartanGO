"""Service alerts: stop moved for an event, no service on a holiday, delays, announcements.

Only admins create alerts. Alerts turn on and off by themselves using their start and end
times, and every alert records who created it.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from . import db
from .models import AlertOut, AlertType, Route, TemporaryStop


def _dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _row_to_alert(row, now: datetime) -> AlertOut:
    starts, ends = _dt(row["starts_at"]), _dt(row["ends_at"])
    return AlertOut(
        id=row["id"], type=row["type"], title=row["title"], message=row["message"],
        route_ids=json.loads(row["route_ids"] or "[]"), stop_id=row["stop_id"],
        moved_to_name=row["moved_to_name"], moved_to_lat=row["moved_to_lat"], moved_to_lng=row["moved_to_lng"],
        starts_at=starts, ends_at=ends, created_at=_dt(row["created_at"]),
        active=starts <= now and (ends is None or now < ends),
    )


def list_alerts(now: Optional[datetime] = None, include_upcoming: bool = False, include_ended: bool = False) -> list[AlertOut]:
    now = now or datetime.now(timezone.utc)
    with db.connect() as c:
        rows = c.execute("SELECT * FROM service_alerts ORDER BY starts_at DESC, id DESC LIMIT 200").fetchall()
    out = []
    for r in rows:
        a = _row_to_alert(r, now)
        ended = a.ends_at is not None and a.ends_at <= now
        upcoming = a.starts_at > now
        if a.active or (include_upcoming and upcoming) or (include_ended and ended):
            out.append(a)
    return out


def applies_to(alert: AlertOut, route_id: str) -> bool:
    return not alert.route_ids or route_id in alert.route_ids


def no_service_for(route_id: str, active: list[AlertOut]) -> Optional[AlertOut]:
    for a in active:
        if a.type == AlertType.no_service and applies_to(a, route_id):
            return a
    return None


def apply_to_routes(routes: list[Route], active: list[AlertOut]) -> list[Route]:
    """Copy of the routes with moved stops and paused service marked, for the app to display."""
    out = []
    for r in routes:
        stops = []
        for s in r.stops:
            moved = next((a for a in active if a.type == AlertType.stop_moved and a.stop_id == s.id and applies_to(a, r.id)
                          and a.moved_to_lat is not None and a.moved_to_lng is not None), None)
            if moved:
                s = s.model_copy(update={"temporary": TemporaryStop(
                    name=moved.moved_to_name or "Temporary stop", lat=moved.moved_to_lat, lng=moved.moved_to_lng,
                    alert_id=moved.id, until=moved.ends_at)})
            stops.append(s)
        paused = no_service_for(r.id, active)
        out.append(r.model_copy(update={"stops": stops, "service_paused": paused.title if paused else None}))
    return out
