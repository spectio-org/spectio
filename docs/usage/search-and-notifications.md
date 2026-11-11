---
icon: material/magnify
---
# Search and notifications

!!! note "Built on the integration branch, not released yet"

    The search dialog (step FU-P3-89) and the notifications panel (FU-P3-113) work today from a checkout, 2026-11-11, batch [P3-B15](../progress/W5/P3-M9.md#batch-p3-b15); the panel was redrawn by UI-05b in batch [P3-B16](../progress/W5/P3-M9.md#batch-p3-b16). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). The screens come from a server seeded by `tools/media/b15_demo.py` (the notifications shots by `b16_demo.py`): run records with no pipeline behind them.

Two buttons in the top bar: **Search**, and the bell. Both open a dialog over the page. Both are owned by the top-bar note of [ui-spec §2](../specs/ui-spec.md#2-main-navigation); the bell's two routes by [api §5.9](../specs/api-and-data-model.md#59-notifications-001).

## Search

Click **Search**, or press ⌘K (Ctrl+K on Windows and Linux). On a phone, tap the search icon of the top bar; the dialog then fills the screen.

![The search dialog with "rna" typed: 7 results, five runs under Runs, and nf-core-rnaseq and RNA-seq test under Pipelines](../assets/shots/app-search_light.webp#only-light)
![The search dialog with "rna" typed, dark](../assets/shots/app-search_dark.webp#only-dark)

*Seven seeded runs and three catalog entries. Typing "rna" finds five runs by their name and two pipelines.*

| Under | What it matches | Where it looks |
|---|---|---|
| **Runs** | a run name that starts with your text, at most 5; a run ID, exactly | `GET /runs?q=` and `GET /runs/{id}` |
| **Pipelines** | the name, label or location of an entry of [your catalog](pipeline-catalog.md) | `GET /catalog` |
| **Pages** | the app's pages by name: Home, Runs, Launch, Pipelines, Environments, Profile | the page itself, no request |

- **No new server route.** Search asks the API for what it already has. `GET /search` of the API catalogue comes later.
- **A six-letter ID ending.** Six letters of a run ID's end, as the Runs page shows them, also find the run, among the 200 newest only: the API has no match on the end of an ID yet.
- **Keyboard.** Results are buttons. ArrowDown and ArrowUp move between the box and the results, Enter opens one, Escape closes the dialog and the focus returns to the button you used. A line under the box says "7 results" or "No match" and is read out.
- **Requests.** Spectio waits 150 ms after the last key, and drops the requests of the previous text when the text changes or the dialog closes.
- **A failure** shows "Search failed: …" beside whatever did answer.

## The bell

The bell shows a badge with the count of unread notifications and is named "Notifications, 6 unread" (the number changes). Click it. On a desktop or a tablet the panel opens under the bell; on a phone it is a sheet from the bottom. The panel was redrawn by step UI-05b (batch [P3-B16](../progress/W5/P3-M9.md#batch-p3-b16)); its layout is owned by [ui-spec §12.13](../specs/ui-spec.md#1213-notifications-panel).

![The notifications panel under the bell: a header with All and Unread and a Mark all as read icon, then Today with four runs, Yesterday with one and 2026-11-09 with one, each row a state tile, the run name and its state, the engine and the time, and an unread dot; View all runs at the foot](../assets/shots/app-notifications_light.webp#only-light)
![The notifications panel, dark](../assets/shots/app-notifications_dark.webp#only-dark)

*Six seeded runs, all unread. The day groups follow the clock of the capture, 2026-11-11 (Today, Yesterday, then the ISO date).*

![The same panel on a phone, a bottom sheet with a close button, All and Unread, Mark all as read as a button, and the same three day groups](../assets/shots/app-notifications-phone_light.webp#only-light)
![The same panel on a phone, dark](../assets/shots/app-notifications-phone_dark.webp#only-dark)

- **What it lists.** One item for each run that succeeded, failed or was cancelled, or that waits at a gate, newest first, at most 50. 0.0.1 never sets the gate state, so no item says "waits at a gate" yet.
- **A row** is a link to its run: a tile with the state's icon, the run name and the state word, then the engine's mark and the time. An unread row has a dot and a tint. Its name for a screen reader is "rnaseq-treatC-ctrl, Failed, Nextflow, 5 h ago, unread". The time is relative for 7 days ("35 min ago", "1 day ago"), then the date.
- **Day groups.** Today, Yesterday, then the date. The time of an item is the run's end time, not the time Spectio saw it, so a run that ended before Spectio adopted it sits where it ended ([api §5.9](../specs/api-and-data-model.md#59-notifications-001), amended 2026-11-11).
- **All and Unread** filter the list in the browser. "No unread notifications" offers **Show all**.
- **Mark all as read** (the check icon, or the button on a phone) moves the mark forward to the newest item. It never moves back, and a run that ends later is unread again. Opening a row does not mark it: a per-item mark is Later. A failed mark says "Could not mark as read: …", and its Retry tries the mark again.
- **Keyboard.** The list is one Tab stop: ArrowUp and ArrowDown move between rows, Home and End jump, Enter opens the run, Escape closes the panel and the focus returns to the bell. **[Not run in a browser by `doc-writer`; covered by `NotificationsBell.test.tsx`.]**
- **View all runs →** at the foot goes to the Runs page.
- **No e-mail.** The list is in the app only.
- **Live.** The count is read again after each run change on the event stream; there is no polling.
- **Loading, empty or failed.** Three grey rows, "No notifications yet", or an error panel with Retry.
- **On a narrow phone** the bell stays at every width, down to 320 px. Below 390 px the theme switch hides instead, since the [Profile page](profile.md) also sets the colour mode; search stays.

## On the API

Run against the demo server of the shots, with the session cookie and the loopback `Origin` (2026-11-11):

```console
GET  /api/v1/me/notifications                      200  6 items, unread 6, read_up_to null; each item has id, kind, run_id, run_name, engine, at, read
POST /api/v1/me/notifications:mark-read {"up_to": "<newest item's at>"}   200  unread 0
POST /api/v1/me/notifications:mark-read {"up_to": "2026-01-01T00:00:00"} 422  (no offset)
GET  /api/v1/me/notifications?after=<newest at>    200  0 items
GET  /api/v1/runs?q=rna&limit=5                    200  rnaseq-treatB-ctrl, rnaseq-treatA-ctrl, rnaseq-tuned, rnaseq-treatC-ctrl, rnaseq-pilot
```

- **No notification table.** An item is derived from a run in one of four states, at the run's last state change. `unread` counts every item newer than the one mark, not only the 50 listed.
- **One mark, for the one user.** 0.0.1 is single-user. Items are not scoped to a principal yet (SEC-P3FU113-02, open).

## Not shown

- The search dialog on a phone, the Unread view, and the empty, loading and failed states of both dialogs: covered by `vitest` (`SearchDialog.test.tsx`, `NotificationsBell.test.tsx`), not by a shot.
- **Open findings.** In the panel: a long run name has no tooltip (CR-P3UI05B-06) and Tab leaves the popover to the end of the page (CR-P3UI05B-08). A far-future `up_to` hides later notifications for good (CR-P3FU113-03, SEC-P3FU113-01, SEC-P3UI05A-02); search drops every rejection, not only an abort (CR-P3FU89-02) and reads the catalog again after each key (-03). The panel's loading line (CR-P3FU113-05) is closed: the new panel shows skeleton rows. See [Follow-ups of batch P3-B16](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b16) and [B15](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b15).

## Next

- [Your pipeline catalog](pipeline-catalog.md), which Search looks in.
- [Your profile](profile.md).
- [Progress page of milestone M9](../progress/W5/P3-M9.md).
