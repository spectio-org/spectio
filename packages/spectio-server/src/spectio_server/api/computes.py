"""Computes and execution profiles: their files and routes (#408; api §5.13).

`computes.toml` and `execution-profiles.toml` are read and written by `environments.Store`
(`spectio.envfile`: the pool, timeout, five states, identity check, lock and rename), with the
`compute-file-*` and `execution-profile-file-*` problems. The routes (`GET`, `POST`, `GET`, `PUT`,
`DELETE` of `/computes` and of `/execution-profiles`) are mounted in `create_app`'s conditional
set, so they are absent wherever the API is. `PUT` and `DELETE` need `If-Match` with the item's
ETag (`*` is refused). Each write logs its route, the name and the old and new values.

The first read of either file migrates `environments.toml` (`migrate`). `choose` is the launch's
reading of a profile name: it resolves the profile and its compute into the run's snapshot.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, Request, Response

from spectio import envfile
from spectio.catalog import Entry
from spectio.computes import (
    MAX_COMPUTES,
    MAX_PROFILES,
    Compute,
    ExecutionProfile,
    builtins,
    check,
    resolve,
    split,
)
from spectio.config import Settings
from spectio.environments import NO_SLURM, RESERVED, Snapshot
from spectio_server.api import models
from spectio_server.api.environments import Store, etag, if_match, offline
from spectio_server.api.problems import Invalid, Problem
from spectio_server.files.pool import Stalled

log = logging.getLogger(__name__)
router = APIRouter()

BUILTIN = RESERVED - {"new"}
CEntry = tuple[Compute, bool, bool, str | None]  # compute, builtin, usable, reason
PEntry = tuple[ExecutionProfile, bool]  # profile, builtin
Noun = Literal["compute", "execution-profile"]


@dataclass(frozen=True)
class Chosen:
    """What a launch runs with: the snapshot, and the profile it came from."""

    env: Snapshot
    profile: ExecutionProfile


# --- Migration of environments.toml, on the first read ---------------------------------------


def migrate(request: Request) -> None:
    """Once per server process, before the first read of either file: each environment of
    `environments.toml` becomes the compute and the profile of its name (`computes.split`), in
    each file that does not exist yet, and `default` goes to the profiles file. Idempotent:
    `environments.toml` is left as it is, a file that exists is never rewritten, and a file that
    is not `ok` (or an unreachable one, tried again by the next read) migrates nothing."""
    state = request.app.state
    if state.migrated:
        return
    settings, files = state.settings, state.files
    old = state.environments.read(settings, files)
    if old.state == "unreachable":
        return
    if old.state == "ok":
        pairs = [split(e) for e in old.entries]
        computes, profiles = [c for c, _ in pairs], [p for _, p in pairs]
        for store, entries, default in (
            (state.computes, computes, None),
            (state.profiles, profiles, old.default),
        ):
            if store.read(settings, files).state == "missing":
                store.update(settings, files, _create_once(entries, default))
                log.info("environments migrated into %s: %d entries", store.kind.file, len(entries))
    state.migrated = True


def _create_once(entries: list[Any], default: str | None) -> Callable[[Any], Any]:
    def change(current: envfile.File[Any]) -> tuple[str | None, list[Any]]:
        if current.state == "missing":
            return default, entries
        return current.default, list(current.entries)  # another request got there first

    return change


# --- The two lists, built-ins first ----------------------------------------------------------


def _usable(compute: Compute, settings: Settings) -> tuple[bool, str | None]:
    if compute.executor == "slurm" and settings.executor != "slurm":
        return False, NO_SLURM
    return True, None


def computes_view(request: Request) -> tuple[envfile.File[Compute], list[CEntry]]:
    """The file and every compute listed: the built-ins, then the file's."""
    migrate(request)
    state = request.app.state
    found: envfile.File[Compute] = state.computes.read(state.settings, state.files)
    entries: list[CEntry] = [
        (b.compute, True, b.usable, b.unusable_reason) for b in builtins(state.settings)
    ]
    return found, entries + [(c, False, *_usable(c, state.settings)) for c in found.entries]


