"""Spike server: reads a user's files only through that user's runner, and serves the runner-
channel demo (one fake run `demo`, its files under the runner's `data/`, the built UI under `ui/`).

Throwaway (spike/runner-channel). Standard library only, so the pod needs no build.

- The runner, on the login node, long-polls `GET /runner/poll` over outgoing HTTPS and answers
  each command with `POST /runner/reply/<id>`: the server never connects to the runner
  (admin-and-operations §3.2: commands are pulled, never pushed). A file over 8 MiB is read in
  several `file` commands, each at most one range.
- Browser auth: `GET /login?token=…` checks the token and sets an HttpOnly, Secure,
  SameSite=Strict cookie; the API and the static routes accept that cookie or the `Bearer`
  header (the runner keeps the header).
- `GET /` and every other non-API path serve a file of `ui/` under the runner's root, with the
  Content-Type its extension says.
- The demo run's routes copy the results routes the viewers call (api §5.3, results.py):
  the listing `GET /api/v1/runs/demo/results?path=`, `…/stat/<path>`, `…/text/<path>` (one Range
  → `206` with `Content-Range`, else the tail), and `…/raw/<path>` with `as=image` (an image for
  `Sec-Fetch-Dest: image`, signature checked), `as=tiff` (one closed Range → `206`), `as=zarr`
  (a key below a `.ome.zarr`, whole or by one Range), a report's HTML with the report CSP, and
  an attachment otherwise. One demo-only difference, marked in the code: a PDF is served inline
  (`application/pdf`), because the demo page shows it in an `<iframe>`; the product server has
  no PDF viewer and sends it as an attachment.
- The old debug routes `GET /api/file|stat|list` stay, for curl at the terminal.
"""

import hmac
import json
import os
import queue
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

TOKEN = os.environ["SPIKE_TOKEN"]
POLL_WAIT = 25.0  # seconds a poll is held open when no command waits
REPLY_WAIT = 30.0  # a browser request waits this long for the runner
MAX_LENGTH = 8 * 1024 * 1024 + 1  # one runner read, as one imaging range (api §5.3)
CHUNK = 1 << 20  # one read of a raw file, as files.CHUNK of the product server
MAX_RAW = 1 << 30  # the largest results file served (api/results.py MAX_RAW)
MAX_IMAGE = 20 << 20  # the largest served as an image
MAX_SVG = 5 << 20  # the largest SVG served as an image
MAX_KEY = 16 << 20  # the largest Zarr key (api §5.3.1, step 7)
MAX_RANGE = (8 << 20) + 1  # the most bytes of one imaging range (api §5.3.1, step 8)
MAX_READ = 1 << 20  # the most one text read returns (files.confine MAX_READ)
TAIL = 65536  # the text route's default tail (files.confine TAIL)
SNIFF = 8192  # a NUL in these first bytes makes a file binary (taskfiles SNIFF)
MAX_ENTRIES = 1000  # of one listing (files.results MAX_ENTRIES)
MAX_REPORTS = 50  # of one report search
REPORT_DEPTH = 4  # a report at most this many levels below the root
RUN_ID = "demo"
COOKIE = "spike_session"
DEMO_ROOT = "/home/demo/runs/demo/results"  # shown as the run's `root`; the runner's is private

commands: "queue.Queue[dict]" = queue.Queue()
pending: dict[str, dict] = {}  # id -> {"event", "status", "body", "headers"}
pending_lock = threading.Lock()
runner_seen = {"at": 0.0, "host": None}

sessions: dict[str, float] = {}  # cookie -> login time; the browser's token, never the runner's
sessions_lock = threading.Lock()

