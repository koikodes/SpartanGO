"""Adapter for Samsara, the fleet-tracking platform NSU's shuttles report to.

Uses Samsara's official REST API (read-only), NOT the public live-share map link.
Docs: https://developers.samsara.com/docs/vehicle-locations-1

Setup (all values come from NSU's Samsara admin, with written approval):

    TRACKER_PROVIDER=samsara
    SAMSARA_API_TOKEN=samsara_api_...        # token with ONLY "Read Vehicle Statistics"
    SAMSARA_TAG_IDS=1234                     # optional: limit to the tag holding the shuttles
    SAMSARA_VEHICLE_ROUTE_MAP={"Shuttle 1": "campus-loop", "281474977": "campus-loop"}
    SAMSARA_DEFAULT_ROUTE=campus-loop        # optional: route for shuttles not in the map

Samsara vehicles have no "route", so SAMSARA_VEHICLE_ROUTE_MAP assigns each shuttle
(by Samsara vehicle id or by its name) to a SpartanGO route. Vehicles that are not
mapped (and no default is set) are ignored, so maintenance trucks and other fleet
vehicles never appear in the student app.

GPS updates about every 5 s while a vehicle is on; Samsara asks clients to poll no
faster than every 5 s, so this adapter caches the last response for MIN_POLL_SECONDS.
"""
import json
import time
from datetime import datetime, timezone

import httpx

from ..models import Vehicle
from .base import TrackerProvider

BASE_URL = "https://api.samsara.com"
MIN_POLL_SECONDS = 5
MAX_AGE_SECONDS = 120
MPH_TO_MPS = 0.44704


class SamsaraProvider(TrackerProvider):
    def __init__(self, token: str, vehicle_route_map: dict[str, str], default_route: str = "",
                 tag_ids: str = "", fetch=None, clock=time.time):
        if not token:
            raise ValueError("Set SAMSARA_API_TOKEN to use the Samsara provider.")
        self.token = token
        self.vehicle_route_map = vehicle_route_map
        self.default_route = default_route
        self.tag_ids = tag_ids
        self._fetch = fetch or self._http_get
        self.clock = clock
        self._cache: tuple[float, list[Vehicle]] = (0.0, [])

    @classmethod
    def from_settings(cls, s):
        return cls(s.samsara_api_token, json.loads(s.samsara_vehicle_route_map or "{}"),
                   s.samsara_default_route, s.samsara_tag_ids)

    async def _http_get(self) -> list[dict]:
        """All pages of GET /fleet/vehicles/locations (latest position per vehicle)."""
        headers = {"Authorization": f"Bearer {self.token}"}
        params: dict[str, str] = {}
        if self.tag_ids:
            params["tagIds"] = self.tag_ids
        rows: list[dict] = []
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=8) as client:
            while True:
                r = await client.get("/fleet/vehicles/locations", headers=headers, params=params)
                r.raise_for_status()
                body = r.json()
                rows.extend(body.get("data", []))
                page = body.get("pagination") or {}
                if not page.get("hasNextPage"):
                    return rows
                params["after"] = page["endCursor"]

    async def get_vehicles(self) -> list[Vehicle]:
        cached_at, cached = self._cache
        if self.clock() - cached_at < MIN_POLL_SECONDS:
            return cached
        vehicles = self.parse(await self._fetch())
        self._cache = (self.clock(), vehicles)
        return vehicles

    def parse(self, rows: list[dict]) -> list[Vehicle]:
        now = self.clock()
        out = []
        for row in rows:
            vid, name = str(row.get("id", "")), row.get("name") or ""
            route_id = self.vehicle_route_map.get(vid) or self.vehicle_route_map.get(name) or self.default_route
            loc = row.get("location") or {}
            if not route_id or "latitude" not in loc or "longitude" not in loc:
                continue
            ts = _parse_time(loc.get("time"))
            if ts is None or now - ts.timestamp() > MAX_AGE_SECONDS:
                continue  # parked / powered off: don't show as live
            speed = loc.get("speed")
            out.append(Vehicle(
                id=name or vid,
                route_id=route_id,
                lat=loc["latitude"],
                lng=loc["longitude"],
                heading=loc.get("heading"),
                speed_mps=speed * MPH_TO_MPS if isinstance(speed, (int, float)) else None,
                updated_at=ts,
            ))
        return out


def _parse_time(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
