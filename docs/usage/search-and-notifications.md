---
icon: material/magnify
---
# Search and notifications

!!! note "Built on the integration branch, not released yet"

    The search dialog (step FU-P3-89) and the notifications panel (FU-P3-113) work today from a checkout, 2026-11-11, batch [P3-B15](../progress/W5/P3-M9.md#batch-p3-b15). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). The screens come from a server seeded by `tools/media/b15_demo.py`: run records with no pipeline behind them.

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

The bell shows a badge with the count of unread notifications and is named "Notifications, 6 unread" (the number changes). Click it.

![The notifications panel at the top right: six items, rnaseq-treatA-ctrl succeeded, rnaseq-tuned succeeded, liver-qc-batch-7 succeeded, rnaseq-treatC-ctrl failed, liver-qc-batch-6 succeeded and rnaseq-pilot was cancelled, each with its time and "Unread"; above them Mark all as read](../assets/shots/app-notifications_light.webp#only-light)
![The notifications panel, dark](../assets/shots/app-notifications_dark.webp#only-dark)

*The times are those of the seeded records' creation, which is also their last change.*

- **What it lists.** One item for each run that succeeded, failed or was cancelled, or that waits at a gate, newest first, at most 50. Each item is a link to its run, named by the run, what happened and when ("rnaseq-treatC-ctrl failed, Today 03:07, unread"). 0.0.1 never sets the gate state, so no item says "waits at a gate" yet.
- **No e-mail.** The list is in the app only.
- **Mark all as read** moves the mark forward to the newest item. It never moves back, and a run that ends later is unread again. A failed mark says "Could not mark as read: …", and its Retry tries the mark again.
- **Live.** The count is read again after each run change on the event stream; there is no polling.
- **Empty or failed.** "No notifications yet", or an error line with Retry.
- **On a narrow phone** the bell stays at every width, down to 320 px. Below 390 px the theme switch hides instead, since the [Profile page](profile.md) also sets the colour mode; search stays.

## On the API

Run against the demo server of the shots, with the session cookie and the loopback `Origin` (2026-11-11):

```console
GET  /api/v1/me/notifications                      200  6 items, unread 6, read_up_to null
POST /api/v1/me/notifications:mark-read {"up_to": "<newest item's at>"}   200  unread 0
POST /api/v1/me/notifications:mark-read {"up_to": "2026-01-01T00:00:00"} 422  (no offset)
GET  /api/v1/me/notifications?after=<newest at>    200  0 items
GET  /api/v1/runs?q=rna&limit=5                    200  rnaseq-treatB-ctrl, rnaseq-treatA-ctrl, rnaseq-tuned, rnaseq-treatC-ctrl, rnaseq-pilot
```

- **No notification table.** An item is derived from a run in one of four states, at the run's last state change. `unread` counts every item newer than the one mark, not only the 50 listed.
- **One mark, for the one user.** 0.0.1 is single-user. Items are not scoped to a principal yet (SEC-P3FU113-02, open).

## Not shown

- The search dialog on a phone, and the empty and failed states of both dialogs: covered by `vitest` (`SearchDialog.test.tsx`, `NotificationsBell.test.tsx`), not by a shot.
- **Open findings.** A far-future `up_to` hides later notifications for good (CR-P3FU113-03, SEC-P3FU113-01); the panel opened before the first answer is empty, with no loading line (CR-P3FU113-05); search drops every rejection, not only an abort (CR-P3FU89-02) and reads the catalog again after each key (-03). See [Follow-ups of batch P3-B15](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b15).

## Next

- [Your pipeline catalog](pipeline-catalog.md), which Search looks in.
- [Your profile](profile.md).
- [Progress page of milestone M9](../progress/W5/P3-M9.md).
