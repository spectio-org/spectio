# Spike: a central UI reading run outputs through a runner on the login node (2026-11-25)

Question (Thomas, 2026-11-24, inbox #162, issues #355 and #358): can a server on the Kubernetes cluster show a run's outputs when it cannot mount the cluster file systems, with a runner under the user's own account on the login node? Can the login node reach the server at all?

Code: branch `spike/runner-channel`, `spikes/runner-channel/` (throwaway, standard library only).

## 1. What was built

- `server.py`: the central side. A runner long-polls `GET /runner/poll` and answers `POST /runner/reply/<id>`; the server never connects to the runner ([admin-and-operations](../specs/admin-and-operations.md), "the server never connects to a runner"). The browser logs in once with `/login?token=…` and gets an HttpOnly, Secure, SameSite=Strict cookie. The server emulates Spectio's results routes for one fake run, so the real viewers run unchanged.
- `runner.py`: the login node side. It opens every path component with `O_NOFOLLOW` from the root's descriptor, refuses `..`, serves regular files only, and caps one read at 8 MiB.
- `web/src/demo/channel/`: a page that mounts Spectio's own `FilePreview` and `ReportViewer` for six files (CSV, MultiQC report, PDF, PNG, OME-TIFF, OME-Zarr).
- `k8s.yaml`: a Deployment (non-root, read-only root file system, capabilities dropped), a Service, and an Ingress on the internal ingress class. No DNS name: clients connect to the ingress address with the expected host name.

## 2. Results

| Check | Result |
|---|---|
| Outgoing HTTPS from the login node | the internal ingress reached; a held connection lasted 152 s without being cut |
| Runner → pod channel, listing | about 60 ms per command |
| One 8 MiB range | about 0.4 s (about 20 MB/s) |
| Refusals | a symlink, `..` and a request without the token are refused |
| Viewers, files on the login node's scratch | CSV table, MultiQC report (sandboxed), PNG, OME-TIFF and OME-Zarr (WebGL) all open; the PDF opens in the browser's own viewer (demo only, the product offers a download) |

The viewer row was measured with the runner on the login node and the spike server on a workstation, joined by a loopback tunnel; the pod still ran the previous server version, which had the channel but not the demo routes. The channel rows were measured through the pod.

## 3. Findings

1. **The runner channel works for every viewer**, including ranged imaging reads, with no mount on the server. This backs proposal 1 of [output-viewers-2026-11-24](output-viewers-2026-11-24.md).
2. **Spectio keeps one WebGL viewer per page** (`web/src/runs/imaging/viv.ts`): a second OME-TIFF or OME-Zarr viewer on the same page ends the first. That is by design, and it matters for any page showing several images.
3. **About 20 MB/s per range** is enough for tiles and chunks. A whole large file (a 1 GiB report) would take close to a minute: the server-side cache of proposal 2 is worth having.
4. **Not a security model.** The spike uses one shared token and does not verify the ingress certificate (no DNS name yet). The target, per runner tokens, OIDC for browsers, routing to the owner's runner only and an audit, is tracked in #355.

## 4. Next steps

- The runner protocol (inbox #12) carries ranged reads from the start.
- A DNS name and a certificate for the dev namespace, so the runner verifies TLS **[to be validated with EMBL IT]**.
