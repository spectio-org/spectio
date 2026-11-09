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
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response

from spectio import envfile
from spectio.config import Settings
from spectio.environments import NO_SLURM, RESERVED, Environment, builtins
from spectio_server.api import models
from spectio_server.api.problems import Invalid, Problem
from spectio_server.files.pool import READ_TIMEOUT_S, FilePool, Stalled

log = logging.getLogger(__name__)
router = APIRouter()

BUILTIN = frozenset({"local", "slurm"})
Entry = tuple[Environment, bool, bool, str | None]  # environment, builtin, usable, reason


def _offline(exc: Exception) -> Problem:
    return Problem(503, "runner-offline", "File system not answering", str(exc))


def _builtin_names(settings: Settings) -> list[str]:
    return [b.environment.name for b in builtins(settings)]


class Store:
    """`environments.toml` at its one path (`envfile.environments_path()`)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._cached: envfile.EnvFile | None = None

    def read(self, settings: Settings, files: FilePool) -> envfile.EnvFile:
        names, cached = _builtin_names(settings), self._cached
        try:
            found = files.run(lambda: envfile.read_file(self.path, names, cached), READ_TIMEOUT_S)
        except Stalled as exc:
            return envfile.EnvFile("unreachable", str(exc))
        if found.identity is not None:
            self._cached = found
        return found

    def update(
        self, settings: Settings, files: FilePool, change: envfile.Change
    ) -> envfile.EnvFile:
        """`envfile.update` in the pool. A write whose answer timed out may still land: the
        client reads the list again."""
        names = _builtin_names(settings)
        try:
            return files.run(lambda: envfile.update(self.path, names, change), READ_TIMEOUT_S)
        except Stalled as exc:
            raise _offline(exc) from None
        except OSError as exc:  # ENOSPC, EDQUOT, EIO on the write (CR-P3FU86BCD-01)
            detail = f"the environments file cannot be written: {exc.strerror}"
            raise _offline(Exception(detail)) from None
        except envfile.Unusable as exc:
            detail = f"The environments file is {exc.state}: {exc.detail}"
            raise Problem(
                409, "environments-file-unusable", "Environments file unusable", detail
            ) from None
        except envfile.Changed as exc:
            title = "Environments file changed"
            raise Problem(409, "environments-file-changed", title, str(exc)) from None


def etag(env: Environment) -> str:
    """A strong ETag of the definition (api §5.4: per item)."""
    text = json.dumps(env.model_dump(mode="json"), sort_keys=True)
    return f'"{hashlib.sha256(text.encode()).hexdigest()[:32]}"'


def _usable(env: Environment, settings: Settings) -> tuple[bool, str | None]:
    if env.executor == "slurm" and settings.executor != "slurm":
        return False, NO_SLURM
    return True, None


def view(request: Request) -> tuple[envfile.EnvFile, list[Entry], str]:
    """The file, every environment listed (built-ins first) and the default."""
    settings: Settings = request.app.state.settings
    store: Store = request.app.state.environments
    found = store.read(settings, request.app.state.files)
    entries: list[Entry] = [
        (b.environment, True, b.usable, b.unusable_reason) for b in builtins(settings)
    ]
    default: str = settings.executor  # the built-in of the server's kind
    if found.state == "ok":
        entries += [(e, False, *_usable(e, settings)) for e in found.environments]
        default = found.default or default
    return found, entries, default


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
        return _offline(Stalled(found.detail or "the environments file is unreachable"))
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
    store: Store = request.app.state.environments
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


def _if_match(request: Request) -> set[str]:
    value = request.headers.get("if-match")
    tags = {t.strip() for t in (value or "").split(",") if t.strip()}
    if not tags or "*" in tags:
        detail = "Send the environment's ETag in If-Match; * is not accepted."
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
    store: Store = request.app.state.environments
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
    tags = _if_match(request)
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
    tags = _if_match(request)

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
        entries: list[Entry] = [
            (b.environment, True, b.usable, b.unusable_reason) for b in builtins(settings)
        ]
        entries += [(e, False, *_usable(e, settings)) for e in current.environments]
        for env, _, usable, reason in entries:
            if env.name == name:
                if not usable:
                    raise Invalid("name", reason or "not usable on this server")
                return name, list(current.environments)
        raise _not_found(current)

    _write(request, "POST /environments/{name}:make-default", name, change)
    return Response(status_code=204)
