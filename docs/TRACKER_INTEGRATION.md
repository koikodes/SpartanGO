# Connecting SpartanGO to the existing shuttle tracking system

**Short answer:** SpartanGO doesn't replace the tracking system the shuttles already use; it reads from it. The backend has one connection point, `backend/app/providers/`, and the app only ever talks to our API. Once NSU tells us which system tracks the shuttles and grants read access, connecting it is configuration (if the vendor offers a standard feed) or one small Python class (if it doesn't). No mobile-app changes are needed either way.

```
Shuttle GPS units ──► Vendor's tracking system ──► [provider adapter] ──► SpartanGO API ──► Student / driver app
 (already installed)    (already running)            read-only, polled         ETAs, rides,
                                                      every 3 s, cached         QR passes
```

## What we know so far

| Shuttle service | Who runs it | Tracking system | Source |
| --- | --- | --- | --- |
| NSU campus shuttles (East and West Campus, weekend service) | NSU (Facilities Management handles fleet) | **Unknown: not published.** Ask NSU. | [Visit Norfolk student guide](https://www.visitnorfolk.com/?p=11705), [NSU Fleet Management](https://www.nsu.edu/About/Administrative-Offices-Services/Facilities-Management/Departments/Administrative-Services/Fleet-Management) |
| Campus Connector (NSU ↔ VHS ↔ ODU), stops at Brooks Library and E.L. Hamm Fine Arts | ODU Monarch Transit | ODU tracks Monarch Transit shuttles in the **TransLoc** app | [ODU Fixed-Route Shuttle Services](https://www.odu.edu/transportation-parking-services/transportation/odu-shuttles) |

## Three ways it can work, best first

| Path | When it applies | What we do | Effort |
| --- | --- | --- | --- |
| **A. Standard feed (GTFS-Realtime)** | The vendor can give a GTFS-Realtime "VehiclePositions" URL. Many shuttle-tracking vendors support this open standard. | Already built: `providers/gtfs_rt.py`. Set the env vars below; no code. | Hours |
| **B. Vendor's own API** | The vendor only has a proprietary API (key + JSON). | Copy `providers/transloc.py` (a template), match the vendor's field names, register it in `providers/__init__.py`. | 1–3 days |
| **C. No access in time** | NSU can't share data this year, or there is no tracker. | Keep the **mock** provider for the demo (the proposal allows simulated data if it's clearly labeled), or add a driver-app GPS mode in CSC499 as a stretch. | Already works |

### Path A setup (no code)

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

Send one email to NSU Transportation / Facilities Management (Fleet Management), copying Dr. Nwosu. For the Campus Connector, ask ODU Transportation & Parking Services ([monarchtransit@odu.edu](mailto:monarchtransit@odu.edu), 757-683-4358, per the ODU page above).

1. Which system tracks NSU's shuttles (vendor and product name)?
2. Can a student capstone team get **read-only** access to live vehicle positions for a non-public prototype? Through a GTFS-Realtime feed, an API key, or a test/sandbox account?
3. The route and stop list with coordinates (a static GTFS file is ideal), plus the vendor's route IDs.
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

This page is a draft of the "Shuttle location source" decision the proposal asks for in section 10: candidate sources (A, B, C), the update model (poll every 3 s, 2-minute staleness cutoff), accuracy assumptions (ETA = distance along route ÷ observed or average speed), and the fallback (mock provider). Fill in the vendor answer once NSU replies.
