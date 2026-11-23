"""Live locations sent by a phone or tablet riding the shuttle (the driver app's Track screen).

Use this while NSU's Samsara feed isn't available: put a device running SpartanGO (logged in
as a driver or admin) on the shuttle, open the Track tab, and it posts its GPS position to
POST /tracker/ping every few seconds. The real drivers don't need to install anything.

Privacy (proposal FR-09): only the latest position per shuttle is kept, in memory. Nothing
is written to the database, and a shuttle disappears once its last ping is older than
STALE_AFTER_SECONDS (tracker closed, screen locked, or out of signal).
"""
import time
from datetime import datetime, timezone

from ..models import TrackerPingIn, Vehicle
from .base import TrackerProvider

STALE_AFTER_SECONDS = 120  # same 2-minute cutoff the Samsara and GTFS-RT adapters use


class DeviceProvider(TrackerProvider):
    def __init__(self, clock=time.time):
        self.clock = clock
        self._latest: dict[str, Vehicle] = {}

    def record(self, ping: TrackerPingIn) -> Vehicle:
        vehicle = Vehicle(
            id=ping.vehicle_id,
            route_id=ping.route_id,
            lat=ping.lat,
            lng=ping.lng,
            heading=ping.heading,
            speed_mps=ping.speed_mps,
            updated_at=datetime.fromtimestamp(self.clock(), tz=timezone.utc),
        )
        self._latest[ping.vehicle_id] = vehicle
        return vehicle

    def stop(self, vehicle_id: str) -> None:
        self._latest.pop(vehicle_id, None)

    async def get_vehicles(self) -> list[Vehicle]:
        cutoff = self.clock() - STALE_AFTER_SECONDS
        for vid, v in list(self._latest.items()):
            if v.updated_at.timestamp() < cutoff:
                del self._latest[vid]
        return list(self._latest.values())
