# Final demo guide: real shuttles, Uber-style rides, QR boarding, service alerts

This is how the team runs the end-of-semester demo with a **real NSU shuttle**, without any
access to NSU's Samsara system.

## What's new in the app

| Feature | How it works | Requirement |
| --- | --- | --- |
| **Tracker mode** | A teammate (or a driver, if Facilities approves) rides the shuttle with the app open on the **Drive** tab. The phone sends its GPS position every 5 seconds. Riders see that shuttle live on the map. Positions are kept in memory only, never saved, and disappear after 2 minutes without an update. | FR-03, FR-11, NFR-03, NFR-09 |
| **Arrival times** | From the shuttle's live position, using the team's own measured stop-to-stop times (`segment_seconds` in `routes.json`) plus a short stop at each stop. When no shuttle is reporting, the app shows **Scheduled** times from the timetable. Every time is labeled *Live*, *Simulated* or *Scheduled*. | FR-03, NFR-08 |
| **Uber-style ride requests** | The student picks pickup and drop-off; the server automatically assigns the shuttle that can reach the pickup soonest and has a seat. Riders share shuttles. The student never picks a driver and sees "Shuttle 1 is on the way · about 4 min" with a live map. | FR-02 (updated), new FR-15 |
| **QR pass** | Unchanged: rotates every 30 s, works once, scanned in the driver's **Scan** tab. Physical NSU ID always accepted. | FR-05 to FR-07, FR-12 |
| **Service alerts** | Admins post alerts from **More → Post a service alert**: *Stop moved* (shows the temporary pickup on the map), *No service* (holidays; ride requests are paused), *Delay*, *Announcement*. Alerts start and end on their own, appear as banners, and are sent as push notifications. | new FR-14 |

## 1. Put the server online (once)

1. Create a free account at **render.com** and sign in with GitHub.
2. **New → Blueprint →** pick the `SpartanGO` repo. Render reads `render.yaml`.
3. When asked, type a **DEMO_DRIVER_PASSWORD** and **DEMO_ADMIN_PASSWORD** (keep them private; never put them in GitHub).
4. Wait for "Live". Your API address looks like `https://spartango-api.onrender.com`. Open `/docs` on it to check.

Notes: the free plan sleeps after 15 minutes idle (the first request takes ~1 minute to wake it up, so open the app a few minutes before presenting), and its disk resets on restart (students sign up again; the demo driver and admin accounts are re-created automatically). For a permanent version, add a Render Postgres database later.

## 2. Point the app at the server

In `mobile/.env`:
```
EXPO_PUBLIC_API_URL=https://spartango-api.onrender.com
```
Then `cd mobile && npm install && npx expo start`. Because the server is online, phones no longer need to be on the same Wi-Fi as a laptop: cellular data works.

## 3. Load NSU's real stops and timing (team task)

Edit `backend/app/data/routes.json`:
- **Stops:** exact name, latitude and longitude for every stop, in the order the shuttle drives them. Get coordinates by dropping a pin in Google Maps at each stop.
- **segment_seconds:** ride the route 2–3 times, record the time the shuttle leaves each stop, and enter the average travel time (in seconds) for each leg. A loop with 5 stops has 5 legs (including last stop → first stop).
- **schedule:** first and last departure times, minutes between shuttles, and service days, from Facilities.

Run `pytest` in `backend/` after editing, then push. Render redeploys automatically.

## 4. Demo accounts and phones

| Phone | Account | Used for |
| --- | --- | --- |
| Phone A (presenter) | a student account (sign up with an `@spartans.nsu.edu` email) | request a ride, show the QR pass |
| Phone B (on the shuttle) | `driver@nsu.edu` | Drive tab (tracker mode), Queue, Scan |
| Phone C (optional) | `admin@nsu.edu` | post a service alert live |

Before demo day: charge every phone, check cellular data, allow Location (Phone B) and Notifications (Phone A).

## 5. Demo script (about 3 minutes)

1. **Real shuttle on the map.** Phone B is riding a real NSU shuttle with tracker mode on. On Phone A, open the Map: "This is a live NSU shuttle, tracked by a teammate's phone riding it right now."
2. **Arrival time.** Arrivals tab: "*Live · about 4 min* at the Library."
3. **Request a ride.** Ride tab → pickup and drop-off → Request. The app assigns the shuttle automatically: "Shuttle 1 is on the way · about 4 min," with the shuttle moving toward the pickup.
4. **Board with the QR pass.** Pass tab on Phone A; Phone B scans it in the Scan tab → **Valid · name**. Then scan an old screenshot → **Already scanned / Expired**.
5. **Service alert.** Phone C posts "Library stop moved for tonight's event." Phone A shows the banner and notification, and the map shows the temporary stop.
6. **Wrap up.** Driver marks Picked up → Dropped off.

**Backups:** record a screen video of the full flow beforehand. If the shuttle isn't running at demo time, switch the server to `TRACKER_PROVIDER=phone+mock` and show the simulated shuttles, clearly labeled *Simulated*.

## 6. Push notifications when the app is closed (optional)

In-app banners and notifications work in Expo Go while the app is open. To receive pushes with the app closed, create an EAS project (`npx eas-cli@latest init` in `mobile/`), which adds a project id to `app.json`, then build the app with EAS (`eas build --profile preview`). The server already sends pushes for service alerts and ride assignments.

## Rules we keep (Statement of Assurance)

- No scraping, copying or probing of Samsara or the public live map.
- No driver names, driving behavior or camera footage, ever.
- Tracker mode shares only the shuttle's current position, only while it is turned on.
- Tell Facilities before using tracker mode on their shuttle.