def profiles_view(
    request: Request,
) -> tuple[envfile.File[ExecutionProfile], list[PEntry], str]:
    """The file, every profile listed (built-ins first) and the default: the file's, else the
    built-in of the server's kind."""
    migrate(request)
    state = request.app.state
    found: envfile.File[ExecutionProfile] = state.profiles.read(state.settings, state.files)
    entries: list[PEntry] = [(b.profile, True) for b in builtins(state.settings)]
    entries += [(p, False) for p in found.entries]
    return found, entries, found.default or state.settings.executor


def _compute_item(entry: CEntry) -> dict[str, Any]:
    compute, builtin, usable, reason = entry
    return {
        **compute.model_dump(mode="json"),
        "builtin": builtin,
        "usable": usable,
        "unusable_reason": reason,
        "etag": etag(compute),
    }


def _profile_item(entry: PEntry, default: str) -> dict[str, Any]:
    profile, builtin = entry
    return {
        **profile.model_dump(mode="json"),
        "builtin": builtin,
        "default": profile.name == default,
        "etag": etag(profile),
    }


def _file(store: Store[Any], found: envfile.File[Any]) -> dict[str, Any]:
    return {"path": str(store.path), "state": found.state, "detail": found.detail}


def _words(noun: str) -> str:
    return noun.replace("-", " ")


def _not_found(found: envfile.File[Any], noun: Noun) -> Problem:
    if found.state == "unreachable":
        return offline(Stalled(found.detail or f"the {_words(noun)}s file is unreachable"))
    why = (
        "" if found.state in ("missing", "ok") else f" (the {_words(noun)}s file is {found.state})"
    )
    return Problem(404, "not-found", "Not found", f"No such {_words(noun)}{why}.")


def _find(current: envfile.File[Any], name: str, tags: set[str], noun: Noun) -> None:
    for entry in current.entries:
        if entry.name == name:
            if etag(entry) not in tags:
                detail = f"The {_words(noun)} changed since it was read: read it again."
                raise Problem(412, "etag-mismatch", "ETag mismatch", detail)
            return
    raise _not_found(current, noun)


def _builtin(name: str, noun: Noun) -> None:
    if name in BUILTIN:
        detail = f"{name} is built in: it cannot be changed; duplicate it into a new name."
        raise Problem(409, f"{noun}-builtin", f"Built-in {_words(noun)}", detail)


def _reserved(name: str) -> None:
    if name in RESERVED:
        kind = "a reserved" if name == "new" else "a built-in"
        raise Invalid("name", f"{name} is {kind} name")


def _values(found: envfile.File[Any], name: str) -> dict[str, Any]:
    entry = next((e for e in found.entries if e.name == name), None)
    return {
        "default": found.default,
        name: None if entry is None else entry.model_dump(mode="json"),
    }


def _write(
    request: Request,
    store: Store[Any],
    route: str,
    name: str,
    change: Callable[[Any], tuple[str | None, list[Any]]],
) -> None:
    old: list[dict[str, Any]] = []

    def logged(current: envfile.File[Any]) -> tuple[str | None, list[Any]]:
        old.append(_values(current, name))
        return change(current)

    written = store.update(request.app.state.settings, request.app.state.files, logged)
    log.info("%s %s: %s -> %s", route, name, old[0], _values(written, name))


# --- Computes --------------------------------------------------------------------------------


def _check_compute(body: Compute, settings: Settings) -> None:
    _reserved(body.name)
    if not _usable(body, settings)[0]:
        raise Invalid("executor", NO_SLURM)


def _compute_entry(request: Request, name: str) -> CEntry:
    found, entries = computes_view(request)
    for entry in entries:
        if entry[0].name == name:
            return entry
    raise _not_found(found, "compute")


@router.get("/computes", response_model=models.ComputeList)
def list_computes(request: Request) -> dict[str, Any]:
    found, entries = computes_view(request)
    return {
        "items": [_compute_item(e) for e in entries],
        "file": _file(request.app.state.computes, found),
    }


@router.get("/computes/{name}", response_model=models.ComputeItem)
def get_compute(request: Request, response: Response, name: str) -> dict[str, Any]:
    entry = _compute_entry(request, name)
    response.headers["ETag"] = etag(entry[0])
    return _compute_item(entry)


