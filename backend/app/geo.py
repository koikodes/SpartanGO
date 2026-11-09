"""Geometry helpers and the ETA estimator.

ETA approach (simple, explainable for a capstone demo):
  1. Snap the shuttle to the closest point on its route path.
  2. Measure distance along the path from there to the stop (wrapping on loops).
  3. Divide by average speed (observed speed when the tracker gives one).
Swap in the vendor's own ETA feed later if it provides one.
"""
from typing import Optional
import math

from .models import Route, Vehicle

EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def path_points(route: Route) -> list[tuple[float, float]]:
    pts = [(s.lat, s.lng) for s in route.stops]
    if route.is_loop:
        pts.append(pts[0])
    return pts


def segment_lengths(route: Route) -> list[float]:
    pts = path_points(route)
    return [haversine_m(*pts[i], *pts[i + 1]) for i in range(len(pts) - 1)]


def _project(p, a, b) -> tuple[float, float]:
    """Project p onto segment a-b in a local flat approximation.
    Returns (fraction along segment 0..1, distance from p to the projection in meters)."""
    lat0 = math.radians(a[0])
    ax, ay = 0.0, 0.0
    bx = math.radians(b[1] - a[1]) * math.cos(lat0) * EARTH_RADIUS_M
    by = math.radians(b[0] - a[0]) * EARTH_RADIUS_M
    px = math.radians(p[1] - a[1]) * math.cos(lat0) * EARTH_RADIUS_M
    py = math.radians(p[0] - a[0]) * EARTH_RADIUS_M
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    cx, cy = ax + t * dx, ay + t * dy
    return t, math.hypot(px - cx, py - cy)


def position_along_route(route: Route, lat: float, lng: float) -> float:
    """Distance in meters from the route's first stop to where the vehicle snaps onto the path."""
    pts = path_points(route)
    lengths = segment_lengths(route)
    best_offset, best_dist, travelled = 0.0, float("inf"), 0.0
    for i in range(len(pts) - 1):
        t, d = _project((lat, lng), pts[i], pts[i + 1])
        if d < best_dist:
            best_dist, best_offset = d, travelled + t * lengths[i]
        travelled += lengths[i]
    return best_offset


def stop_offset(route: Route, stop_id: str) -> float:
    lengths = segment_lengths(route)
    for i, s in enumerate(route.stops):
        if s.id == stop_id:
            return sum(lengths[:i])
    raise KeyError(stop_id)


def _has_timing_table(route: Route) -> bool:
    return bool(route.segment_seconds) and len(route.segment_seconds) == len(segment_lengths(route))


def _timed_seconds(route: Route, here: float, target: float) -> float:
    """Travel time from offset `here` to offset `target` (target >= here, may be past the end on a loop)
    using the team's measured stop-to-stop times, plus a dwell at every stop passed on the way."""
    lengths = segment_lengths(route)
    times = route.segment_seconds or []
    n, total = len(lengths), sum(lengths)
    seconds, pos, i = 0.0, here, 0
    # find the segment `here` sits in
    start = 0.0
    while i < n and start + lengths[i] < pos:
        start += lengths[i]
        i += 1
    i = min(i, n - 1)
    while pos < target - 1e-6:
        seg_len = lengths[i % n]
        seg_end = start + seg_len
        stop_at = min(seg_end, target)
        if seg_len > 0:
            seconds += times[i % n] * (stop_at - pos) / seg_len
        pos = stop_at
        if pos >= target - 1e-6:
            break
        seconds += route.dwell_seconds  # stopping at an intermediate stop
        start = seg_end
        i += 1
        if i >= n and not route.is_loop:
            break
        if i >= n and start >= total * 2:  # safety: never loop forever
            break
    return seconds


def eta_seconds(route: Route, vehicle: Vehicle, stop_id: str, default_speed_mps: float) -> Optional[int]:
    """Seconds until `vehicle` reaches `stop_id`, or None if it has already passed it (one-way routes).

    Uses the measured stop-to-stop timing table when the route has one, otherwise
    distance along the route divided by the shuttle's (or the default) speed."""
    total = sum(segment_lengths(route))
    here = position_along_route(route, vehicle.lat, vehicle.lng)
    target = stop_offset(route, stop_id)
    remaining = target - here
    if remaining < -15:  # small tolerance for GPS jitter at the stop itself
        if not route.is_loop:
            return None
        remaining += total
    remaining = max(0.0, remaining)
    if remaining <= 15:
        return 0
    if _has_timing_table(route):
        return int(round(_timed_seconds(route, here, here + remaining)))
    speed = vehicle.speed_mps if vehicle.speed_mps and vehicle.speed_mps > 1 else default_speed_mps
    return int(round(remaining / speed))


def scheduled_offset_seconds(route: Route, stop_id: str, default_speed_mps: float) -> float:
    """Seconds from a trip leaving the first stop until it reaches `stop_id`."""
    target = stop_offset(route, stop_id)
    if target == 0:
        return 0.0
    if _has_timing_table(route):
        return _timed_seconds(route, 0.0, target)
    index = [s.id for s in route.stops].index(stop_id)
    return target / default_speed_mps + route.dwell_seconds * max(0, index - 1)


def scheduled_etas(route: Route, stop_id: str, now_local, default_speed_mps: float, limit: int = 3) -> list[int]:
    """Seconds until the next scheduled trips reach `stop_id`, from the route's timetable."""
    sched = route.schedule
    if not sched:
        return []
    from datetime import datetime, timedelta
    offset = scheduled_offset_seconds(route, stop_id, default_speed_mps)
    h1, m1 = (int(x) for x in sched.first_departure.split(":"))
    h2, m2 = (int(x) for x in sched.last_departure.split(":"))
    out: list[int] = []
    for day in range(0, 8):
        d = (now_local + timedelta(days=day)).date()
        if d.weekday() not in sched.days:
            continue
        dep = datetime(d.year, d.month, d.day, h1, m1, tzinfo=now_local.tzinfo)
        last = datetime(d.year, d.month, d.day, h2, m2, tzinfo=now_local.tzinfo)
        while dep <= last:
            eta = (dep - now_local).total_seconds() + offset
            if eta >= 0:
                out.append(int(round(eta)))
                if len(out) >= limit:
                    return out
            dep += timedelta(minutes=sched.headway_minutes)
    return out
