import asyncio

import pytest

from app import main
from app.models import TrackerPingIn
from app.providers.device import STALE_AFTER_SECONDS, DeviceProvider
from tests.test_api import client, login, make_user, signup  # noqa: F401  (reuse the fixture and helpers)

PING = {"vehicle_id": "ipad-1", "route_id": "campus-loop", "lat": 36.8478, "lng": -76.2622, "speed_mps": 5.5}


@pytest.fixture()
def device(monkeypatch):
    d = DeviceProvider()
    monkeypatch.setattr(main, "provider", d)
    main._vehicle_cache.update(at=0.0, data=[])
    yield d
    main._vehicle_cache.update(at=0.0, data=[])


def test_stale_pings_drop_off():
    now = [1000.0]
    d = DeviceProvider(clock=lambda: now[0])
    d.record(TrackerPingIn(**PING))
    assert [v.id for v in asyncio.run(d.get_vehicles())] == ["ipad-1"]
    now[0] += STALE_AFTER_SECONDS + 1
    assert asyncio.run(d.get_vehicles()) == []


def test_driver_ping_shows_on_map_and_arrivals(client, device):
    make_user("driver@nsu.edu", "driver")
    h = login(client, "driver@nsu.edu")
    r = client.post("/tracker/ping", json=PING, headers=h)
    assert r.status_code == 200, r.text
    vehicles = client.get("/vehicles").json()
    assert [(v["id"], v["lat"]) for v in vehicles] == [("ipad-1", 36.8478)]
    arrivals = client.get("/routes/campus-loop/stops/fine-arts/arrivals").json()
    assert arrivals and arrivals[0]["vehicle_id"] == "ipad-1"

    assert client.post("/tracker/stop", json={"vehicle_id": "ipad-1"}, headers=h).status_code == 204
    assert client.get("/vehicles").json() == []


def test_students_cannot_send_locations(client, device):
    h = signup(client)
    assert client.post("/tracker/ping", json=PING, headers=h).status_code == 403
    assert client.post("/tracker/ping", json=PING).status_code == 401


def test_unknown_route_rejected(client, device):
    make_user("driver@nsu.edu", "driver")
    r = client.post("/tracker/ping", json={**PING, "route_id": "nope"}, headers=login(client, "driver@nsu.edu"))
    assert r.status_code == 404


def test_ping_refused_when_device_mode_off(client):
    make_user("driver@nsu.edu", "driver")
    r = client.post("/tracker/ping", json=PING, headers=login(client, "driver@nsu.edu"))
    assert r.status_code == 409 and "TRACKER_PROVIDER=device" in r.json()["detail"]
