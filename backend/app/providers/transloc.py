"""Adapter for TransLoc-style vehicle feeds.

STATUS: template. Confirm with NSU Transportation which tracking vendor the shuttles use
and how to get API access (key, agency ID, endpoint). Then adjust URL, headers and the
field mapping in `_to_vehicle` to match the real response.

The legacy TransLoc OpenAPI exposed vehicles at /vehicles.json?agencies=<id> with a
response shaped like {"data": {"<agency_id>": [ {vehicle_id, route_id, location:{lat,lng},
heading, speed (km/h), passenger_load, last_updated_on}, ... ]}}. Newer vendor APIs differ,
so treat this mapping as a starting point, not a spec.
"""
from typing import Optional
from datetime import datetime, timezone

import httpx

from ..models import Vehicle
from .base import TrackerProvider

BASE_URL = "https://transloc-api-1-2.p.rapidapi.com"


class TransLocProvider(TrackerProvider):
    def __init__(self, api_key: str, agency_id: str, route_map: Optional[dict[str, str]] = None):
        if not api_key or not agency_id:
            raise ValueError("Set TRANSLOC_API_KEY and TRANSLOC_AGENCY_ID to use the TransLoc provider.")
        self.api_key = api_key
        self.agency_id = agency_id
        # Vendor route IDs -> SpartanGO route IDs (e.g. {"4012345": "campus-loop"}).
        self.route_map = route_map or {}

    async def get_vehicles(self) -> list[Vehicle]:
        headers = {"X-RapidAPI-Key": self.api_key}
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=8) as client:
            r = await client.get("/vehicles.json", params={"agencies": self.agency_id}, headers=headers)
            r.raise_for_status()
            raw = r.json().get("data", {}).get(self.agency_id, [])
        return [v for v in (self._to_vehicle(x) for x in raw) if v]

    def _to_vehicle(self, x: dict) -> Optional[Vehicle]:
        route_id = self.route_map.get(str(x.get("route_id")))
        loc = x.get("location") or {}
        if not route_id or "lat" not in loc:
            return None
        speed_kmh = x.get("speed")
        updated = x.get("last_updated_on")
        return Vehicle(
            id=str(x.get("vehicle_id")),
            route_id=route_id,
            lat=loc["lat"],
            lng=loc["lng"],
            heading=x.get("heading"),
            speed_mps=speed_kmh / 3.6 if speed_kmh is not None else None,
            passenger_load=x.get("passenger_load"),
            updated_at=datetime.fromisoformat(updated) if updated else datetime.now(timezone.utc),
        )