@router.post("/computes", status_code=201, response_model=models.ComputeItem)
def create_compute(body: Compute, request: Request, response: Response) -> dict[str, Any]:
    _check_compute(body, request.app.state.settings)

    def change(current: envfile.File[Compute]) -> tuple[str | None, list[Compute]]:
        if any(c.name == body.name for c in current.entries):
            detail = f"A compute named {body.name} exists."
            raise Problem(409, "compute-exists", "Compute exists", detail)
        if len(current.entries) >= MAX_COMPUTES:
            raise Invalid("name", f"at most {MAX_COMPUTES} computes")
        return None, [*current.entries, body]

    _write(request, request.app.state.computes, "POST /computes", body.name, change)
    response.headers["Location"] = f"/api/v1/computes/{body.name}"
    response.headers["ETag"] = etag(body)
    return _compute_item(_compute_entry(request, body.name))


@router.put("/computes/{name}", response_model=models.ComputeItem)
def replace_compute(
    name: str, body: Compute, request: Request, response: Response
) -> dict[str, Any]:
    _builtin(name, "compute")
    tags = if_match(request, "compute")
    if body.name != name:
        raise Invalid("name", "a name cannot change: duplicate the compute, then delete it")
    _check_compute(body, request.app.state.settings)

    def change(current: envfile.File[Compute]) -> tuple[str | None, list[Compute]]:
        _find(current, name, tags, "compute")
        return None, [body if c.name == name else c for c in current.entries]

    _write(request, request.app.state.computes, "PUT /computes/{name}", name, change)
    response.headers["ETag"] = etag(body)
    return _compute_item(_compute_entry(request, name))


@router.delete("/computes/{name}", status_code=204)
def delete_compute(name: str, request: Request) -> Response:
    _builtin(name, "compute")
    tags = if_match(request, "compute")
    _, profiles, _ = profiles_view(request)
    users = [p.name for p, _ in profiles if p.compute == name]
    if users:
        detail = f"The compute {name} is used by the execution profile(s) {', '.join(users[:5])}."
        raise Problem(409, "compute-in-use", "Compute in use", detail)

    def change(current: envfile.File[Compute]) -> tuple[str | None, list[Compute]]:
        _find(current, name, tags, "compute")
        return None, [c for c in current.entries if c.name != name]

    _write(request, request.app.state.computes, "DELETE /computes/{name}", name, change)
    return Response(status_code=204)


# --- Execution profiles ----------------------------------------------------------------------


def _compute_of(request: Request, name: str, field: str) -> Compute:
    """The usable compute a profile names, else 422 on `field` (503 while the file is
    unreachable)."""
    found, entries = computes_view(request)
    for compute, _, usable, reason in entries:
        if compute.name == name:
            if not usable:
                raise Invalid(field, reason or "not usable on this server")
            return compute
    if found.state == "unreachable":
        raise _not_found(found, "compute")
    if found.state not in ("ok", "missing"):
        raise Invalid(field, f"the computes file is {found.state}: {found.detail}")
    raise Invalid(field, f"there is no compute {name}")


def _check_profile(body: ExecutionProfile, request: Request) -> None:
    _reserved(body.name)
    compute = _compute_of(request, body.compute, "compute")
    if (problem := check(compute, body)) is not None:
        raise Invalid(*problem)


def choose(request: Request, name: str | None, field: str = "execution_profile") -> Chosen:
    """The profile a launch names, or the default, with its compute (api §5.13): `422` on `field`
    when it is unknown, its compute is missing or not usable, or the pair breaks `check`; `503`
    while a file is unreachable and the name is not a built-in."""
    found, entries, default = profiles_view(request)
    wanted = default if name is None else name
    profile = next((p for p, _ in entries if p.name == wanted), None)
    if profile is None:
        if wanted == "slurm":
            raise Invalid(field, NO_SLURM)
        if found.state == "unreachable":
            raise _not_found(found, "execution-profile")
        if found.state not in ("ok", "missing"):
            raise Invalid(field, f"the execution profiles file is {found.state}: {found.detail}")
        raise Invalid(field, f"there is no execution profile {wanted}")
    compute = _compute_of(request, profile.compute, field)
    if (problem := check(compute, profile)) is not None:
        raise Invalid(field, f"{profile.name}: {problem[1]}")
    return Chosen(resolve(compute, profile), profile)


