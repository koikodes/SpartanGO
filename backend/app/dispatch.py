"""Automatic shuttle assignment (the "Uber-like" part of SpartanGO).

Students never pick a driver. When a ride is requested, the server picks the shuttle on that
route that can reach the pickup stop soonest and still has a seat. Several riders can share
one shuttle, because that's how a shuttle works.
"""
from typing import Optional

from .geo import eta_seconds
from .models import Route, Vehicle


def choose_vehicle(route: Route, pickup_stop_id: str, vehicles: list[Vehicle], riders_on: dict[str, int],
                   capacity: int, default_speed_mps: float) -> Optional[tuple[Vehicle, int]]:
    """Return (shuttle, seconds to pickup) for the best shuttle, or None if none can take the rider.

    riders_on: vehicle id -> riders already assigned or on board."""
    best: Optional[tuple[Vehicle, int]] = None
    for v in vehicles:
        if v.route_id != route.id:
            continue
        if riders_on.get(v.id, 0) >= capacity:
            continue
        eta = eta_seconds(route, v, pickup_stop_id, default_speed_mps)
        if eta is None:  # one-way route and the shuttle already passed the stop
            continue
        if best is None or eta < best[1]:
            best = (v, eta)
    return best
