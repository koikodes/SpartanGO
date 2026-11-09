# SpartanGO

Capstone prototype of a campus shuttle app for NSU: live shuttle map, arrival times with alerts, Uber-style ride requests (the closest shuttle with a seat is assigned automatically), a short-lived QR boarding code a driver can check, and service alerts for moved stops and holidays. The QR code is a prototype credential, not an official NSU ID.

**Final demo:** real shuttles come from *tracker mode* (a phone riding the shuttle shares its GPS), so no access to NSU's Samsara system is needed. See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for hosting, setup and the demo script.

> **Status (CSC498, fall):** this code is a disposable *feasibility prototype*. Per the approved proposal, fall produces the design baseline (D1-D10) and spring (CSC499) builds it. Use this code as evidence for the Feasibility Report (D2), not as the production app.

CSC capstone · Team: Tijaina Hill, Dennis Jordan, Jaden Lunsford, Ty'vaughn Daniels, Koi Williamson · Advisor: Dr. Nwosu

```
spartango/
├── docs/               Proposal (D1), project plan, diagrams, and CSC498 deliverables
├── backend/            Python FastAPI API (routes, live shuttles, ETAs, rides, passes)
│   ├── app/
│   │   ├── main.py         all API endpoints
│   │   ├── providers/      where live shuttle locations come from (phone tracker mode, mock, Samsara with approval)
│   │   ├── geo.py          ETA math (measured stop-to-stop times, timetable fallback)
│   │   ├── dispatch.py     automatic shuttle assignment for ride requests
│   │   ├── alerts.py       service alerts (stop moved, no service, delay, announcement)
│   │   ├── push.py         push notifications through Expo
│   │   ├── security.py     passwords, login tokens, QR pass signing
│   │   ├── db.py           SQLite tables
│   │   └── data/routes.json  routes + stops (PLACEHOLDER coordinates, replace)
│   ├── tests/          pytest suite (run before every merge)
│   └── seed.py         creates demo driver/admin accounts
└── mobile/             Expo (React Native + TypeScript) app for iOS and Android
    └── src/
        ├── app/            screens (Expo Router: every file is a screen)
        │   ├── (auth)/     login, signup
        │   ├── (tabs)/     map, arrivals, ride, pass  |  driver: queue, scan, drive (tracker mode)
        │   ├── alerts.tsx        service alerts for everyone
        │   └── admin-alerts.tsx  admins post alerts
        ├── components/     shared UI
        └── lib/            API client, auth, polling, notifications, theme
```

## Run it (about 10 minutes)

**1. Backend** (Python 3.9+)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then edit secrets
python seed.py                                          # demo driver@nsu.edu / driverpass123
uvicorn app.main:app --reload --env-file .env --host 0.0.0.0 --port 8000
```
Open http://localhost:8000/docs to try every endpoint in the browser. Run tests with `pytest`.

**2. Mobile app** (Node 20+)
```bash
cd mobile
npm install
cp .env.example .env          # set EXPO_PUBLIC_API_URL to your computer's LAN IP, e.g. http://192.168.1.20:8000
npx expo start
```
Scan the QR code in the terminal with **Expo Go** on your phone (phone and laptop on the same Wi-Fi). Sign up with an `@spartans.nsu.edu` or `@nsu.edu` email. Log in as `driver@nsu.edu` on a second phone to see the driver tabs and scan a student's pass.

Checks before committing: `npm run typecheck` (mobile) and `pytest` (backend).

## Plugging in NSU's real shuttle tracker

NSU's shuttles report to **Samsara**. With a read-only Samsara API token from NSU, set `TRACKER_PROVIDER=samsara` and the token in `.env`; no code changes. Full guide, including what to ask NSU: [docs/TRACKER_INTEGRATION.md](docs/TRACKER_INTEGRATION.md).

Every location source implements one method, `get_vehicles()`, in `backend/app/providers/`. `TRACKER_PROVIDER=phone` uses tracker mode (a phone on the shuttle), `mock` simulates shuttles, and sources can be combined, e.g. `phone+mock`.

1. Ask NSU Transportation which vendor the shuttles report to (TransLoc, Passio GO, DoubleMap, Samsara, a fleet GPS, etc.) and request read-only API access for the project.
2. Copy `providers/transloc.py` (a template) or write a new class for that vendor; map its vehicle and route IDs to ours.
3. Register it in `providers/__init__.py`, set `TRACKER_PROVIDER` in `.env`. The app needs no changes.
4. Replace `data/routes.json` with the official stops and route shapes (or load them from the vendor API).

If access doesn't come through in time, demo with the mock provider and show the adapter as the integration point.

## How the QR pass works (security)

The pass encodes `user_id.time_window.HMAC-SHA256(user_id.time_window, PASS_SECRET)`.
- Changes every 30 s, so a screenshot shared with someone else stops working almost immediately.
- Can't be forged without the server-only secret; tampering with the user id breaks the signature.
- Each code can be scanned once (replay protection), and inactive accounts are rejected.
- Login tokens are stored in the phone's Keychain/Keystore (expo-secure-store), passwords hashed with PBKDF2-SHA256 (600,000 iterations).

## Making it downloadable

Use EAS (Expo's cloud build service, free tier works):
```bash
npx eas-cli@latest build --platform android --profile preview   # gives an installable .apk link
npx eas-cli@latest build --platform ios                          # needs an Apple Developer account ($99/yr) for TestFlight
```
Android APKs can be shared by link for testing. App Store / Play Store release needs NSU's approval to use its name and logo.

Deploy the backend somewhere with HTTPS (Render, Railway, Fly.io) and point `EXPO_PUBLIC_API_URL` at it. Swap SQLite for Postgres once real students use it.

## Known gaps / next steps
- Arrival alerts are local notifications while the app is running; add server-side push (Expo push tokens) so alerts arrive when it's closed.
- Admin screens (manage drivers, routes, service alerts) are API-only so far.
- Stop coordinates in `routes.json` are placeholders.
- Ride requests are polled; WebSockets would make them instant.
