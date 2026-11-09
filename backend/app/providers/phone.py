"""Tracker mode: a phone riding the shuttle reports its own GPS position.

This gives SpartanGO real shuttle locations without touching NSU's Samsara system. A driver
(or a teammate riding the shuttle) turns on tracker mode in the app, and the phone sends a
GPS fix every few seconds to POST /tracker/position.

Privacy (NFR-03): positions live only in this process's memory. Only the latest fix per
shuttle is kept, it is never written to the database, and it is dropped once it goes stale.
"""
from typing import Optional
import time
from datetime import datetime, timezone

from ..models import Vehicle
from .base import TrackerProvider

# vehicle_id -> (latest position, received at epoch seconds)
_latest: dict[str, tuple[Vehicle, float]] = {}


def report(vehicle: Vehicle, now: Optional[float] = None) -> None:
    _latest[vehicle.id] = (vehicle, time.time() if now is None else now)


def stop(vehicle_id: str) -> None:
    _latest.pop(vehicle_id, None)


def clear() -> None:
    _latest.clear()


class PhoneProvider(TrackerProvider):
    def __init__(self, stale_after_seconds: int = 120, clock=time.time):
        self.stale_after = stale_after_seconds
        self.clock = clock

    async def get_vehicles(self) -> list[Vehicle]:
        now = self.clock()
        out = []
        for vid, (v, at) in list(_latest.items()):
            if now - at > self.stale_after:
                del _latest[vid]  # stale: forget it entirely
                continue
            out.append(v.model_copy(update={"source": "live"}))
        return out


def vehicle_from_fix(vehicle_id: str, route_id: str, lat: float, lng: float,
                     speed_mps: Optional[float], heading: Optional[float]) -> Vehicle:
    return Vehicle(id=vehicle_id, route_id=route_id, lat=lat, lng=lng, speed_mps=speed_mps, heading=heading,
                   updated_at=datetime.now(timezone.utc), source="live")
