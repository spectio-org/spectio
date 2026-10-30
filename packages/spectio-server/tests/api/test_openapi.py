"""The OpenAPI snapshot of 0.0.1, for the typed client of P1 Task 19.

Regenerate it with
`SPECTIO_UPDATE_OPENAPI=1 uv run pytest packages/spectio-server/tests/api/test_openapi.py`.
The served documents stay off (Task 11): the snapshot is a file, not a route.
"""

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

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
