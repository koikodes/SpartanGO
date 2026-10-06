"""Simulated shuttles that drive along each route. Use for development and demos
until NSU grants access to the real tracker feed."""
import time
from datetime import datetime, timezone

from ..geo import path_points, segment_lengths
from ..models import Route, Vehicle
from .base import TrackerProvider

SIM_SPEED_MPS = 7.0


class MockProvider(TrackerProvider):
    def __init__(self, routes: list[Route], vehicles_per_route: int = 2, clock=time.time):
        self.routes = routes
        self.vehicles_per_route = vehicles_per_route
        self.clock = clock

    def _position(self, route: Route, distance: float) -> tuple[float, float]:
        pts = path_points(route)
        lengths = segment_lengths(route)
        total = sum(lengths)
        if route.is_loop:
            distance %= total
        else:  # out-and-back: ping-pong along the line
            cycle = distance % (2 * total)
            distance = cycle if cycle <= total else 2 * total - cycle
        for i, seg in enumerate(lengths):
            if distance <= seg or i == len(lengths) - 1:
                t = 0 if seg == 0 else min(1.0, distance / seg)
                (a_lat, a_lng), (b_lat, b_lng) = pts[i], pts[i + 1]
                return a_lat + t * (b_lat - a_lat), a_lng + t * (b_lng - a_lng)
            distance -= seg
        return pts[-1]

    async def get_vehicles(self) -> list[Vehicle]:
        now = self.clock()
        out = []
        for route in self.routes:
            total = sum(segment_lengths(route))
            for n in range(self.vehicles_per_route):
                spacing = total / self.vehicles_per_route
                lat, lng = self._position(route, now * SIM_SPEED_MPS + n * spacing)
                out.append(Vehicle(
                    id=f"{route.id}-{n + 1}",
                    route_id=route.id,
                    lat=lat,
                    lng=lng,
                    speed_mps=SIM_SPEED_MPS,
                    passenger_load=round(((int(now) // 60 + n * 3) % 10) / 10, 1),
                    updated_at=datetime.fromtimestamp(now, tz=timezone.utc),
                ))
        return out
