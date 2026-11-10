"""The pipeline catalog's routes (FU-P3-87b; api §5.6; dev-env §15.3 req. 18).

`catalog.toml` is read and written by the environments' `Store` (`spectio.envfile`: the same
pool, timeout, five states, identity check, lock and rename), with the `catalog-file-*`
problems. The routes (`GET`, `POST /catalog`, `GET`, `PUT`, `DELETE /catalog/{name}`) are
mounted in `create_app`'s conditional set, as the environments'. Saving checks how the fields
are written (`spectio.catalog.Entry`), never what they name: no directory is read and no remote
contacted. `PUT` and `DELETE` need `If-Match` with the item's ETag (`*` is refused). Each write
logs its route, the name and the old and new values.
"""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request, Response

from spectio import envfile
from spectio.catalog import MAX_ENTRIES, Entry
from spectio_server.api import models
from spectio_server.api.environments import Store, etag, if_match, offline
from spectio_server.api.problems import Invalid, Problem
from spectio_server.files.pool import Stalled

log = logging.getLogger(__name__)
router = APIRouter()

CatalogFile = envfile.File[Entry]
Change = Callable[[CatalogFile], list[Entry]]  # the current file → its new entries


def _read(request: Request) -> CatalogFile:
    store: Store[Entry] = request.app.state.catalog
    return store.read(request.app.state.settings, request.app.state.files)


def _item(entry: Entry) -> dict[str, Any]:
    return {**entry.model_dump(mode="json"), "etag": etag(entry)}


def _not_found(found: CatalogFile) -> Problem:
    if found.state == "unreachable":
        return offline(Stalled(found.detail or "the catalog file is unreachable"))
    why = "" if found.state in ("missing", "ok") else f" (the catalog file is {found.state})"
    return Problem(404, "not-found", "Not found", f"No such catalog entry{why}.")


def _get(found: CatalogFile, name: str) -> Entry:
    entry = next((e for e in found.entries if e.name == name), None)
    if entry is None:
        raise _not_found(found)
    return entry


def _find(current: CatalogFile, name: str, tags: set[str]) -> None:
    if etag(_get(current, name)) not in tags:
        detail = "The catalog entry changed since it was read: read it again."
        raise Problem(412, "etag-mismatch", "ETag mismatch", detail)


def _value(found: CatalogFile, name: str) -> dict[str, Any] | None:
    entry = next((e for e in found.entries if e.name == name), None)
    return None if entry is None else entry.model_dump(mode="json")


def _write(request: Request, route: str, name: str, change: Change) -> None:
    store: Store[Entry] = request.app.state.catalog
    old: list[dict[str, Any] | None] = []

    def logged(current: CatalogFile) -> tuple[str | None, list[Entry]]:
        old.append(_value(current, name))
        return None, change(current)

    written = store.update(request.app.state.settings, request.app.state.files, logged)
    log.info("catalog %s %s: %s -> %s", route, name, old[0], _value(written, name))


@router.get("/catalog", response_model=models.CatalogList)
def list_catalog(request: Request) -> dict[str, Any]:
    found = _read(request)
    store: Store[Entry] = request.app.state.catalog
    return {
        "items": [_item(e) for e in found.entries],  # in name order; none unless `ok`
        "file": {"path": str(store.path), "state": found.state, "detail": found.detail},
    }


@router.get("/catalog/{name}", response_model=models.CatalogItem)
def get_entry(request: Request, response: Response, name: str) -> dict[str, Any]:
    entry = _get(_read(request), name)
    response.headers["ETag"] = etag(entry)
    return _item(entry)


@router.post("/catalog", status_code=201, response_model=models.CatalogItem)
def create_entry(body: Entry, request: Request, response: Response) -> dict[str, Any]:
    if body.name == "new":  # the screen route `/catalog/new`
        raise Invalid("name", "new is a reserved name")

    def change(current: CatalogFile) -> list[Entry]:
        if any(e.name == body.name for e in current.entries):
            detail = f"A catalog entry named {body.name} exists."
            raise Problem(409, "catalog-entry-exists", "Catalog entry exists", detail)
        if len(current.entries) >= MAX_ENTRIES:
            raise Invalid("name", f"at most {MAX_ENTRIES} catalog entries")
        return [*current.entries, body]

    _write(request, "POST /catalog", body.name, change)
    response.headers["Location"] = f"/api/v1/catalog/{body.name}"
    response.headers["ETag"] = etag(body)
    return _item(body)


@router.put("/catalog/{name}", response_model=models.CatalogItem)
def replace_entry(name: str, body: Entry, request: Request, response: Response) -> dict[str, Any]:
    tags = if_match(request, "catalog entry")
    if body.name != name:
        raise Invalid("name", "a name cannot change: add the entry again, then delete this one")

    def change(current: CatalogFile) -> list[Entry]:
        _find(current, name, tags)
        return [body if e.name == name else e for e in current.entries]

    _write(request, "PUT /catalog/{name}", name, change)
    response.headers["ETag"] = etag(body)
    return _item(body)


@router.delete("/catalog/{name}", status_code=204)
def delete_entry(name: str, request: Request) -> Response:
    tags = if_match(request, "catalog entry")

    def change(current: CatalogFile) -> list[Entry]:
        _find(current, name, tags)
        return [e for e in current.entries if e.name != name]

    _write(request, "DELETE /catalog/{name}", name, change)
    return Response(status_code=204)
