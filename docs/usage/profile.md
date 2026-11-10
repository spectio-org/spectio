---
icon: material/account-outline
---
# Your profile

!!! note "Built on the integration branch, not released yet"

    The Profile page and its two routes (step FU-P3-112, batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14)) work today from a checkout, 2026-11-10. The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **0.0.1 has one mode: single-user.** There are no accounts, so the page says who the server runs as and shows nothing about teams or roles.

The Profile page answers four questions: who is this server running as, how long is this browser signed in, where are Spectio's files, and which colour mode is on. It is owned by [ui-spec §4.10.1](../specs/ui-spec.md#4101-profile-in-001); its two routes by [api §5.8](../specs/api-and-data-model.md#58-me-and-sign-out-001).

## Open it

Click the avatar at the right of the top bar. The breadcrumb reads Home › Profile.

!!! warning "Open it from the avatar, not from the address bar"

    Today `/profile` is not on the server's list of screen addresses (`static.py`, `ROUTES`). A Reload on the Profile page, a bookmark or a typed address answers `404` with `{"type":"/problems/not-found", …}` instead of the page ([DW-P3B14-01](../reviews/code/P3-B14.md#findings), open). The avatar link works because the browser handles it without asking the server.

## What it shows

![The Profile page: Who the server runs as (Unix user alice, UID 0), This session (started, expires, Sign out of this session), Config paths (config file, data directory, database directory, observed runs directory, each with a Copy button) and the theme](../assets/shots/app-profile_light.webp#only-light)
![The Profile page, dark](../assets/shots/app-profile_dark.webp#only-dark)

*A seeded demo server run as `alice`. The UID reads 0 because the capture host runs as root: the demo patches the name, not the number.*

| Card | What it says |
|---|---|
| **Who the server runs as** | the Unix user and its UID, and "You are the only principal: runs, files and settings are this user's." |
| **This session** | when this browser's session started; "Expires: Ends when the server stops, or when you sign out" (a session lives in memory and has no end date); **Sign out of this session** |
| **Config paths** | the config file, the data directory, the database directory and the observed runs directory, each with a **Copy** button. They are read only here: change them in `spectio.toml`, then restart `spectio serve` |
| **Theme** | Light, Dark or System, kept in this browser. System follows your device |

- **Paths only.** The page and `GET /me` show where things are, never a token, a secret or the contents of a file.
- **Copy** says "Copied the config file path", or "Could not copy …: the browser gave no clipboard".
- **Sign out of this session** revokes this session only. The page then says "Signed out of this session. To sign in again, open the link that spectio serve printed, or run spectio login --print-link." and moves focus to that line. Open event streams of the page may keep running until they disconnect (SEC-P3FU112-01, open, low impact: the same browser and the same Unix user).
- **If the profile cannot be read** the page says "Your profile could not be read." with **Retry**; focus then moves to the loading line and to the first card.
- **On a phone** the title bar carries "Single-user mode · alice", and **Sign out of this session** is full width (the first review round found it at its natural width and the Copy keys at 40 px; the fix is in `profile.css`, checked in Chrome at 360 px).

![The Profile page on a phone: the cards stacked, Sign out of this session full width](../assets/shots/app-profile-phone_light.webp#only-light)
![The Profile page on a phone, dark](../assets/shots/app-profile-phone_dark.webp#only-dark)

*Sign out is 36 px tall, under the 44 px of the phone rule (UX-PAR-09): a known minor, open.*

## On the API

Both routes are under `/api/v1` and need the session cookie; the write also needs the loopback `Origin`. These calls ran against the demo server of the shots, in this order:

```console
GET /me
200  {"principal": {"user": "alice", "uid": 0}, "session": {"started_at": "2026-11-10T19:25:17+00:00", "expires_at": null}, "paths": {"config_file": "/srv/demo-b14/data/spectio.toml", "data_dir": "/srv/demo-b14/data", "db_dir": "/srv/demo-b14/db", "observed_dir": "/srv/demo-b14/home/.spectio/observed"}}
POST /auth/session:sign-out        (no Origin header)
403
POST /auth/session:sign-out
204
GET /me                            (the same cookie)
401
```

- **`expires_at` is always `null`** in 0.0.1.
- **`db_dir` comes from the open database's URL.** A URL with no database would raise a `TypeError` and answer `500` (SEC-P3FU112-03, open).
- **The sign-out is beyond what the task asked for** ("one read-only GET"). It is recorded in the spec's notes as an assumed scope extension, and the security review found it acceptable.

## Not shown

- The page on a server with an `expires_at` (no 0.0.1 session has one), the "Could not copy" message, and the Retry state: not captured. Tests cover them (`ProfilePage.test.tsx`).
- The avatar's "you are here" cue: not built (UX-P3FU112-02, open).
- Firefox, WebKit and a screen reader: Chromium only.
