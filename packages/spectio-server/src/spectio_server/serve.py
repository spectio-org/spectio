"""`spectio serve`: one process with the app, the runner loop and the index (P1 Task 11;
architecture §7.1, §7.2; dev-env §15.3 req. 1 and "Server restart").

The start, in order, each refusal a `ServeError` (exit 2) before anything is left behind:

1. the bind address must be 127.0.0.1 (req. 1); the runs root the user's, not writable by
   others (req. 10);
2. `<db dir>/serve.lock` (flock, node-local): one server per user and node;
3. the recorded port, bound on 127.0.0.1 only; a taken port is refused, naming its owner's uid,
   never replaced by another (Assumption 10);
4. the state file `<data dir>/server.json`, created with O_EXCL (Assumption 9): one that names
   another node is refused unless `--force`; one that names this node is a dead server's, since
   the lock was free, and is replaced; it is removed at a clean stop;
5. the database, the tenancy rows, the run directories missing from the index (`rebuild.py`),
   then one runner tick (adopt the heads, replay the spools), the runner thread and uvicorn.

Local-only build (inbox #80 (a)): heads start with the local launcher only. On a SLURM
environment the runner loop is not started until the tmux launcher (P1 Task 10), and the API is
not served until sign-in (P1 Tasks 12 to 16, inbox #86). There is no token link and no server
key yet (P1 Task 12).
"""

import fcntl
import json
import logging
import os
import pwd
import signal
import socket
import threading
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import uvicorn
from sqlalchemy import Engine

from spectio.config import LOOPBACK, Settings
from spectio.runner.local import LocalLauncher
from spectio.runner.loop import RunnerLoop
from spectio.runner.rundir import open_private, private_dir, read_small, write_file
from spectio_server.app import create_app
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.rebuild import Rebuilt, rebuild_index
from spectio_server.sink import StoreSink
from spectio_server.store.db import UnsafeDatabase, _require_private_dir, default_db_dir, open_db
from spectio_server.store.writer import Writer

log = logging.getLogger(__name__)

LOCK = "serve.lock"
STATE = "server.json"


class ServeError(Exception):
    """A refusal to start; the message says why and what to do."""


@dataclass
class Booted:
    engine: Engine
    writer: Writer
    new: bool  # the database was just created
    rebuilt: Rebuilt
    loop: RunnerLoop | None  # None on a SLURM environment (P1 Task 10)

    def close(self) -> None:
        self.writer.close()
        self.engine.dispose()


@dataclass
class Started:
    sock: socket.socket
    uvicorn: uvicorn.Server
    booted: Booted
    stop: threading.Event = field(default_factory=threading.Event)

    def run(self) -> None:
        self.uvicorn.run(sockets=[self.sock])


def _user() -> str:
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return str(os.getuid())


def start_text(settings: Settings, node: str, user: str) -> str:
    port = settings.port
    page = f"http://127.0.0.1:{port}/"
    lines = [f"Spectio {version('spectio')} is running on {node}, port {port}."]
    if settings.executor == "local":
        lines.append(f"Open this page in a browser on this machine:  {page}")
    else:
        lines += [
            f"1. On your laptop, open a tunnel:  ssh -N -L 127.0.0.1:{port}:127.0.0.1:{port} "
            f"{user}@{node}",
            f"2. Then open this page:  {page}",
            "Runs are not launched or watched on a SLURM environment until the tmux launcher "
            "(P1 Task 10).",
            "The API is served in local mode only until sign-in (P1 Tasks 12 to 16).",
        ]
    lines.append("Sign-in comes with P1 Task 12: until then this build is local-only.")
    return "\n".join(lines)


def boot(settings: Settings, db_dir: Path) -> Booted:
    """Open the database, add the missing runs and make the first runner tick."""
    engine, new = open_db(db_dir)
    writer = Writer(engine)
    try:
        config = {"runs_root": str(settings.runs_root)}
        writer.submit(
            lambda conn: ensure_tenancy(
                conn, _user(), settings.executor, config, version("spectio")
            )
        ).result()
        rebuilt = rebuild_index(writer, settings.runs_root)
        log.info("index %s: %d runs added", "rebuilt" if new else "reconciled", rebuilt.added)
        loop = None
        if settings.executor == "local":
            loop = RunnerLoop(
                StoreSink(writer, settings.runs_root),
                LocalLauncher(),
                settings,
                tick_s=settings.runner.spool_s,
            )
            try:
                loop.tick()
            except Exception:  # as RunnerLoop.run does: the next tick tries again
                log.exception("first runner tick failed")
        else:
            log.warning(
                "SLURM environment: the runner loop is not started; heads need the tmux "
                "launcher (P1 Task 10), not built yet"
            )
    except BaseException:
        writer.close()
        engine.dispose()
        raise
    return Booted(engine, writer, new, rebuilt, loop)


