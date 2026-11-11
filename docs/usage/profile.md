---
icon: material/account-outline
---
# Your profile

0.0.1 has one mode: single-user. There are no accounts, so the page says who the server runs as and shows nothing about teams or roles.

The Profile page answers four questions: who is this server running as, how long is this browser signed in, where are Spectio's files, and which colour mode is on.

## Open it

Click the avatar at the right of the top bar. The breadcrumb reads Home › Profile.

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
- **Sign out of this session** revokes this session only. The page then says "Signed out of this session. To sign in again, open the link that spectio serve printed, or run spectio login --print-link." and moves focus to that line. Open event streams of the page may keep running until they disconnect (low impact: the same browser and the same Unix user).
- **If the profile cannot be read** the page says "Your profile could not be read." with **Retry**; focus then moves to the loading line and to the first card.
- **On a phone** the title bar carries "Single-user mode · alice", and **Sign out of this session** is full width.

![The Profile page on a phone: the cards stacked, Sign out of this session full width](../assets/shots/app-profile-phone_light.webp#only-light)
![The Profile page on a phone, dark](../assets/shots/app-profile-phone_dark.webp#only-dark)

*Sign out is 36 px tall, under the 44 px target the phone screens aim for: a known minor.*

## On the API

Both routes are under `/api/v1` and need the session cookie; the write also needs the loopback `Origin`. These calls ran against a demo server, in this order:

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

## Not checked

- The page on a server with an `expires_at` (no 0.0.1 session has one), the "Could not copy" message, and the Retry state were not captured. Unit tests cover them.
- The avatar has no "you are here" cue yet.
- Firefox, WebKit and a screen reader: Chromium only.
