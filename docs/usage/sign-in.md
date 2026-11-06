---
icon: material/key-link
---
# Signing in on your own machine

!!! note "Built on the integration branch, not released yet"

    Everything below runs today from a checkout (batch [P3-B01](../progress/W5/P3-M3.md#tasks-12-to-16-batch-p3-b01), 2026-11-06). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). There are no accounts yet: 0.0.1 serves one user on one machine.

Spectio's 0.0.1 server listens on `127.0.0.1` only. On a shared login node every user can reach that port, so Spectio asks for a sign-in before it shows any data. You sign in with a link, not a password.

The rules are owned by [development environment §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (requirements 2 to 5, 7 and 9). This page says what you see.

## Steps

1. **Start the server.** `spectio serve` prints a first link, single use, valid 15 minutes:

    ```text
    Spectio 0.0.1 is running on demo-hpc-login1, port 18081.
    Open this link in a browser on this machine (single use, valid 15 minutes):
       http://127.0.0.1:18081/auth/link#<ticket>
    New link at any time: spectio login --print-link
    Spectio never asks you to paste a link.
    ```

2. **Open the link** in a browser on the same machine. The page reads the ticket after the `#`, removes it from the address bar and history, and opens Spectio. The browser keeps a session cookie named after the port, for example `spectio_session_18081`.
3. **Need another link?** Run `spectio login --print-link` on the node where the server runs. `--json` prints one line for scripts.
4. **Server on another node?** The command prints the `ssh` line to run there and sends nothing: `The server runs on <node>: run ssh <node> spectio login --print-link.`
5. **Restart the server** and every session ends. Sessions live in the server's memory only. Ask for a new link.

!!! warning "A spent or old link"

    A link works once and for 15 minutes. After that the page says "This link was already used or has expired. Run `spectio login --print-link` on the cluster for a new one."

## What is refused

Each request passes four checks, in this order. The first that fails answers and stops the request.

| Check | Refusal | When |
|---|---|---|
| Host allow-list | `400` host-not-allowed | the `Host` header is not `127.0.0.1`, `localhost` or `[::1]` |
| Cross-site check | `403` cross-site | the request comes from another site (`Sec-Fetch-Site`, `Origin` or `Referer`) |
| Session | `401` unauthenticated | no valid cookie for this port; four routes are exempt: the link page, its script, the exchange and the new-link route |
| Write checks | `403`, `411`, `415`, `413` | a write with no `Origin`, with `Transfer-Encoding`, with a body that is not JSON, or with a body over 1 MiB |

Private files follow [requirement 5](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts): the data and config directories are `0700`, the files in them `0600`. Spectio refuses a looser directory and does not tighten it.

## See it run

The cast runs the real CLI in a demo home, with the demo host `demo-hpc-login1`. The ticket and the session secret are masked by a visible `sed`. Steps: the start text, a request with no session and one with a foreign `Host`, a new link, the exchange, the spent link, three refused writes, the file modes, the clean stop.

<div class="asciinema-cast" data-cast="assets/casts/spectio-sign-in.cast"></div>

## Not built or not checked

- **A browser end to end.** The page script (`link.js`) was not run in a browser for this batch. Two browser behaviours that requirement 3 marks **[to be validated]** (the `EventSource` carries the cookie; a `SameSite=Strict` cookie is sent after a link opened from another site) wait for the Playwright smoke.
- **SLURM and shared hosts.** The API is still not served there, and its refusal text still says "until sign-in is complete". Mounting it is a security-posture choice that waits for a decision ([inbox #109](../reviews/inbox.md#109-assumed-writes-need-origin-and-json-as-built-p3-task-16) rule 5).
- **Hard links on the EMBL shared home.** The first state file is linked into place; whether `link(2)` works there is **[to be validated]**.
- **Accounts, passwords, tokens for robots.** Later versions: [Authentication and access](../specs/authentication-and-access.md).
