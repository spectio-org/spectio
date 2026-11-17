---
icon: material/api
---
# API and CLI

0.0.1 has a REST API under `/api/v1` and five commands. The web interface is built on this API and uses nothing else.

!!! note "Later: not in 0.0.1"
    Webhooks, MQTT, AMQP and Kafka events, tokens for robots and services, GA4GH WES, MCP and embedded elements. A script today signs in the way the browser does.

## The REST API

- **Under `/api/v1`,** described by an OpenAPI document, [`openapi/0.0.1.json`](https://github.com/spectio-org/spectio/blob/main/packages/spectio-server/openapi/0.0.1.json) in the `spectio-server` sources: 36 paths. The server does not serve it.
- **Errors** are [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) problem documents (`application/problem+json`).
- **Live events** on `GET /api/v1/events/stream`, Server-Sent Events: one frame per changed run, at most one per second, with the task counts of its processes.
- **Local mode** serves it on `127.0.0.1:<port>`. **On a cluster login node** it is served on a Unix socket only, so call it through the SSH tunnel of [Opening from your laptop](../usage/open-from-your-laptop.md).

| Area | Routes |
|---|---|
| Runs | `GET` and `POST /runs`, `GET` and `PATCH /runs/{id}` (pin), `POST /runs:delete`, `GET /runs:summary`, `POST /runs/{id}:cancel`, `POST /runs/{id}:relaunch` (resume), `GET /runs/{id}:launch-template` (copy to a new launch) |
| Inside a run | `/runs/{id}/stages`, `/processes`, `/tasks`, `/logs`, `/config-file` |
| Files | `/runs/{id}/results` and `/tasks/{id}/attempts/{n}/workdir`, each with `stat`, `text` and `raw`; `/tasks/{id}/attempts/{n}/files` |
| Launch inputs | `GET /workflows:inspect`, `/environments` (with `:make-default`), `/catalog` |
| You | `GET /me`, `/me/notifications` and `:mark-read` |
| Server | `GET /version`, `/events/stream` |

### Signing in from a script

Every route but the sign-in ones needs the session cookie, and every write needs a same-origin `Origin` header and a JSON body.

1. `spectio login --print-link --json` on the server's node prints a single-use ticket (valid 15 minutes).
2. `POST /api/v1/auth/magic-links:exchange` with `{"ticket": "…"}` answers `204` and sets the session cookie, for this port only.
3. Call the routes with that cookie. `POST /api/v1/auth/session:sign-out` ends the session.

The end-to-end tests of the repository do exactly this (`tests/e2e/global-setup.ts`).

## The command line

| Command | What it does |
|---|---|
| `spectio init` | creates the data directory, `spectio.toml`, the default project and its environment. `--local` is for one machine with no scheduler |
| `spectio doctor` | checks this machine: one `ok`, `warn` or `fail` line per check |
| `spectio serve` | starts the server; `--detach` runs it in a tmux session ([details](../usage/keep-the-server-running.md)) |
| `spectio login --print-link` | prints a new single-use link to the server of this node |
| `spectio open <host>` | from a laptop, opens your server on a cluster login node through an SSH tunnel ([details](../usage/open-from-your-laptop.md)) |

There is no command to launch or list runs yet: use the web form or `POST /api/v1/runs`.