def _profile_entry(request: Request, name: str) -> tuple[PEntry, str]:
    found, entries, default = profiles_view(request)
    for entry in entries:
        if entry[0].name == name:
            return entry, default
    raise _not_found(found, "execution-profile")


def _catalog_users(request: Request, name: str) -> list[str]:
    """The catalog entries that name the profile, in `profiles` or as the default."""
    found = request.app.state.catalog.read(request.app.state.settings, request.app.state.files)
    entries: list[Entry] = list(found.entries)
    return [e.name for e in entries if name in (e.profiles or []) or e.default_profile == name]


@router.get("/execution-profiles", response_model=models.ExecutionProfileList)
def list_profiles(request: Request) -> dict[str, Any]:
    found, entries, default = profiles_view(request)
    return {
        "items": [_profile_item(e, default) for e in entries],
        "default": default,
        "file": _file(request.app.state.profiles, found),
    }


@router.get("/execution-profiles/{name}", response_model=models.ExecutionProfileItem)
def get_profile(request: Request, response: Response, name: str) -> dict[str, Any]:
    entry, default = _profile_entry(request, name)
    response.headers["ETag"] = etag(entry[0])
    return _profile_item(entry, default)


@router.post("/execution-profiles", status_code=201, response_model=models.ExecutionProfileItem)
def create_profile(body: ExecutionProfile, request: Request, response: Response) -> dict[str, Any]:
    _check_profile(body, request)

    def change(
        current: envfile.File[ExecutionProfile],
    ) -> tuple[str | None, list[ExecutionProfile]]:
        if any(p.name == body.name for p in current.entries):
            detail = f"An execution profile named {body.name} exists."
            raise Problem(409, "execution-profile-exists", "Execution profile exists", detail)
        if len(current.entries) >= MAX_PROFILES:
            raise Invalid("name", f"at most {MAX_PROFILES} execution profiles")
        return current.default, [*current.entries, body]

    store = request.app.state.profiles
    _write(request, store, "POST /execution-profiles", body.name, change)
    entry, default = _profile_entry(request, body.name)
    response.headers["Location"] = f"/api/v1/execution-profiles/{body.name}"
    response.headers["ETag"] = etag(body)
    return _profile_item(entry, default)


@router.put("/execution-profiles/{name}", response_model=models.ExecutionProfileItem)
def replace_profile(
    name: str, body: ExecutionProfile, request: Request, response: Response
) -> dict[str, Any]:
    _builtin(name, "execution-profile")
    tags = if_match(request, "execution profile")
    if body.name != name:
        raise Invalid("name", "a name cannot change: duplicate the profile, then delete it")
    _check_profile(body, request)

    def change(
        current: envfile.File[ExecutionProfile],
    ) -> tuple[str | None, list[ExecutionProfile]]:
        _find(current, name, tags, "execution-profile")
        return current.default, [body if p.name == name else p for p in current.entries]

    _write(request, request.app.state.profiles, "PUT /execution-profiles/{name}", name, change)
    entry, default = _profile_entry(request, name)
    response.headers["ETag"] = etag(body)
    return _profile_item(entry, default)


@router.delete("/execution-profiles/{name}", status_code=204)
def delete_profile(name: str, request: Request) -> Response:
    _builtin(name, "execution-profile")
    tags = if_match(request, "execution profile")
    users = _catalog_users(request, name)
    if users:
        detail = (
            f"The execution profile {name} is named by the catalog entry {', '.join(users[:5])}."
        )
        raise Problem(409, "execution-profile-in-use", "Execution profile in use", detail)

    def change(
        current: envfile.File[ExecutionProfile],
    ) -> tuple[str | None, list[ExecutionProfile]]:
        _find(current, name, tags, "execution-profile")
        default = None if current.default == name else current.default  # the built-in's again
        return default, [p for p in current.entries if p.name != name]

    _write(request, request.app.state.profiles, "DELETE /execution-profiles/{name}", name, change)
    return Response(status_code=204)
