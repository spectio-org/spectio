"""The environments: their file, read through the server's pool, and their routes (FU-P3-86b,
-86d; api §5.4; dev-env §15.3 req. 18).

`Store` reads `environments.toml` (`spectio.envfile`) in the bounded file pool with its timeout
(req. 13), so a file system that stops answering makes it `unreachable`, never a stuck request,
and keeps the last read, which a list reuses while the file's identity is unchanged. The built-ins
come first, from `Settings`; in every state but `ok` only they are listed, and the default is the
built-in of the server's kind.

The routes (`GET`, `POST /environments`, `GET`, `PUT`, `DELETE /environments/{name}` and
`:make-default`) are mounted with the other API routers in `create_app`'s conditional set, so
they are absent wherever the API is (SEC-PRE-FU86-R1-07). `PUT` and `DELETE` need `If-Match`
with the item's ETag (`*` is refused: two tabs may edit). Each write logs its route, the name
and the old and new values, none of which is a secret (SEC-PRE-FU86-R1-10). `choose` is the
launch's reading of a name (FU-P3-86c).
"""

import hashlib
import json
import logging
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Generic, TypeVar

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from spectio import envfile
from spectio.config import Settings
from spectio.environments import NO_SLURM, RESERVED, Environment, builtins
from spectio_server.api import models
from spectio_server.api.problems import Invalid, Problem
from spectio_server.files.pool import READ_TIMEOUT_S, FilePool, Stalled

log = logging.getLogger(__name__)
router = APIRouter()

BUILTIN = RESERVED - {"new"}
Entry = tuple[Environment, bool, bool, str | None]  # environment, builtin, usable, reason
E = TypeVar("E", bound=BaseModel)


def offline(exc: Exception) -> Problem:
    return Problem(503, "runner-offline", "File system not answering", str(exc))


def _builtin_names(settings: Settings) -> list[str]:
    return [b.environment.name for b in builtins(settings)]


class Store(Generic[E]):
    """A definitions file of `kind` at its one path: `environments.toml`
    (`envfile.environments_path()`), or `catalog.toml` (`spectio.catalog`, FU-P3-87b). `noun`
    names its problems (`environments-file-unusable`); only the environments have built-ins."""

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


def _usable(env: Environment, settings: Settings) -> tuple[bool, str | None]:
    if env.executor == "slurm" and settings.executor != "slurm":
        return False, NO_SLURM
    return True, None


def _entries(settings: Settings, defined: Iterable[Environment]) -> list[Entry]:
    """The built-ins first, then the file's environments."""
    entries: list[Entry] = [
        (b.environment, True, b.usable, b.unusable_reason) for b in builtins(settings)
    ]
    return entries + [(e, False, *_usable(e, settings)) for e in defined]


def view(request: Request) -> tuple[envfile.EnvFile, list[Entry], str]:
    """The file, every environment listed (built-ins first) and the default."""
    settings: Settings = request.app.state.settings
    store: Store[Environment] = request.app.state.environments
    found = store.read(settings, request.app.state.files)
    # a file that is not `ok` has no environments and no default
    default = found.default or settings.executor  # else the built-in of the server's kind
    return found, _entries(settings, found.environments), default


def _item(entry: Entry, default: str) -> dict[str, Any]:
    env, builtin, usable, reason = entry
    return {
        **env.model_dump(mode="json"),
        "builtin": builtin,
        "default": env.name == default,
        "usable": usable,
        "unusable_reason": reason,
        "etag": etag(env),
    }


def _not_found(found: envfile.EnvFile) -> Problem:
    if found.state == "unreachable":
        return offline(Stalled(found.detail or "the environments file is unreachable"))
    why = "" if found.state in ("missing", "ok") else f" (the environments file is {found.state})"
    return Problem(404, "not-found", "Not found", f"No such environment{why}.")


def _entry(request: Request, name: str) -> tuple[Entry, str]:
    found, entries, default = view(request)
    for entry in entries:
        if entry[0].name == name:
            return entry, default
    raise _not_found(found)


def choose(request: Request, name: str | None) -> Environment:
    """The environment a launch names, or the default (FU-P3-86c, api §5.4): `422` on
    `environment` when it is unknown, not usable or `slurm` on a local server, `503` while the
    file is unreachable and the name is not a built-in."""
    found, entries, default = view(request)
    wanted = default if name is None else name
    for env, _, usable, reason in entries:
        if env.name == wanted:
            if not usable:
                raise Invalid("environment", reason or "not usable on this server")
            return env
    if wanted == "slurm":
        raise Invalid("environment", NO_SLURM)
    if found.state == "unreachable":
        raise _not_found(found)
    if found.state != "ok" and found.state != "missing":
        raise Invalid("environment", f"the environments file is {found.state}: {found.detail}")
    raise Invalid("environment", f"there is no environment {wanted}")


@router.get("/environments", response_model=models.EnvironmentList)
def list_environments(request: Request) -> dict[str, Any]:
    found, entries, default = view(request)
    store: Store[Environment] = request.app.state.environments
    return {
        "items": [_item(e, default) for e in entries],
        "default": default,
        "file": {"path": str(store.path), "state": found.state, "detail": found.detail},
    }


