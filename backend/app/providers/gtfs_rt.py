"""Adapter for GTFS-Realtime VehiclePositions feeds.

GTFS-Realtime is the open standard for live transit data. Many shuttle tracking
vendors can export it, so if NSU's tracker offers a GTFS-RT "VehiclePositions" URL,
this adapter connects to it with configuration only (no code changes):

    TRACKER_PROVIDER=gtfs_rt
    GTFS_RT_URL=https://<vendor>/.../vehiclepositions      # from NSU / the vendor
    GTFS_RT_API_KEY=...                                     # only if the feed needs one
    GTFS_RT_API_KEY_HEADER=x-api-key                        # header name the vendor expects
    GTFS_RT_ROUTE_MAP={"4012345": "campus-loop", "4012346": "campus-connector"}

GTFS_RT_ROUTE_MAP maps the vendor's route ids to SpartanGO route ids in data/routes.json.
Vehicles on routes not in the map, without a position, or older than MAX_AGE_SECONDS
are skipped, so the app never shows a stale or unknown shuttle as live.
"""
from typing import Optional
import json
import time
from datetime import datetime, timezone

import httpx
from google.transit import gtfs_realtime_pb2

from ..models import Vehicle
from .base import TrackerProvider

MAX_AGE_SECONDS = 120


class GtfsRealtimeProvider(TrackerProvider):
    def __init__(self, url: str, route_map: dict[str, str], api_key: str = "", api_key_header: str = "x-api-key",
                 fetch=None, clock=time.time):
        if not url:
            raise ValueError("Set GTFS_RT_URL to use the GTFS-Realtime provider.")
        self.url = url
        self.route_map = route_map
        self.headers = {api_key_header: api_key} if api_key else {}
        self._fetch = fetch or self._http_get
        self.clock = clock

    @classmethod
    def from_settings(cls, s):
        return cls(s.gtfs_rt_url, json.loads(s.gtfs_rt_route_map or "{}"), s.gtfs_rt_api_key, s.gtfs_rt_api_key_header)

    async def _http_get(self) -> bytes:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(self.url, headers=self.headers)
            r.raise_for_status()
            return r.content

    async def get_vehicles(self) -> list[Vehicle]:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(await self._fetch())
        return self.parse(feed)

    def parse(self, feed) -> list[Vehicle]:
        now = self.clock()
        out = []
        for entity in feed.entity:
            if not entity.HasField("vehicle"):
                continue
            vp = entity.vehicle
            route_id = self.route_map.get(vp.trip.route_id)
            if not route_id or not vp.HasField("position"):
                continue
            ts = vp.timestamp or feed.header.timestamp or int(now)
            if now - ts > MAX_AGE_SECONDS:
                continue
            pos = vp.position
            out.append(Vehicle(
                id=vp.vehicle.id or vp.vehicle.label or entity.id,
                route_id=route_id,
                lat=pos.latitude,
                lng=pos.longitude,
                heading=pos.bearing if pos.HasField("bearing") else None,
                speed_mps=pos.speed if pos.HasField("speed") else None,
                passenger_load=_occupancy_to_load(vp),
                updated_at=datetime.fromtimestamp(ts, tz=timezone.utc),
            ))
        return out


def _occupancy_to_load(vp) -> Optional[float]:
    if vp.HasField("occupancy_percentage"):
        return max(0.0, min(1.0, vp.occupancy_percentage / 100))
    if vp.HasField("occupancy_status"):
        S = gtfs_realtime_pb2.VehiclePosition
        return {
            S.EMPTY: 0.0,
            S.MANY_SEATS_AVAILABLE: 0.25,
            S.FEW_SEATS_AVAILABLE: 0.6,
            S.STANDING_ROOM_ONLY: 0.85,
            S.CRUSHED_STANDING_ROOM_ONLY: 0.95,
            S.FULL: 1.0,
        }.get(vp.occupancy_status)
    return None
