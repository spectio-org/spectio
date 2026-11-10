"""`GET /me` in 0.0.1: who the server runs as, this session and the config paths, for the
Profile page (ui-spec §4.10.1, api §5.8; FU-P3-112).

Single-user mode: the principal is the Unix user the server runs as. Behind the session, as
every route; it answers paths only, never a secret, a token or a file's contents, and
`Cache-Control: no-store`. The session never expires on its own: it lives in memory until the
server stops or it signs out (`auth.routes`), so `expires_at` is null.
"""

import os
import pwd
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response

from spectio.config import config_path
from spectio_server.api import models
from spectio_server.auth.middleware import cookie_name

router = APIRouter(tags=["me"])


def _user(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


@router.get("/me", response_model=models.Me)
def me(request: Request, response: Response) -> dict[str, Any]:
    state = request.app.state
    secret = request.cookies.get(cookie_name(request.headers.get("host")), "")
    uid = os.getuid()
    started = state.sessions.started(secret)
    response.headers["Cache-Control"] = "no-store"
    return {
        "principal": {"user": _user(uid), "uid": uid},
        "session": {
            "started_at": None if started is None else started.isoformat(),
            "expires_at": None,
        },
        "paths": {
            "config_file": str(config_path()),
            "data_dir": str(state.settings.data_dir),
            "db_dir": str(Path(state.writer.engine.url.database).parent),
            "observed_dir": str(Path.home() / ".spectio" / "observed"),
        },
    }