@router.get("/environments/{name}", response_model=models.EnvironmentItem)
def get_environment(request: Request, response: Response, name: str) -> dict[str, Any]:
    entry, default = _entry(request, name)
    response.headers["ETag"] = etag(entry[0])
    return _item(entry, default)


def _check(body: Environment, settings: Settings) -> None:
    if body.name in RESERVED:
        kind = "a reserved" if body.name == "new" else "a built-in"
        raise Invalid("name", f"{body.name} is {kind} name")
    if not _usable(body, settings)[0]:
        raise Invalid("executor", NO_SLURM)


def _builtin(name: str) -> None:
    if name in BUILTIN:
        detail = f"{name} is built in: it cannot be changed; duplicate it into a new name."
        raise Problem(409, "environment-builtin", "Built-in environment", detail)


def if_match(request: Request, what: str = "environment") -> set[str]:
    value = request.headers.get("if-match")
    tags = {t.strip() for t in (value or "").split(",") if t.strip()}
    if not tags or "*" in tags:
        detail = f"Send the {what}'s ETag in If-Match; * is not accepted."
        raise Problem(428, "if-match-required", "If-Match required", detail)
    return tags


def _find(current: envfile.EnvFile, name: str, tags: set[str]) -> Environment:
    for env in current.environments:
        if env.name == name:
            if etag(env) not in tags:
                detail = "The environment changed since it was read: read it again."
                raise Problem(412, "etag-mismatch", "ETag mismatch", detail)
            return env
    raise _not_found(current)


def _values(found: envfile.EnvFile, name: str) -> dict[str, Any]:
    env = next((e for e in found.environments if e.name == name), None)
    return {"default": found.default, name: None if env is None else env.model_dump(mode="json")}


def _write(request: Request, route: str, name: str, change: envfile.Change) -> None:
    store: Store[Environment] = request.app.state.environments
    old: list[dict[str, Any]] = []

    def logged(current: envfile.EnvFile) -> tuple[str | None, list[Environment]]:
        old.append(_values(current, name))
        return change(current)

    written = store.update(request.app.state.settings, request.app.state.files, logged)
    log.info("environments %s %s: %s -> %s", route, name, old[0], _values(written, name))


@router.post("/environments", status_code=201, response_model=models.EnvironmentItem)
def create_environment(body: Environment, request: Request, response: Response) -> dict[str, Any]:
    _check(body, request.app.state.settings)

    def change(current: envfile.EnvFile) -> tuple[str | None, list[Environment]]:
        if any(e.name == body.name for e in current.environments):
            detail = f"An environment named {body.name} exists."
            raise Problem(409, "environment-exists", "Environment exists", detail)
        if len(current.environments) >= envfile.MAX_ENVIRONMENTS:
            raise Invalid("name", f"at most {envfile.MAX_ENVIRONMENTS} environments")
        return current.default, [*current.environments, body]

    _write(request, "POST /environments", body.name, change)
    entry, default = _entry(request, body.name)
    response.headers["Location"] = f"/api/v1/environments/{body.name}"
    response.headers["ETag"] = etag(entry[0])
    return _item(entry, default)


@router.put("/environments/{name}", response_model=models.EnvironmentItem)
def replace_environment(
    name: str, body: Environment, request: Request, response: Response
) -> dict[str, Any]:
    _builtin(name)
    tags = if_match(request)
    if body.name != name:
        raise Invalid("name", "a name cannot change: duplicate the environment, then delete it")
    _check(body, request.app.state.settings)

    def change(current: envfile.EnvFile) -> tuple[str | None, list[Environment]]:
        _find(current, name, tags)
        return current.default, [body if e.name == name else e for e in current.environments]

    _write(request, "PUT /environments/{name}", name, change)
    entry, default = _entry(request, name)
    response.headers["ETag"] = etag(entry[0])
    return _item(entry, default)


@router.delete("/environments/{name}", status_code=204)
def delete_environment(name: str, request: Request) -> Response:
    _builtin(name)
    tags = if_match(request)

    def change(current: envfile.EnvFile) -> tuple[str | None, list[Environment]]:
        _find(current, name, tags)
        default = None if current.default == name else current.default  # the built-in's again
        return default, [e for e in current.environments if e.name != name]

    _write(request, "DELETE /environments/{name}", name, change)
    return Response(status_code=204)


@router.post("/environments/{name}:make-default", status_code=204)
def make_default(name: str, request: Request) -> Response:
    settings: Settings = request.app.state.settings

    def change(current: envfile.EnvFile) -> tuple[str | None, list[Environment]]:
        for env, _, usable, reason in _entries(settings, current.environments):
            if env.name == name:
                if not usable:
                    raise Invalid("name", reason or "not usable on this server")
                return name, list(current.environments)
        raise _not_found(current)

    _write(request, "POST /environments/{name}:make-default", name, change)
    return Response(status_code=204)