HEADERS = {  # of every file and listing route (api/taskfiles.py HEADERS)
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
}
TEXT_CSP = "sandbox; default-src 'none'"  # every text and image read (dev-env §15.3 req. 14)
REPORT_CSP = (
    "sandbox allow-scripts allow-downloads; default-src 'none'; "
    "script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)
AS = ("image", "tiff", "zarr")
SCRIPT_DESTS = frozenset({"script", "worker", "sharedworker", "serviceworker"})  # api §5.3.1 step 0
TIFF_HEADS = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")  # TIFF 6.0 and BigTIFF (step 10)
MEDIA = {  # files/images.py MEDIA: a name's suffix → the type an image is served with
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
SVG = "image/svg+xml"
MAX_PIXELS = 50_000_000  # 50 megapixels, as images.check holds
ENGINE_DIRS = frozenset({".spectio", ".snakemake", ".nextflow"})  # never part of a results path
METADATA = frozenset({".zattrs", ".zgroup", ".zarray", "zarr.json"})  # a Zarr key's last part
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".map": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".wasm": "application/wasm",
    ".woff2": "font/woff2",
}

_CLOSED = re.compile(r"bytes=([0-9]{1,19})-([0-9]{1,19})")  # one closed imaging range (step 8)
_RANGE = re.compile(r"bytes=([0-9]{1,15})-([0-9]{0,15})")  # one text range (taskfiles _RANGE)
_KEY_PART = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,254}")  # a middle part of a Zarr key
_CHUNK_PART = re.compile(r"c|[0-9]{1,10}(\.[0-9]{1,10}){0,9}")
UNSERVED = re.compile(  # the control, bidi and format characters a name never carries
    "[\\u0000-\\u001f\\u007f-\\u009f\\u061c\\u200b-\\u200f\\u2028-\\u202e"
    "\\u2060-\\u206f\\ufeff\\ufff9-\\ufffb]"
)
PROBLEM_JSON = "application/problem+json"


class Missing(Exception):
    """The runner has no such path (404)."""


class Refused(Exception):
    """The runner refused the read (403, 400)."""


class RunnerAway(Exception):
    """The runner did not answer in time, or answered something unusable (504)."""


# --- The runner channel -------------------------------------------------------------------


