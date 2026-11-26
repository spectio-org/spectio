"""The definitions files the routes share: their `Store`, ETags and `If-Match` (FU-P3-86b, -86d;
api §5.4, §5.13; dev-env §15.3 req. 18).

`Store` reads one definitions file (`spectio.envfile`: `computes.toml`, `execution-profiles.toml`,
`catalog.toml`, and `environments.toml` for the migration of #408) in the bounded file pool with
its timeout (req. 13), so a file system that stops answering makes it `unreachable`, never a
stuck request, and keeps the last read, which a list reuses while the file's identity is
unchanged. `PUT` and `DELETE` need `If-Match` with the item's ETag (`*` is refused: two tabs may
edit). The environments' own routes ended with #408: `api.computes` serves their successors.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Generic, TypeVar

from fastapi import Request
from pydantic import BaseModel

from spectio import envfile
from spectio.config import Settings
from spectio.environments import builtins
from spectio_server.api.problems import Problem
from spectio_server.files.pool import READ_TIMEOUT_S, FilePool, Stalled

log = logging.getLogger(__name__)

E = TypeVar("E", bound=BaseModel)


def offline(exc: Exception) -> Problem:
    return Problem(503, "runner-offline", "File system not answering", str(exc))


def _builtin_names(settings: Settings) -> list[str]:
    return [b.environment.name for b in builtins(settings)]


class Store(Generic[E]):
    """A definitions file of `kind` at its one path (`Kind.path()`). `noun` names its problems
    (`catalog-file-unusable`); a file with a `default` may name a built-in there."""

    def __init__(self, path: Path, kind: envfile.Kind[E], noun: str) -> None:
        self.path, self.kind, self.noun = path, kind, noun
        self._cached: envfile.File[E] | None = None

    def _names(self, settings: Settings) -> list[str]:
        return _builtin_names(settings) if self.kind.has_default else []

    def read(self, settings: Settings, files: FilePool) -> envfile.File[E]:
        names, cached = self._names(settings), self._cached
        try:
            found = files.run(
                lambda: envfile.read_kind(self.kind, self.path, names, cached), READ_TIMEOUT_S
            )
        except Stalled as exc:
            return envfile.File("unreachable", str(exc))
        if found.identity is not None:
            self._cached = found
        return found

    def update(
        self,
        settings: Settings,
        files: FilePool,
        change: Callable[[envfile.File[E]], tuple[str | None, list[E]]],
    ) -> envfile.File[E]:
        """`envfile.update_kind` in the pool. A write whose answer timed out may still land: the
        client reads the list again. The lock is waited for here, in the request's thread, never
        in a pool worker (dev-env §15.3 req. 13, SEC-P3FU86BCD-02); the job releases it."""
        names, noun = self._names(settings), self.noun
        try:
            if not envfile.WRITE.acquire(timeout=envfile.LOCK_TIMEOUT_S):
                raise Stalled(f"another write of {self.kind.file} has not ended")
            return files.run(
                lambda: envfile.update_kind(self.kind, self.path, names, change, locked=True),
                READ_TIMEOUT_S,
                on_done=envfile.WRITE.release,
            )
        except Stalled as exc:
            raise offline(exc) from None
        except OSError as exc:  # ENOSPC, EDQUOT, EIO on the write (CR-P3FU86BCD-01)
            detail = f"the {noun} file cannot be written: {exc.strerror}"
            raise offline(Exception(detail)) from None
        except envfile.Unusable as exc:
            detail = f"The {noun} file is {exc.state}: {exc.detail}"
            title = f"{noun.capitalize()} file unusable"
            raise Problem(409, f"{noun}-file-unusable", title, detail) from None
        except envfile.Changed as exc:
            title = f"{noun.capitalize()} file changed"
            raise Problem(409, f"{noun}-file-changed", title, str(exc)) from None


def etag(env: BaseModel) -> str:
    """A strong ETag of the definition (api §5.4: per item; a catalog entry's too, §5.6)."""
    text = json.dumps(env.model_dump(mode="json"), sort_keys=True)
    return f'"{hashlib.sha256(text.encode()).hexdigest()[:32]}"'


def if_match(request: Request, what: str = "environment") -> set[str]:
    value = request.headers.get("if-match")
    tags = {t.strip() for t in (value or "").split(",") if t.strip()}
    if not tags or "*" in tags:
        detail = f"Send the {what}'s ETag in If-Match; * is not accepted."
        raise Problem(428, "if-match-required", "If-Match required", detail)
    return tags
