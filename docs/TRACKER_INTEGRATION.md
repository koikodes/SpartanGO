# Connecting SpartanGO to the existing shuttle tracking system

**Short answer:** NSU's shuttles report to **Samsara**, a fleet-tracking platform with an official, documented API. SpartanGO doesn't replace it; it reads from it. The Samsara adapter is already written (`backend/app/providers/samsara.py`, with tests). Once NSU's Samsara admin creates a read-only API token for the project, connecting is configuration only. No mobile-app changes are needed.

```
Samsara GPS units ──► Samsara cloud (NSU's org) ──► samsara.py adapter ──► SpartanGO API ──► Student / driver app
 (already installed     (already running;           read-only token,        ETAs, rides,
  in the shuttles)       NSU shares a live map)      polled every 5 s        QR passes
```

## What we know so far

| Shuttle service | Who runs it | Tracking system | Source |
| --- | --- | --- | --- |
| NSU campus shuttles (East and West Campus, weekend service) | NSU (Facilities Management handles fleet) | **Samsara** (NSU shares a Samsara live-map link for the shuttles) | [Visit Norfolk student guide](https://www.visitnorfolk.com/?p=11705), [NSU Fleet Management](https://www.nsu.edu/About/Administrative-Offices-Services/Facilities-Management/Departments/Administrative-Services/Fleet-Management) |
| Campus Connector (NSU ↔ VHS ↔ ODU), stops at Brooks Library and E.L. Hamm Fine Arts | ODU Monarch Transit | ODU tracks Monarch Transit shuttles in the **TransLoc** app | [ODU Fixed-Route Shuttle Services](https://www.odu.edu/transportation-parking-services/transportation/odu-shuttles) |

## The plan: Samsara API

Samsara's API returns each vehicle's latest GPS position (`GET https://api.samsara.com/fleet/vehicles/locations`). GPS updates about every 5 seconds while a vehicle is on, and Samsara asks clients to poll no faster than every 5 seconds. ([Samsara docs](https://developers.samsara.com/docs/vehicle-locations-1))

**What NSU's Samsara admin needs to do (about 5 minutes):**

1. In Samsara: **Settings → API Tokens → Add API Token**.
2. Give it **only** the **Read Vehicle Statistics** permission (no write access, no driver or safety data).
3. Optionally limit it to the tag that groups the shuttles.
4. Send the token to the project's backend owner privately (not by group chat or email thread), and tell us each shuttle's name in Samsara and which route it runs.

**What we do with it.** In `backend/.env` (never committed):

```
TRACKER_PROVIDER=samsara
SAMSARA_API_TOKEN=<token from NSU>
SAMSARA_TAG_IDS=<shuttle tag id, optional>
SAMSARA_VEHICLE_ROUTE_MAP={"Shuttle 1": "campus-loop", "Shuttle 2": "campus-loop"}
```

Then restart the API. The app's map and arrival times switch from simulated to real shuttles.

**What the adapter already handles** (covered by `tests/test_samsara.py`):
- Only vehicles you map to a route appear, so maintenance trucks and other fleet vehicles never show up in the student app.
- A shuttle whose last GPS point is older than 2 minutes (parked or powered off) is not shown as live.
- Samsara's speed in mph is converted for ETA math; heading is passed through.
- Polls at most every 5 seconds, per Samsara's guidance, no matter how many students have the app open.

**Why not use the live-map link directly?** The share link is a web page meant for people to look at, not a data feed. Pulling positions from it is scraping: it can break Samsara's terms, it can stop working whenever the page changes or the link expires, and it bypasses NSU's control over who gets the data. Use the link for what it's good for: confirming the vendor, seeing shuttle names, and comparing against our map during testing. Keep the link itself out of the repo, since anyone with it can see the fleet live.

## Other options (if the token isn't granted)

| Path | When it applies | What we do | Effort |
| --- | --- | --- | --- |
| **A. Standard feed (GTFS-Realtime)**, e.g. for ODU's Campus Connector | The vendor can give a GTFS-Realtime "VehiclePositions" URL. Many shuttle-tracking vendors support this open standard. | Already built: `providers/gtfs_rt.py`. Set the env vars below; no code. | Hours |
| **B. Vendor's own API** | The vendor only has a proprietary API (key + JSON). | Copy `providers/transloc.py` (a template), match the vendor's field names, register it in `providers/__init__.py`. | 1–3 days |
| **C. No access in time** | NSU can't share data this year, or there is no tracker. | Keep the **mock** provider for the demo (the proposal allows simulated data if it's clearly labeled), or add a driver-app GPS mode in CSC499 as a stretch. | Already works |

### GTFS-Realtime setup (no code)

In `backend/.env`:

```
TRACKER_PROVIDER=gtfs_rt
GTFS_RT_URL=<VehiclePositions URL from the vendor>
GTFS_RT_API_KEY=<only if the feed needs one>
GTFS_RT_API_KEY_HEADER=x-api-key
GTFS_RT_ROUTE_MAP={"<vendor route id>": "campus-loop", "<vendor route id>": "campus-connector"}
```

Then replace `backend/app/data/routes.json` with the official stops (the vendor's static GTFS `stops.txt` has names and coordinates). Run `pytest` and start the API; the app's map and arrival times switch to real shuttles.

What the adapter already handles: skips vehicles on routes we don't serve, skips positions older than 2 minutes so a parked or offline shuttle never shows as live, uses the vendor's speed for ETAs when present, and converts crowding data into "seats available / filling up / nearly full".

## What to ask, and whom

Send one email to whoever administers NSU's Samsara account (likely Facilities Management / Fleet Management), copying Dr. Nwosu. For the Campus Connector, ask ODU Transportation & Parking Services ([monarchtransit@odu.edu](mailto:monarchtransit@odu.edu), 757-683-4358, per the ODU page above).

1. Can the SpartanGO capstone team get a **read-only Samsara API token** (Read Vehicle Statistics only) for a non-public prototype, ending when the course ends?
2. Which Samsara vehicles are the student shuttles (names or a tag), and which route each runs?
3. The official route and stop list with coordinates and service hours.
4. Any terms of use: rate limits, attribution, whether data can be shown in a student-built app, and when access ends.
5. A contact person on the vendor side for technical questions.

## Rules we follow (from the approved proposal)

- **Approval first.** Section 22: proposal approval does not authorize access to operational university systems. Get written permission before connecting to any live feed, and keep it in `docs/`.
- **Read-only.** SpartanGO never writes to, or controls, the tracking system.
- **No scraping.** Don't pull positions from a vendor's public web map; it can break the vendor's terms and fails without warning. Use an approved feed or API, or stay on mock data.
- **Keep secrets out of the app and the repo.** API keys live only in the backend `.env` (never committed, never in the mobile app).
- **Minimize location data.** We keep only the latest position in memory for 3 seconds; we don't store location history (FR-09, section 11).
- **Label simulated data.** If the demo runs on the mock provider, say so on screen and in the presentation (section 20).

## For the Feasibility Report (D2)

This page is a draft of the "Shuttle location source" decision the proposal asks for in section 10: selected source (Samsara API, read-only token), update model (poll every 5 s, 2-minute staleness cutoff), accuracy assumptions (ETA = distance along route ÷ Samsara speed or average speed), and fallback (mock provider, clearly labeled). Record NSU's answer and the approval here once it arrives.
