import asyncio
from datetime import datetime, timezone

from app.providers.samsara import SamsaraProvider

NOW = datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc).timestamp()


def iso(seconds_ago):
    return datetime.fromtimestamp(NOW - seconds_ago, tz=timezone.utc).isoformat().replace("+00:00", "Z")


ROWS = [
    {"id": "281474977", "name": "Shuttle 1",
     "location": {"time": iso(8), "latitude": 36.8478, "longitude": -76.2622, "heading": 90, "speed": 15}},
    {"id": "281474978", "name": "Shuttle 2",
     "location": {"time": iso(3600), "latitude": 36.8466, "longitude": -76.2636, "speed": 0}},   # parked an hour
    {"id": "281474979", "name": "Maintenance Truck",
     "location": {"time": iso(4), "latitude": 36.85, "longitude": -76.26, "speed": 20}},          # not a shuttle
    {"id": "281474980", "name": "Shuttle 3"},                                                       # no location
]


def provider(**kw):
    calls = []

    async def fetch():
        calls.append(1)
        return ROWS

    p = SamsaraProvider("token", {"Shuttle 1": "campus-loop", "Shuttle 2": "campus-loop", "Shuttle 3": "campus-loop"},
                        fetch=fetch, clock=lambda: NOW, **kw)
    return p, calls


def test_only_live_mapped_shuttles_are_returned():
    p, _ = provider()
    vs = asyncio.run(p.get_vehicles())
    assert [v.id for v in vs] == ["Shuttle 1"]
    v = vs[0]
    assert v.route_id == "campus-loop" and v.heading == 90
    assert abs(v.speed_mps - 15 * 0.44704) < 1e-6


def test_default_route_includes_unmapped_vehicles():
    p, _ = provider(default_route="campus-loop")
    assert {v.id for v in asyncio.run(p.get_vehicles())} == {"Shuttle 1", "Maintenance Truck"}


def test_respects_samsara_minimum_poll_interval():
    p, calls = provider()
    asyncio.run(p.get_vehicles())
    asyncio.run(p.get_vehicles())
    assert len(calls) == 1


def test_requires_token():
    try:
        SamsaraProvider("", {})
    except ValueError as e:
        assert "SAMSARA_API_TOKEN" in str(e)
    else:
        raise AssertionError("expected ValueError")
