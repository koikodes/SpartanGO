import asyncio

from google.transit import gtfs_realtime_pb2 as g

from app.providers.gtfs_rt import GtfsRealtimeProvider

NOW = 1_800_000_000


def make_feed() -> bytes:
    feed = g.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = NOW

    def add(eid, route, lat, lng, ts, **extra):
        e = feed.entity.add(id=eid)
        e.vehicle.trip.route_id = route
        e.vehicle.vehicle.id = eid
        e.vehicle.position.latitude = lat
        e.vehicle.position.longitude = lng
        e.vehicle.timestamp = ts
        for k, v in extra.items():
            setattr(e.vehicle, k, v)
        return e

    add("bus-7", "4012", 36.8478, -76.2622, NOW - 10, occupancy_status=g.VehiclePosition.FEW_SEATS_AVAILABLE)
    add("bus-9", "4012", 36.8466, -76.2636, NOW - 600)           # stale: skipped
    add("van-2", "9999", 36.8500, -76.2600, NOW - 5)             # unknown route: skipped
    feed.entity.add(id="alert-only")                             # no vehicle: skipped
    return feed.SerializeToString()


def test_parses_live_vehicles_and_skips_stale_or_unmapped():
    async def fetch():
        return make_feed()

    p = GtfsRealtimeProvider("https://example.test/vp", {"4012": "campus-loop"}, fetch=fetch, clock=lambda: NOW)
    vehicles = asyncio.run(p.get_vehicles())
    assert [v.id for v in vehicles] == ["bus-7"]
    v = vehicles[0]
    assert v.route_id == "campus-loop"
    assert abs(v.lat - 36.8478) < 1e-4 and abs(v.lng + 76.2622) < 1e-4
    assert v.passenger_load == 0.6


def test_requires_url():
    try:
        GtfsRealtimeProvider("", {})
    except ValueError as e:
        assert "GTFS_RT_URL" in str(e)
    else:
        raise AssertionError("expected ValueError")
