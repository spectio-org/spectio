"""API input hardening (follow-up FU-P3-17 of P3 Task 17): every refusal is a 4xx, never a 500."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from spectio_server.app import NO_API

RUNS = "/api/v1/runs"
INSPECT = "/api/v1/workflows:inspect"


def body(location: str, **extra: Any) -> dict[str, Any]:
    return {"workflow": {"location": location, "engine": "nextflow"}, "params": {}, **extra}


@pytest.mark.parametrize("code", [0x202E, 0x200B, 0x2028, 0x2029, 0xFEFF])
def test_format_and_separator_characters_refused(
    authed_client: TestClient, synthetic: Path, code: int
) -> None:
    name = f"a{chr(code)}b"  # a bidi override, a zero-width space, two separators, a BOM
    response = authed_client.post(RUNS, json=body(str(synthetic / "nextflow"), name=name))
    assert response.status_code == 422, response.text
    assert response.json()["errors"][0]["field"] == "name"


@pytest.mark.parametrize("referer", ["http://[", "http://[::1"])
def test_malformed_referer_is_403(authed_client: TestClient, referer: str) -> None:
    response = authed_client.get(f"{RUNS}:summary", headers={"Referer": referer})
    assert response.status_code == 403, response.text


def test_body_cap_413(authed_client: TestClient) -> None:
    big = json.dumps(body("/x", params={"a": "x" * 1_100_000}))
    response = authed_client.post(RUNS, content=big, headers={"Content-Type": "application/json"})
    assert response.status_code == 413, response.text
    assert response.json()["type"] == "/problems/request-too-large"


@pytest.mark.parametrize("location", ["/" + "a" * 300, "/x/" * 2000, "/" + "a/" * 2100])
def test_long_location_is_422(authed_client: TestClient, location: str) -> None:
    response = authed_client.get(INSPECT, params={"location": location})
    assert response.status_code == 422, response.text
    assert response.json()["errors"][0]["field"] == "location"


def test_deep_params_422(authed_client: TestClient, synthetic: Path) -> None:
    deep: Any = 1
    for _ in range(40):
        deep = {"a": deep}
    response = authed_client.post(RUNS, json=body(str(synthetic / "nextflow"), params=deep))
    assert response.status_code == 422, response.text
    assert response.json()["errors"][0]["field"] == "params"


@pytest.mark.parametrize(
    "schema", [{"$ref": "#"}, {"$schema": ["x"]}, {"$schema": 7, "type": "object"}]
)
def test_unusable_schema_is_422(authed_client: TestClient, tmp_path: Path, schema: Any) -> None:
    root = tmp_path / "pipeline"
    root.mkdir()
    (root / "main.nf").write_text("\n")
    (root / "nextflow_schema.json").write_text(json.dumps(schema))
    response = authed_client.post(RUNS, json=body(str(root), params={"a": 1}))
    assert response.status_code == 422, response.text
    assert response.json()["errors"][0]["field"].startswith("params")


def test_no_api_text_names_no_missing_host_check() -> None:
    assert "Host" not in NO_API and "CSRF" not in NO_API