def _lock(db_dir: Path) -> int:
    """Hold `serve.lock` until the descriptor closes; refuse when another server holds it."""
    fd = os.open(db_dir / LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pid = os.pread(fd, 32, 0).decode(errors="replace").strip()
            raise ServeError(
                f"another spectio serve (pid {pid}) runs on this node: it holds {db_dir / LOCK}"
            ) from None
        os.ftruncate(fd, 0)
        os.pwrite(fd, f"{os.getpid()}\n".encode(), 0)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _port_owner(port: int) -> int | None:
    """The uid of a socket listening on `port`, from /proc/net/tcp and tcp6."""
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(table).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if int(fields[1].rsplit(":", 1)[1], 16) == port and fields[3] == "0A":  # LISTEN
                return int(fields[7])
    return None


def _bind(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # not past a live listener
        sock.bind((LOOPBACK, port))
        sock.listen(128)
    except OSError as exc:
        sock.close()
        owner = _port_owner(port)
        who = "uid unknown" if owner is None else f"uid {owner}"
        raise ServeError(
            f"port {port} on 127.0.0.1 is taken ({who}): stop that server, or record another "
            f"port with spectio init --port; Spectio never picks one itself ({exc.strerror})"
        ) from exc
    return sock


def _record(settings: Settings, db_dir: Path) -> bytes:
    return json.dumps(
        {
            "host": socket.gethostname(),
            "port": settings.port,
            "pid": os.getpid(),
            "db_dir": str(db_dir),
            "started_at": datetime.now(UTC).isoformat(),
        }
    ).encode()


def _write_state(data_dir: Path, record: bytes, force: bool) -> None:
    with private_dir(data_dir) as fd:
        try:
            new = os.open(
                STATE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd
            )
        except FileExistsError:
            pass
        else:
            with os.fdopen(new, "wb") as f:
                f.write(record)
            return
        if not force:
            try:
                raw = read_small(fd, STATE, cap=65536)
                node = json.loads(raw or b"{}").get("host")
            except (OSError, ValueError, AttributeError) as exc:
                raise ServeError(
                    f"{data_dir / STATE} cannot be read ({exc}): check it, or start with --force"
                ) from exc
            if node != socket.gethostname():
                raise ServeError(
                    f"{data_dir / STATE} names a server on {node}: run spectio there, or start "
                    "here with --force, which replaces it"
                )
        write_file(fd, STATE, record)  # a dead server's file on this node, or --force


def _remove_state(data_dir: Path, record: bytes) -> None:
    """Remove the state file if it is still ours (another node's --force may have replaced it)."""
    try:
        with private_dir(data_dir) as fd:
            if read_small(fd, STATE, cap=65536) == record:
                os.unlink(STATE, dir_fd=fd)
    except (OSError, ValueError) as exc:
        log.warning("%s not removed: %r", data_dir / STATE, exc)


@contextmanager
def started(settings: Settings, *, force: bool = False) -> Iterator[Started]:
    """The server, booted and bound, not yet serving: `Started.run()` serves until stopped."""
    if settings.server.host != LOOPBACK:
        raise ServeError(
            f"0.0.1 binds to 127.0.0.1 only: remove host = {settings.server.host!r} "
            "from [server] in spectio.toml, or unset SPECTIO_SERVER_HOST"
        )
    try:
        os.close(open_private(settings.runs_root, ()))
    except OSError as exc:
        raise ServeError(
            f"runs root {settings.runs_root} must be a directory of yours that others cannot "
            f"write (dev-env §15.3 req. 10): {exc}"
        ) from exc
    with ExitStack() as stack:  # undone in reverse order, whatever stops the server
        try:
            db_dir = settings.db_dir or default_db_dir()
            _require_private_dir(db_dir, os.getuid())
            stack.callback(os.close, _lock(db_dir))
            sock = stack.enter_context(_bind(settings.port))
            record = _record(settings, db_dir)
            _write_state(settings.data_dir, record, force)
            stack.callback(_remove_state, settings.data_dir, record)
            booted = boot(settings, db_dir)
        except (UnsafeDatabase, OSError) as exc:  # a missing data directory, among others
            raise ServeError(str(exc)) from exc
        stack.callback(booted.close)
        config = uvicorn.Config(
            create_app(settings, booted.writer),
            host=LOOPBACK,
            port=settings.port,
            lifespan="off",
            proxy_headers=False,  # every client is on loopback: never trust X-Forwarded-*
        )
        server = Started(sock, uvicorn.Server(config), booted)
        if booted.loop is not None:
            thread = threading.Thread(
                target=booted.loop.run, args=(server.stop,), name="spectio-runner"
            )
            thread.start()
            stack.callback(thread.join)
            stack.callback(server.stop.set)
        yield server


def _stop(signum: int, frame: object) -> None:
    raise SystemExit(0)


def serve(settings: Settings, *, force: bool = False) -> None:
    """Start, print the start text and serve until Ctrl-C or SIGTERM, then stop cleanly.

    uvicorn catches both while it serves, stops, and raises the signal again: SIGTERM then
    reaches `_stop`, and Ctrl-C the default KeyboardInterrupt, so the cleanup above runs."""
    signal.signal(signal.SIGTERM, _stop)
    try:
        with started(settings, force=force) as server:
            print(start_text(settings, socket.gethostname(), _user()), flush=True)
            server.run()
    except KeyboardInterrupt:
        pass
