"""Geometry helpers and the ETA estimator.

ETA approach (simple, explainable for a capstone demo):
  1. Snap the shuttle to the closest point on its route path.
  2. Measure distance along the path from there to the stop (wrapping on loops).
  3. Divide by average speed (observed speed when the tracker gives one).
Swap in the vendor's own ETA feed later if it provides one.
"""
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


def eta_seconds(route: Route, vehicle: Vehicle, stop_id: str, default_speed_mps: float) -> int | None:
    """Seconds until `vehicle` reaches `stop_id`, or None if it has already passed it (one-way routes)."""
    total = sum(segment_lengths(route))
    here = position_along_route(route, vehicle.lat, vehicle.lng)
    target = stop_offset(route, stop_id)
    remaining = target - here
    if remaining < -15:  # small tolerance for GPS jitter at the stop itself
        if not route.is_loop:
            return None
        remaining += total
    remaining = max(0.0, remaining)
    speed = vehicle.speed_mps if vehicle.speed_mps and vehicle.speed_mps > 1 else default_speed_mps
    return int(round(remaining / speed))