def authorised(handler: BaseHTTPRequestHandler) -> bool:
    """The `Bearer` header (the runner's, and curl's) or a login cookie."""
    if hmac.compare_digest(handler.headers.get("Authorization", "").encode(), f"Bearer {TOKEN}".encode()):
        return True
    for part in handler.headers.get("Cookie", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE:
            with sessions_lock:
                return value in sessions
    return False


def ask_runner(command: dict) -> dict:
    """Queue a command for the runner and wait for its reply."""
    cid = secrets.token_hex(8)
    slot = {"event": threading.Event()}
    with pending_lock:
        pending[cid] = slot
    commands.put({"id": cid, **command})
    if not slot["event"].wait(REPLY_WAIT):
        with pending_lock:
            pending.pop(cid, None)
        return {"status": 504, "body": b"the runner did not answer", "headers": {}}
    return slot


def runner_op(command: dict) -> bytes:
    """The body of a command the runner answered `200`; else the answer's error."""
    slot = ask_runner(command)
    status, body = slot["status"], slot["body"]
    if status == 200:
        return body
    if status == 404:
        raise Missing()
    if status in (400, 403):
        raise Refused(body.decode("utf-8", "replace"))
    raise RunnerAway(body.decode("utf-8", "replace") or f"the runner answered {status}")


# --- Paths and reads through the runner ----------------------------------------------------


def under_root(tree: str, rel: str) -> str:
    """The path of `rel` below `tree` (`data` or `ui`) under the runner's root."""
    return f"{tree}/{rel}" if rel else tree


def check_rel(path: str) -> str:
    """A results path as a relative path below `data/`; "" for the root itself. The rules of
    `files.results.check_rel`: no absolute, empty, `.` or `..` part, no control, bidi or format
    character, no engine directory."""
    if path == "":
        return ""
    if path.startswith("/") or UNSERVED.search(path):
        raise Refused("not a name this server serves")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise Refused("not a name this server serves")
    if any(part.casefold() in ENGINE_DIRS for part in parts):
        raise Refused("not a results file: the engine's own directory")
    return path


def stat_of(tree: str, rel: str) -> dict:
    """`{"size", "mtime", "dir"}` of `<tree>/<rel>` under the runner's root, as its `stat`
    answers."""
    return json.loads(runner_op({"op": "stat", "path": under_root(tree, rel)}))


def stat_rel(rel: str) -> dict:
    """The stat of one path of `data/`."""
    return stat_of("data", rel)


def list_of(tree: str, rel: str) -> list[str]:
    """The names in `<tree>/<rel>`, as the runner's `list` answers."""
    return json.loads(runner_op({"op": "list", "path": under_root(tree, rel)}))


def list_rel(rel: str) -> list[str]:
    """The names in `data/<rel>`."""
    return list_of("data", rel)


def read_of(tree: str, rel: str, start: int, length: int) -> bytes:
    """At most `length` bytes of `<tree>/<rel>` from `start`, in runner reads of at most one
    range (a file over 8 MiB is read in several commands)."""
    pieces: list[bytes] = []
    at = start
    while at < start + length:
        n = min(start + length - at, MAX_LENGTH)
        data = runner_op({"op": "file", "path": under_root(tree, rel), "offset": at, "length": n})
        pieces.append(data)
        at += len(data)
        if len(data) < n:
            break  # the file ended early
    return b"".join(pieces)


def read_bytes(rel: str, start: int, length: int) -> bytes:
    """A read of one path of `data/`."""
    return read_of("data", rel, start, length)


def chunks_of(tree: str, rel: str, start: int, end: int):
    """Bytes `start` to `end` of `<tree>/<rel>`, at most one range per runner read; the
    response's length was statted first, so a shrunk file cuts the stream, not the length."""
    at = start
    while at < end:
        path_ = under_root(tree, rel)
        data = runner_op({"op": "file", "path": path_, "offset": at, "length": min(end - at, MAX_LENGTH)})
        if not data:
            raise RunnerAway(f"{tree}/{rel}: shrank at {at}")
        yield data
        at += len(data)


def _iso(mtime: float | None) -> str | None:
    return None if mtime is None else datetime.fromtimestamp(mtime, timezone.utc).isoformat()


def _suffix(name: str) -> str:
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def _whole_utf8(data: bytes) -> int:
    """The length of `data` without a UTF-8 sequence cut at its end, so the next read starts on
    a whole character (taskfiles _whole_utf8)."""
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as e:
        return e.start if e.reason == "unexpected end of data" else len(data)
    return len(data)


_ANSI = re.compile("\\x1b(?:\\[[0-9;?]*[ -/]*[@-~]|\\][^\\x07\\x1b]*(?:\\x07|\\x1b\\\\)?)")


def _text(data: bytes) -> str:
    """The text of a read, as the one reader gives it: escapes removed, replaced mojibake."""
    return _ANSI.sub("", data.decode("utf-8", "replace"))


def _report_title(name: str) -> str:
    return "MultiQC report" if name == "multiqc_report.html" else name.rsplit(".", 1)[0]


reports_cache: dict[str, list[dict]] = {}
reports_lock = threading.Lock()


def find_reports() -> list[dict]:
    """The reports below the results root, breadth first, at most `MAX_REPORTS` at a depth of at
    most `REPORT_DEPTH` (files.results.find_reports); computed once: the demo's data is static."""
    with reports_lock:
        if "reports" in reports_cache:
            return reports_cache["reports"]
    found: list[dict] = []
    at: list[tuple[str, int]] = [("", 1)]
    while at and len(found) < MAX_REPORTS:
        rel, depth = at.pop(0)
        try:
            names = list_rel(rel)
        except (Missing, Refused, RunnerAway):
            continue
        for name in names:
            if UNSERVED.search(name) or name.casefold() in ENGINE_DIRS or name.startswith("."):
                continue
            below = f"{rel}/{name}" if rel else name
            try:
                info = stat_rel(below)
            except (Missing, Refused, RunnerAway):
                continue
            if info["dir"]:
                if depth < REPORT_DEPTH:
                    at.append((below, depth + 1))
            elif _suffix(name) in (".html", ".htm"):
                found.append({"path": below, "title": _report_title(name), "group": rel or None})
    with reports_lock:
        reports_cache["reports"] = found
        return found


# --- One entry, a listing, a text read ------------------------------------------------------


def entry_of(rel: str, name: str) -> dict | None:
    """The listing's entry for `name` below `data/<rel>`, or None when it cannot be stat'ed."""
    try:
        info = stat_rel(f"{rel}/{name}" if rel else name)
    except (Missing, Refused, RunnerAway):
        return None
    return {
        "name": name,
        "type": "dir" if info["dir"] else "file",
        "size": None if info["dir"] else info["size"],
        "mtime": _iso(info["mtime"]),
    }


def listing(rel: str) -> dict:
    """The `Results` answer for one folder (api §5.3): the entries, folders first, the reports
    below the root, and `exists` false with none when the folder is not there."""
    try:
        names = list_rel(rel)
    except Missing:
        if rel == "":
            return {"root": DEMO_ROOT, "path": rel, "exists": False, "entries": [], "truncated": False, "reports": []}
        raise
    entries = [e for name in names[:MAX_ENTRIES] if (e := entry_of(rel, name)) is not None]
    entries.sort(key=lambda e: (e["type"] != "dir", e["name"]))
    return {
        "root": DEMO_ROOT,
        "path": rel,
        "exists": True,
        "entries": entries,
        "truncated": len(names) > MAX_ENTRIES,
        "reports": find_reports(),
    }


def stat_entry(rel: str) -> dict:
    """The `ResultStat` answer for one path (api §5.3), with the root and path the server
    answered for."""
    info = stat_rel(rel)
    is_dir = info["dir"]
    return {
        "root": DEMO_ROOT,
        "path": rel,
        "name": rel.rsplit("/", 1)[-1],
        "type": "dir" if is_dir else "file",
        "size": None if is_dir else info["size"],
        "mtime": _iso(info["mtime"]),
    }


def text_read(rel: str, tail: int, byte_range: tuple[int, int | None] | None) -> tuple[int, str, dict]:
    """A text read, as `files.taskfiles.read_text` and `text_response` serve it: the tail, or
    one Range, at most MAX_READ bytes, ended on a whole UTF-8 sequence; `206` with its
    `Content-Range` for a range, `200` for a tail."""
    info = stat_rel(rel)
    if info["dir"]:
        raise Refused("not a file")
    size = info["size"]
    if b"\x00" in read_bytes(rel, 0, min(SNIFF, size)):
        raise Refused("binary")  # the route turns this into 415
    if size == 0:
        return 200, "", {}
    if byte_range is None:
        start = max(0, size - min(tail, MAX_READ))
        data = read_bytes(rel, start, size - start)
        return 200, _text(data), {}
    start, last = byte_range
    if start >= size:
        raise Refused(f"the file has {size} bytes")  # the route turns this into 422
    end = min(size, start + MAX_READ, size if last is None else last + 1)
    data = read_bytes(rel, start, end - start)
    if start + len(data) < size:
        data = data[: _whole_utf8(data)]
    text = _text(data)
    return 206, text, {"Content-Range": f"bytes {start}-{start + len(text.encode('utf-8')) - 1}/{size}"}


# --- The raw route's answers ----------------------------------------------------------------


def zarr_key(parts: list[str]) -> bool:
    """The parts after the first `.ome.zarr` part before the last are a Zarr key (results.py
    `_zarr_key`): a metadata name, or a chunk's indices."""
    for i, part in enumerate(parts[:-1]):
        if part.lower().endswith(".ome.zarr"):
            *middle, last = parts[i + 1 :]
            if not all(_KEY_PART.fullmatch(p) for p in middle):
                return False
            return last in METADATA or _CHUNK_PART.fullmatch(last) is not None
    return False


def check_image(media: str, head: bytes) -> None:
    """The image check of api §5.3 step 7 (files/images.py `check`): the signature of the type
    its name says, and a declared size of at most MAX_PIXELS. The PNG and GIF sizes are read
    whole; the JPEG and WebP sizes are skipped (the demo only shows a PNG)."""
    if media == SVG:
        return
    if media == "image/png":
        ok = head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR"
        if not ok:
            raise Refused("not the image its name says")
        width = int.from_bytes(head[16:20], "big")
        height = int.from_bytes(head[20:24], "big")
        if width * height > MAX_PIXELS:
            raise Refused(f"image too large to decode: {width} x {height}")
    elif media == "image/gif":
        if head[:6] not in (b"GIF87a", b"GIF89a"):
            raise Refused("not the image its name says")
        width, height = int.from_bytes(head[6:8], "little"), int.from_bytes(head[8:10], "little")
        if width * height > MAX_PIXELS:
            raise Refused(f"image too large to decode: {width} x {height}")
    elif media == "image/jpeg":
        if head[:3] != b"\xff\xd8\xff":
            raise Refused("not the image its name says")
    elif media == "image/webp":
        if head[:4] != b"RIFF" or head[8:14] != b"WEBPVP":
            raise Refused("not the image its name says")


def closed_range(value: str | None, size: int) -> tuple[int, int]:
    """Step 8: the one closed range asked, its last byte capped at the file's end."""
    found = None if value is None else _CLOSED.fullmatch(value.strip())
    if found is None:
        raise Refused("Range: one closed range, bytes=<first>-<last>")
    first, last = int(found[1]), int(found[2])
    if last < first or last - first + 1 > MAX_RANGE:
        raise Refused(f"Range: from 1 to {MAX_RANGE} bytes, first to last")
    if first >= size:
        raise Refused("Range: starts at or past the end of the file")
    return first, min(last, size - 1)


# --- The HTTP handler ------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:  # one short line per request
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def send(
        self, status: int, body: bytes, ctype: str = "text/plain; charset=utf-8", extra: dict | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def send_json(self, status: int, obj: dict | list) -> None:
        self.send(status, json.dumps(obj).encode(), "application/json")

    def problem(self, status: int, slug: str, title: str, detail: str) -> None:
        body = {"type": f"/problems/{slug}", "title": title, "status": status, "detail": detail}
        self.send(status, json.dumps(body).encode(), PROBLEM_JSON)

    def stream(self, status: int, length: int, ctype: str, extra: dict, chunks) -> None:
        """Headers with a known `Content-Length`, then the body chunk by chunk, each chunk one
        runner read; a read that fails once the headers are sent aborts the response."""
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        sent = 0
        try:
            for piece in chunks:
                self.wfile.write(piece)
                sent += len(piece)
        except (BrokenPipeError, ConnectionResetError, RunnerAway, Missing, Refused) as e:
            print(f"response cut at {sent}: {e}", flush=True)
            self.close_connection = True

    def file_head(self, rel: str) -> tuple[dict, int]:
        """The stat of one path of `data/`, or the problem its refusal is."""
        try:
            info = stat_rel(rel)
        except Missing:
            self.problem(404, "not-found", "Not found", f"{rel}: no such entry")
            raise _Answered()
        except Refused as e:
            self.problem(422, "file-not-allowed", "File not allowed", str(e))
            raise _Answered()
        except RunnerAway as e:
            self.problem(504, "runner-offline", "Runner offline", str(e))
            raise _Answered()
        if info["dir"]:
            self.problem(422, "file-not-allowed", "File not allowed", f"{rel}: not a file")
            raise _Answered()
        return info, info["size"]

    # -- GET ----------------------------------------------------------------------------------

    def do_GET(self) -> None:
        url = urlparse(self.path)
        args = {k: v[0] for k, v in parse_qs(url.query).items()}
        path = url.path
        if path == "/login":
            return self.login(args)
        if path == "/health":
            return self.send(200, b"ok")
        if not authorised(self):
            return self.send(
                401, b"login required: /login?token=... or a Bearer header", extra={"WWW-Authenticate": "Bearer"}
            )
        if path == "/runner/poll":
            runner_seen.update(at=time.time(), host=self.headers.get("X-Runner-Host", "?"))
            try:
                command = commands.get(timeout=POLL_WAIT)
            except queue.Empty:
                return self.send(204, b"")
            return self.send(200, json.dumps(command).encode(), "application/json")
        if path == "/api/runner":
            seen = runner_seen["at"]
            body = {"host": runner_seen["host"], "ago": time.time() - seen if seen else None}
            return self.send_json(200, body)
        if path in ("/api/file", "/api/stat", "/api/list"):  # the spike's first routes, for curl
            return self.legacy(url, args)
        if path == f"/api/v1/runs/{RUN_ID}":
            return self.send_json(200, RUN)
        prefix = f"/api/v1/runs/{RUN_ID}/results"
        if path == prefix:
            return self.route_results(args.get("path", ""))
        if path.startswith(prefix + "/"):
            rest = path[len(prefix) + 1 :]
            for route, handler_ in (("stat/", self.route_stat), ("text/", self.route_text), ("raw/", self.route_raw)):
                if rest.startswith(route):
                    rel = "/".join(unquote(part) for part in rest[len(route) :].split("/"))
                    try:
                        return handler_(rel, args)
                    except _Answered:
                        return None
        return self.static(path)

    def login(self, args: dict) -> None:
        """A token in the query, checked against the runner's token; a cookie for the browser."""
        given = args.get("token", "")
        if not hmac.compare_digest(given.encode(), TOKEN.encode()):
            return self.send(403, b"wrong token", "text/plain; charset=utf-8")
        sid = secrets.token_urlsafe(32)
        with sessions_lock:
            sessions[sid] = time.time()
            while len(sessions) > 100:  # a spike: the oldest logins go when there are too many
                sessions.pop(next(iter(sessions)))
        self.send(
            303,
            b"",
            extra={"Location": "/", "Set-Cookie": f"{COOKIE}={sid}; Path=/; HttpOnly; Secure; SameSite=Strict"},
        )

    def legacy(self, url, args: dict) -> None:
        op = url.path.rsplit("/", 1)[1]
        rel = args.get("path", "")
        command: dict = {"op": op, "path": under_root("data", rel)}
        if op == "file":
            try:
                command["offset"] = max(0, int(args.get("offset", "0")))
                command["length"] = min(MAX_LENGTH, max(1, int(args.get("length", "4096"))))
            except ValueError:
                return self.send(400, b"offset and length are integers")
        started = time.monotonic()
        try:
            body = runner_op(command)
        except Missing:
            return self.send(404, b"not found")
        except Refused as e:
            return self.send(403, str(e).encode())
        except RunnerAway as e:
            return self.send(504, str(e).encode())
        took = f"{(time.monotonic() - started) * 1000:.0f}"
        return self.send(200, body, "application/octet-stream", {"X-Spike-Ms": took})

    def route_results(self, rel: str) -> None:
        try:
            rel = check_rel(rel)
        except Refused as e:
            return self.problem(422, "file-not-allowed", "File not allowed", str(e))
        try:
            return self.send_json(200, listing(rel))
        except Missing:
            return self.problem(404, "not-found", "Not found", "the directory does not exist yet")
        except Refused as e:
            return self.problem(422, "file-not-allowed", "File not allowed", str(e))
        except RunnerAway as e:
            return self.problem(504, "runner-offline", "Runner offline", str(e))

    def route_stat(self, rel: str, args: dict) -> None:
        try:
            rel = check_rel(rel)
            if rel == "":
                raise Refused("not a file")
            return self.send_json(200, stat_entry(rel))
        except Missing:
            return self.problem(404, "not-found", "Not found", f"{rel}: no such entry")
        except Refused as e:
            return self.problem(422, "file-not-allowed", "File not allowed", str(e))
        except RunnerAway as e:
            return self.problem(504, "runner-offline", "Runner offline", str(e))

    def route_text(self, rel: str, args: dict) -> None:
        try:
            rel = check_rel(rel)
        except Refused as e:
            return self.problem(422, "file-not-allowed", "File not allowed", str(e))
        try:
            tail = int(args.get("tail", str(TAIL)))
        except ValueError:
            return self.problem(422, "validation-failed", "Invalid", "tail: an integer")
        if not 1 <= tail <= MAX_READ:
            return self.problem(422, "validation-failed", "Invalid", f"tail: from 1 to {MAX_READ}")
        range_value = self.headers.get("Range")
        byte_range = None
        if range_value is not None:
            found = _RANGE.fullmatch(range_value.strip())
            if found is None:
                return self.problem(422, "validation-failed", "Invalid", "Range: one range, bytes=<start>-[<last>]")
            last = int(found[2]) if found[2] else None
            if last is not None and last < int(found[1]):
                return self.problem(422, "validation-failed", "Invalid", "Range: the last byte is before the first")
            byte_range = (int(found[1]), last)
        try:
            status, text, extra = text_read(rel, tail, byte_range)
        except Missing:
            return self.problem(404, "not-found", "Not found", f"{rel}: no such entry")
        except RunnerAway as e:
            return self.problem(504, "runner-offline", "Runner offline", str(e))
        except Refused as e:
            message = str(e)
            if message == "binary":
                return self.problem(415, "file-not-allowed", "File not allowed", f"{rel}: not text")
            if message.startswith("the file has"):
                return self.problem(422, "validation-failed", "Invalid", f"Range: {message}")
            return self.problem(422, "file-not-allowed", "File not allowed", message)
        headers = {**HEADERS, "Content-Security-Policy": TEXT_CSP, **extra}
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def route_raw(self, rel: str, args: dict) -> None:
        if self.headers.get("Sec-Fetch-Dest") in SCRIPT_DESTS:  # step 0, first on every raw route
            return self.problem(422, "file-not-allowed", "File not allowed", "not served to a script or a worker")
        download = args.get("download") == "true"
        as_ = args.get("as")
        if as_ is not None and as_ not in AS:
            return self.problem(422, "validation-failed", "Invalid", "as: one of `image`, `tiff`, `zarr`")
        try:
            rel = check_rel(rel)
            info, size = self.file_head(rel)
        except _Answered:
            return None
        except Refused as e:
            return self.problem(422, "file-not-allowed", "File not allowed", str(e))
        try:
            return self.raw_answer(rel, as_, download, info, size)
        except _Answered:
            return None

    def raw_answer(self, rel: str, as_: str | None, download: bool, info: dict, size: int) -> None:
        name = rel.rsplit("/", 1)[-1]
        suffix = _suffix(name)
        fetched = self.headers.get("Sec-Fetch-Dest") == "empty"
        if as_ in ("tiff", "zarr") and not download and fetched:
            return self.imaging(rel, as_, name, size)  # may raise _Answered
        if size > MAX_RAW:
            return self.problem(413, "file-too-large", "File too large", f"more than {MAX_RAW} bytes")
        headers = {**HEADERS, "Vary": "Sec-Fetch-Dest"}
        media = MEDIA.get(suffix)
        # steps 4 and 5 of api §5.3.1 are checked even when the answer is an attachment
        if as_ in ("tiff", "zarr") and not download:
            if as_ == "tiff" and not name.lower().endswith((".tif", ".tiff")):
                return self.problem(422, "file-not-allowed", "File not allowed", "not a TIFF's name")
            if as_ == "zarr" and not zarr_key(rel.split("/")):
                return self.problem(422, "file-not-allowed", "File not allowed", "not a key of an OME-Zarr")
        if as_ == "image" and not download and media is not None and self.headers.get("Sec-Fetch-Dest") == "image":
            cap = MAX_SVG if media == SVG else MAX_IMAGE
            if size > cap:
                return self.problem(413, "file-too-large", "File too large", f"an image over {cap} bytes")
            try:
                check_image(media, read_bytes(rel, 0, 32))
            except Refused as e:
                return self.problem(422, "file-not-allowed", "File not allowed", str(e))
            except (Missing, RunnerAway) as e:
                return self.problem(504, "runner-offline", "Runner offline", str(e))
            headers["Content-Security-Policy"] = TEXT_CSP
            return self.stream(200, size, media, headers, chunks_of("data", rel, 0, size))
        if suffix in (".html", ".htm") and not download:  # a report: the sandbox CSP of req. 14
            headers["Content-Security-Policy"] = REPORT_CSP
            return self.stream(200, size, "text/html; charset=utf-8", headers, chunks_of("data", rel, 0, size))
        if suffix == ".pdf" and not download and as_ is None:
            # demo only: the product has no PDF viewer and sends an attachment; the demo page
            # shows the file in an <iframe>, which needs it inline
            return self.stream(200, size, "application/pdf", headers, chunks_of("data", rel, 0, size))
        headers["Content-Security-Policy"] = TEXT_CSP
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(name, safe='')}"
        return self.stream(200, size, "application/octet-stream", headers, chunks_of("data", rel, 0, size))

    def imaging(self, rel: str, as_: str, name: str, size: int) -> None:
        """An imaging read (api §5.3.1): a TIFF by one closed Range, a Zarr key whole or by one
        Range; never an attachment."""
        if as_ == "tiff" and not name.lower().endswith((".tif", ".tiff")):
            return self.problem(422, "file-not-allowed", "File not allowed", "not a TIFF's name")
        if as_ == "zarr" and not zarr_key(rel.split("/")):
            return self.problem(422, "file-not-allowed", "File not allowed", "not a key of an OME-Zarr")
        if as_ == "zarr" and size > MAX_KEY:
            return self.problem(413, "file-too-large", "File too large", f"a Zarr key over {MAX_KEY} bytes")
        headers = {**HEADERS, "Vary": "Sec-Fetch-Dest", "Accept-Ranges": "bytes", "Content-Security-Policy": TEXT_CSP}
        ranges = self.headers.get_all("Range") or []
        if len(ranges) > 1:  # two fields are two ranges (SEC-P3FU102A-02)
            return self.problem(422, "validation-failed", "Invalid", "Range: one closed range, bytes=<first>-<last>")
        if as_ == "zarr" and not ranges:
            return self.stream(200, size, "application/octet-stream", headers, chunks_of("data", rel, 0, size))
        try:
            first, last = closed_range(ranges[0] if ranges else None, size)
        except Refused as e:
            return self.problem(422, "validation-failed", "Invalid", str(e))
        if as_ == "tiff":  # step 10: the head is the TIFF's, read at the file's first opening
            try:
                head = read_bytes(rel, 0, 4)
            except (Missing, Refused, RunnerAway) as e:
                return self.problem(422, "file-not-allowed", "File not allowed", str(e))
            if head not in TIFF_HEADS:
                return self.problem(422, "file-not-allowed", "File not allowed", "not the TIFF its name says")
        headers["Content-Length"] = str(last + 1 - first)
        headers["Content-Range"] = f"bytes {first}-{last}/{size}"
        body = chunks_of("data", rel, first, last + 1)
        return self.stream(206, last + 1 - first, "application/octet-stream", headers, body)

    # -- Static -------------------------------------------------------------------------------

    def static(self, path: str) -> None:
        """A file of `ui/` under the runner's root, read through the runner; `GET /` serves
        `ui/demo.html`. The Content-Type is the extension's."""
        parts = [unquote(part) for part in path.split("/") if part != ""]
        if not parts:
            parts = ["demo.html"]
        if any(part in (".", "..") for part in parts) or any(UNSERVED.search(part) for part in parts):
            return self.send(404, b"not found")
        rel = "/".join(parts)
        try:
            info = stat_of("ui", rel)
        except Missing:
            return self.send(404, b"not found")
        except (Refused, RunnerAway) as e:
            return self.send(504, str(e).encode())
        if info["dir"]:
            return self.send(404, b"not found")
        ctype = STATIC_TYPES.get(_suffix(parts[-1]), "application/octet-stream")
        return self.stream(200, info["size"], ctype, dict(HEADERS), chunks_of("ui", rel, 0, info["size"]))

    # -- POST ---------------------------------------------------------------------------------

    def do_POST(self) -> None:
        url = urlparse(self.path)
        if not authorised(self):
            return self.send(401, b"login required")
        if url.path.startswith("/runner/reply/"):
            cid = url.path.rsplit("/", 1)[1]
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_LENGTH + 4096:
                return self.send(413, b"too large")
            body = self.rfile.read(length)
            with pending_lock:
                slot = pending.pop(cid, None)
            if slot is None:
                return self.send(410, b"nobody waits for this reply")
            slot.update(
                status=int(self.headers.get("X-Status", "200")),
                body=body,
                headers={"Content-Type": self.headers.get("Content-Type", "application/octet-stream")},
            )
            slot["event"].set()
            return self.send(204, b"")
        return self.send(404, b"not found")


class _Answered(Exception):
    """The answer was already sent by `file_head`; the route returns."""


# The demo run as `GET /runs/{id}` answers it (api §7): only what the viewers read — the name,
# the state, and the fields the screens show.
RUN = {
    "id": RUN_ID,
    "name": "Demo run",
    "state": "succeeded",
    "origin": "api",
    "created_at": "2026-11-25T09:00:00Z",
    "started_at": "2026-11-25T09:00:01Z",
    "ended_at": "2026-11-25T09:04:59Z",
    "workflow": {
        "engine": "nextflow",
        "engine_version": None,
        "location": "https://example.org/pipelines/demo",
        "name": "demo pipeline",
        "version": None,
    },
    "profiles": [],
    "target": None,
    "environment": None,
    "pinned": False,
    "failure": None,
    "head": None,
    "task_counts": {},
    "summary": {
        "tasks": {"done": 6, "total": 6, "failed": 0, "cached": 0},
        "last_failure": None,
        "stage_mode": "quarters",
    },
    "params": {},
    "stages_note": None,
    "stall": None,
    "failures": [],
    "failures_total": 0,
    "command": None,
    "parent_run_id": None,
    "resumed_as": [],
    "actions": {"resume": {"allowed": False, "reason": "not_failed_or_cancelled"}},
    "results_dir": DEMO_ROOT,
    "engine_settings": {"cleanup": None, "notemp": None},
    "default_resources": None,
    "config_file": None,
    "head_logs": [],
}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"spike server on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
