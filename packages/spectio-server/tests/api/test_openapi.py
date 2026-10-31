"""The OpenAPI snapshot of 0.0.1, for the typed client of P1 Task 19.

Regenerate it with
`SPECTIO_UPDATE_OPENAPI=1 uv run pytest packages/spectio-server/tests/api/test_openapi.py`.
The served documents stay off (Task 11): the snapshot is a file, not a route.
"""

import json
import os
from pathlib import Path
from typing import get_args

import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio_server import app as app_mod
from spectio_server.api import models
from spectio_server.store.schema import RUN_ORIGINS, RUN_STATES, STAGE_STATES, TASK_STATES
from spectio_server.store.writer import Writer

SNAPSHOT = Path(__file__).resolve().parents[2] / "openapi" / "0.0.1.json"
UPDATE = os.environ.get("SPECTIO_UPDATE_OPENAPI") == "1"  # read before `settings` clears SPECTIO_*


def test_openapi_snapshot(authed_client: TestClient) -> None:
    app = authed_client.app
    found = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"  # type: ignore[attr-defined]
    if UPDATE:
        SNAPSHOT.write_text(found)
    assert SNAPSHOT.read_text() == found, "the API changed: regenerate the snapshot"
    paths = json.loads(found)["paths"]
    for path in ("/api/v1/runs", "/api/v1/runs/{run_id}", "/api/v1/runs/{run_id}:cancel"):
        assert path in paths


def test_docs_not_served(authed_client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert authed_client.get(path).status_code == 404


# The read routes the screens consume (P1 Task 20), each with a named response model (FU-P3-21).
MODELS = {
    ("/api/v1/runs", "get", "200"): "RunList",
    ("/api/v1/runs/{run_id}", "get", "200"): "RunDetail",
    ("/api/v1/runs/{run_id}:cancel", "post", "202"): "RunDetail",
    ("/api/v1/runs:summary", "get", "200"): "Summary",
    ("/api/v1/version", "get", "200"): "ServerVersion",
    ("/api/v1/runs/{run_id}/processes", "get", "200"): "ProcessList",
    ("/api/v1/runs/{run_id}/stages", "get", "200"): "StageList",
    ("/api/v1/runs/{run_id}/tasks", "get", "200"): "TaskList",
}


def test_read_routes_have_response_models(authed_client: TestClient) -> None:
    doc = authed_client.app.openapi()  # type: ignore[attr-defined]
    for (path, method, status), name in MODELS.items():
        content = doc["paths"][path][method]["responses"][status]["content"]
        assert content["application/json"]["schema"] == {"$ref": f"#/components/schemas/{name}"}
        assert doc["components"]["schemas"][name]["properties"], name


def test_info_version_is_the_api_version(
    settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A release bump changes the package version, not the API document (CR-P3T18-03)."""
    monkeypatch.setattr(app_mod, "version", lambda _: "9.9.9")
    app = app_mod.create_app(settings, writer)
    assert app.openapi()["info"]["version"] == "0.0.1"


def test_model_enums_match_the_store() -> None:
    assert get_args(models.RunState) == RUN_STATES
    assert get_args(models.TaskState) == TASK_STATES
    assert get_args(models.StageState) == STAGE_STATES
    assert get_args(models.RunOrigin) == RUN_ORIGINS
