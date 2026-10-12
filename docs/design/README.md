# App design (D4 UI/UX Design Package)

Everything for SpartanGO's look and screen flow lives here: user journeys, wireframes, high-fidelity mockups, and the link to the clickable prototype. Owner: **Mobile UX / Front End** workstream. Reviewer: one other teammate.

Per the proposal (section 14): low-fidelity wireframes in **week 5**, the clickable prototype in **week 10**.

## Folders

| Folder | Put here | File naming |
| --- | --- | --- |
| [`user-flows/`](user-flows/) | The 6 required user journeys, as flow diagrams or step lists | `01-request-ride.png`, `01-request-ride.md` |
| [`wireframes/`](wireframes/) | Low-fidelity, grayscale layouts (sketches or Figma exports) | `wf-03-select-stop.png` |
| [`mockups/`](mockups/) | High-fidelity screens in final colors and type | `hf-03-select-stop.png` |
| [`assets/`](assets/) | App icon, logo drafts, illustrations | `icon-1024.png` |

**Clickable prototype:** _paste the Figma (or similar) link here once it exists._ Figma's free education plan works for a student team. Export each frame to `mockups/` before every advisor review so the repo always has a snapshot.

## Required screens (proposal section 12)

Each screen gets a wireframe and a mockup. The last column shows which feasibility-prototype screen already covers it, so the designer can start from what exists in `mobile/src/app/`.

| # | Screen / flow | Design intent (from the proposal) | Wireframe | Mockup | Closest prototype screen |
| --- | --- | --- | --- | --- | --- |
| 1 | Sign-in / entry | Clarify account context and role | ☐ | ☐ | `(auth)/login.tsx`, `signup.tsx` |
| 2 | Student home / shuttle status | Show current service state and the next useful action | ☐ | ☐ | `(tabs)/index.tsx` (live map) |
| 3 | Select pickup stop | Make designated stops easy to identify | ☐ | ☐ | `(tabs)/ride.tsx` (stop chips) |
| 4 | Ride request confirmation | Prevent accidental requests and show resulting status | ☐ | ☐ | Not built: add a confirm step |
| 5 | Live / estimated arrival view | Present time and location confidence clearly; separate estimates from facts | ☐ | ☐ | `(tabs)/arrivals.tsx` |
| 6 | Notification / status history | Explain changes without forcing repeated checking | ☐ | ☐ | Not built |
| 7 | QR verification display | Obvious, time-bounded verification state | ☐ | ☐ | `(tabs)/pass.tsx` |
| 8 | Operator validation view | Show valid / invalid / expired result clearly | ☐ | ☐ | `(tabs)/scan.tsx` (expired not yet separate) |
| 9 | Service unavailable / degraded state | Explain what the user can do when data or connectivity fails | ☐ | ☐ | Not built (FR-08) |

## Required user journeys (proposal section 5)

1. Student requests a ride from a designated stop.
2. Student checks shuttle / ETA status.
3. Student receives a status or arrival alert.
4. Student displays a time-limited verification code.
5. Authorized operator validates the code.
6. System handles unavailable data or a failed request gracefully.

## Design basics already in the prototype

Change these in one place (`mobile/src/lib/theme.ts`) and the whole app follows.

| Token | Value | Used for |
| --- | --- | --- |
| Green | `#007A53` | Primary buttons, active tabs, headings |
| Gold | `#F2A900` | Accents, alert bell on |
| Background | `#F6F7F5` | Screen background |
| Text / muted | `#1B1F1D` / `#5E6862` | Body text / secondary text |
| Danger / success | `#C62828` / `#2E7D32` | Invalid / valid pass results |

## Design rules (from the non-functional requirements)

- **Few steps:** a ride request should take 3 taps or fewer from home.
- **Estimates look like estimates:** say "about 4 min", show when the location last updated, never show a stale shuttle as live.
- **Accessible:** at least 4.5:1 text contrast, touch targets at least 44 pt, every icon has a text label or screen-reader label, nothing communicated by color alone (valid/invalid also uses ✓ / ✕ and words).
- **Prototype honesty:** the QR screen must say it is a prototype pass, not an official NSU ID (proposal sections 17 and 18).
