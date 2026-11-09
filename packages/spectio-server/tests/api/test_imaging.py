"""The raw routes with `as=tiff` and `as=zarr`: the imaging reads of api §5.3.1 (FU-P3-102a;
dev-env §15.3 req. 14 and 19). One `test_req14_imaging_*` per step of §5.3.1's table; steps 0
and 9 (script loads, read slots) are FU-P3-102b's.
"""

import os
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio.runner.rundir import make_run_dirs
from spectio_server.api import results as api_results
from spectio_server.files import confine
from spectio_server.files import results as files_results
from spectio_server.store.writer import Writer

from . import test_results, test_taskfiles_api
from .conftest import add_run
from .test_results import API, MIB, RUN, TEXT_CSP, Results, attachment, problem, put
from .test_taskfiles_api import NfTask

results = test_results.results  # the fixtures of the results and Job files tests
nf_task = test_taskfiles_api.nf_task

FETCH = {"Sec-Fetch-Dest": "empty"}
TIFF = b"II*\x00" + bytes(range(256)) * 16  # 4 KiB + 4, a little-endian TIFF header first


def get(client: TestClient, rel: str, as_: str, rng: str | None = None, **kw: Any) -> Any:
    headers = {**FETCH, **({"Range": rng} if rng else {}), **kw.pop("headers", {})}
    return client.get(
        f"{API}/runs/{RUN}/results/raw/{rel}", params={"as": as_, **kw}, headers=headers
    )


def ranged(found: Any, first: int, last: int, size: int, body: bytes) -> None:
    assert found.status_code == 206, found.text
    assert found.headers["content-range"] == f"bytes {first}-{last}/{size}"
    assert found.headers["content-length"] == str(len(body))
    assert found.content == body


def range_refused(found: Any) -> None:
    problem(found, 422, "validation-failed")
    assert found.json()["errors"][0]["field"] == "Range"


def test_req14_imaging_raw_checks_first(
    authed_client: TestClient, results: Results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Step 1: the route's checks answer first; the 1 GiB cap holds for every read but a TIFF
    range fetched by the page."""
    put(results, "a.tif", TIFF)
    problem(get(authed_client, "none.tif", "tiff", "bytes=0-9"), 404, "not-found")
    problem(get(authed_client, ".spectio/a.tif", "tiff", "bytes=0-9"), 422, "file-not-allowed")
    monkeypatch.setattr(api_results, "MAX_RAW", 10)
    ranged(get(authed_client, "a.tif", "tiff", "bytes=0-9"), 0, 9, len(TIFF), TIFF[:10])
    problem(get(authed_client, "a.tif", "tiff"), 413, "file-too-large")
    problem(
        get(authed_client, "a.tif", "tiff", "bytes=0-9", headers={"Sec-Fetch-Dest": "document"}),
        413,
        "file-too-large",
    )
    problem(
        get(authed_client, "a.tif", "tiff", "bytes=0-9", download="true"), 413, "file-too-large"
    )


def test_req14_imaging_download_and_other_values(
    authed_client: TestClient, results: Results
) -> None:
    """Step 2: `?download=true` is the attachment, `Range` ignored. Step 3: another `as` value
    is `422 validation-failed` on `as`."""
    put(results, "a.tif", TIFF)
    found = get(authed_client, "a.tif", "tiff", "bytes=0-9", download="true")
    attachment(found, "a.tif")
    assert found.content == TIFF
    for value in ("TIFF", "zarr ", "thumbnail"):
        found = get(authed_client, "a.tif", value, "bytes=0-9")
        problem(found, 422, "validation-failed")
        assert found.json()["errors"][0]["field"] == "as", value


def test_req14_imaging_tiff_name(authed_client: TestClient, results: Results) -> None:
    """Step 4: `as=tiff` only on a `.tif` or `.tiff` name, any case."""
    for rel in ("a.png", "a.tif.txt", "tif", "a.ome.zarr"):
        put(results, rel, TIFF)
        problem(get(authed_client, rel, "tiff", "bytes=0-9"), 422, "file-not-allowed")
    for rel in ("A.TIF", "b.tiff", "c.ome.tif", "d.OME.TIFF"):
        put(results, rel, TIFF)
        ranged(get(authed_client, rel, "tiff", "bytes=0-3"), 0, 3, len(TIFF), b"II*\x00")


ZARR_KEYS = (
    "i.ome.zarr/.zattrs",
    "i.ome.zarr/.zgroup",
    "i.ome.zarr/0/.zarray",
    "i.ome.zarr/zarr.json",
    "I.OME.ZARR/0/0.0.0",
    "i.ome.zarr/labels/c",
    "i.ome.zarr/0/c/1/2/3",
    "i.ome.zarr/0/" + ".".join("1" * 10),
)
NOT_KEYS = (
    "i.ome.zarr/.zmetadata",
    "i.ome.zarr",
    "a/.zattrs",
    "x.zarr/.zattrs",
    "i.ome.zarr/0/x.json",
    "i.ome.zarr/.0/.zarray",
    "i.ome.zarr/0/" + ".".join("1" * 11),
    "i.ome.zarr/0/12345678901",
    "i.ome.zarr/a b/.zattrs",
    "i.ome.zarr/0/0.0.",
)


def test_req14_imaging_zarr_key(authed_client: TestClient, results: Results) -> None:
    """Step 5: `as=zarr` only on a Zarr key below a `.ome.zarr` folder, `.zmetadata` refused."""
    for rel in ZARR_KEYS:
        put(results, rel, b"{}")
        found = get(authed_client, rel, "zarr")
        assert (found.status_code, found.content) == (200, b"{}"), rel
    for rel in NOT_KEYS:
        if not rel.endswith(".ome.zarr"):
            put(results, rel, b"{}")
        problem(get(authed_client, rel, "zarr"), 422, "file-not-allowed")
    problem(get(authed_client, "i.ome.zarr/%2e%2e/.zattrs", "zarr"), 422, "file-not-allowed")
    assert not api_results._zarr_key(("i.ome.zarr", "..", ".zattrs"))  # the client drops `..`


def test_req14_imaging_without_fetch_dest(authed_client: TestClient, results: Results) -> None:
    """Step 6: without `Sec-Fetch-Dest: empty` the attachment, `Range` ignored, no check."""
    put(results, "a.tif", b"not a tiff")
    put(results, "i.ome.zarr/.zattrs", b"{}")
    for dest in (
        {"Sec-Fetch-Dest": ""},
        {"Sec-Fetch-Dest": "document"},
        {"Sec-Fetch-Dest": "image"},
    ):
        attachment(get(authed_client, "a.tif", "tiff", "bytes=0-1", headers=dest), "a.tif")
        attachment(
            get(authed_client, "i.ome.zarr/.zattrs", "zarr", "bytes=0-0", headers=dest), ".zattrs"
        )


def test_req14_imaging_zarr_key_cap(authed_client: TestClient, results: Results) -> None:
    """Step 7: a Zarr key over 16 MiB is `413`, ranged or not."""
    put(results, "i.ome.zarr/0/0", b"\x00" * (16 * MIB))
    assert get(authed_client, "i.ome.zarr/0/0", "zarr", "bytes=0-0").status_code == 206
    with open(results.root / "i.ome.zarr/0/0", "ab") as f:
        f.write(b"\x00")
    problem(get(authed_client, "i.ome.zarr/0/0", "zarr"), 413, "file-too-large")
    problem(get(authed_client, "i.ome.zarr/0/0", "zarr", "bytes=0-0"), 413, "file-too-large")


def test_req14_imaging_range_refused(authed_client: TestClient, results: Results) -> None:
    """Step 8: one closed range of at most 8 MiB + 1 byte, starting before the end; a TIFF read
    needs one."""
    put(results, "a.tif", TIFF)
    put(results, "i.ome.zarr/.zattrs", b"{}")
    for rng in (
        "bytes=0-",
        "bytes=-10",
        "bytes=0-1,4-5",
        "bytes=5-4",
        "bytes 0-1",
        "items=0-1",
        "bytes=0-8388609",
        f"bytes={len(TIFF)}-{len(TIFF) + 9}",
        "bytes=+1-2",
    ):
        range_refused(get(authed_client, "a.tif", "tiff", rng))
        range_refused(get(authed_client, "i.ome.zarr/.zattrs", "zarr", rng))
    range_refused(get(authed_client, "a.tif", "tiff"))
    put(results, "big.tif", b"MM\x00*" + b"\x00" * (9 * MIB))
    ranged(
        get(authed_client, "big.tif", "tiff", "bytes=0-8388608"),
        0,
        8 * MIB,
        9 * MIB + 4,
        b"MM\x00*" + b"\x00" * (8 * MIB - 3),
    )


def test_req14_imaging_not_a_tiff(authed_client: TestClient, results: Results) -> None:
    """Step 10: the first 4 bytes are a TIFF or BigTIFF header, either byte order."""
    for head in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        put(results, "a.tif", head + b"rest")
        ranged(get(authed_client, "a.tif", "tiff", "bytes=4-7"), 4, 7, 8, b"rest")
    for data in (b"II*\x01", b"\x89PNG\r\n\x1a\n", b"MM*\x00rest", b""):
        put(results, "a.tif", data + b"\x00" * 8)
        problem(get(authed_client, "a.tif", "tiff", "bytes=0-1"), 422, "file-not-allowed")


def test_req14_imaging_served(authed_client: TestClient, results: Results) -> None:
    """Step 11: `206` with `Content-Range` (the last byte capped at the end), or `200` for a
    whole key; octet-stream, `Accept-Ranges`, never an attachment, the shared headers."""
    put(results, "a.tif", TIFF)
    put(results, "i.ome.zarr/0/0.0", b"chunk")
    found = get(authed_client, "a.tif", "tiff", f"bytes=4000-{len(TIFF) + 50}")
    ranged(found, 4000, len(TIFF) - 1, len(TIFF), TIFF[4000:])
    ranged(get(authed_client, "i.ome.zarr/0/0.0", "zarr", "bytes=1-2"), 1, 2, 5, b"hu")
    whole = get(authed_client, "i.ome.zarr/0/0.0", "zarr")
    assert (whole.status_code, whole.content) == (200, b"chunk")
    assert "content-range" not in whole.headers
    for answer in (found, whole):
        assert answer.headers["content-type"] == "application/octet-stream"
        assert answer.headers["accept-ranges"] == "bytes"
        assert "content-disposition" not in answer.headers
        assert answer.headers["content-security-policy"] == TEXT_CSP
        assert answer.headers["x-content-type-options"] == "nosniff"
        assert answer.headers["cross-origin-resource-policy"] == "same-origin"
        assert answer.headers["vary"] == "Sec-Fetch-Dest"
        assert "service-worker-allowed" not in answer.headers


def test_req14_imaging_read_amplification(
    authed_client: TestClient, results: Results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 64 KiB range in the middle of a 4 MiB file reads its range and the 4-byte header; a
    ranged Zarr key reads its range alone."""
    put(results, "a.tif", b"II*\x00" + os.urandom(4 * MIB - 4))
    put(results, "i.ome.zarr/0/0", os.urandom(4 * MIB))
    real, read = confine.read_at, []

    def counted(f: Any, start: int, n: int) -> bytes:
        data = real(f, start, n)
        read.append(len(data))
        return data

    monkeypatch.setattr(files_results, "read_at", counted)
    first = 2 * MIB + 12345
    assert get(authed_client, "a.tif", "tiff", f"bytes={first}-{first + 65535}").status_code == 206
    assert sum(read) <= 65536 + 4, read
    read.clear()
    assert (
        get(authed_client, "i.ome.zarr/0/0", "zarr", f"bytes={first}-{first + 65535}").status_code
        == 206
    )
    assert sum(read) == 65536, read


def test_req14_imaging_sparse_2gib(authed_client: TestClient, results: Results) -> None:
    """A TIFF range of a 2 GiB file is served; a plain raw read of it is `413`."""
    path = put(results, "big.tif", b"II*\x00")
    os.truncate(path, 2 << 30)
    with open(path, "r+b") as f:
        f.seek((2 << 30) - 4)
        f.write(b"tail")
    size = 2 << 30
    ranged(
        get(authed_client, "big.tif", "tiff", f"bytes={size - 4}-{size - 1}"),
        size - 4,
        size - 1,
        size,
        b"tail",
    )
    problem(authed_client.get(f"{API}/runs/{RUN}/results/raw/big.tif"), 413, "file-too-large")


def test_req14_imaging_range_across_chunk_seam(
    authed_client: TestClient, results: Results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The range is read from its own first byte in chunks of at most `CHUNK`."""
    monkeypatch.setattr(files_results, "CHUNK", 32)
    put(results, "a.tif", TIFF)
    ranged(get(authed_client, "a.tif", "tiff", "bytes=20-100"), 20, 100, len(TIFF), TIFF[20:101])


def test_req14_imaging_replaced_mid_range(
    served: str,
    session: dict[str, str],
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file replaced between two chunks of one range aborts the answer."""
    paths = make_run_dirs(settings.runs_root, RUN)
    root = paths.launch_dir / "results"
    add_run(writer, settings, RUN, "rnaseq", "running", results_dir=str(root))
    root.mkdir()
    (root / "a.tif").write_bytes(TIFF)
    monkeypatch.setattr(files_results, "CHUNK", 32)
    real, calls = files_results.read_chunk, []

    def replacing(where: Any, rel: Any, *args: Any) -> bytes:
        calls.append(rel)
        if len(calls) == 2:
            (root / "new.tif").write_bytes(TIFF)
            os.replace(root / "new.tif", root / "a.tif")
        return real(where, rel, *args)

    monkeypatch.setattr(files_results, "read_chunk", replacing)
    url = f"{API}/runs/{RUN}/results/raw/a.tif?as=tiff"
    with (
        httpx2.Client(base_url=served, timeout=10, cookies=session) as http,
        http.stream("GET", url, headers={**FETCH, "Range": "bytes=0-99"}) as response,
    ):
        assert response.status_code == 206
        with pytest.raises(httpx2.RemoteProtocolError):
            response.read()


def test_req14_imaging_middle_link_refused(authed_client: TestClient, results: Results) -> None:
    """A `.ome.zarr` folder published as a link to a task's folder: its keys are refused, the
    link not followed as a middle part (SEC-PRE-FU102-R1-09)."""
    store = results.task_dir / "i.ome.zarr"
    store.mkdir()
    (store / ".zattrs").write_text("{}")
    results.root.mkdir()
    (results.root / "i.ome.zarr").symlink_to(store)
    problem(get(authed_client, "i.ome.zarr/.zattrs", "zarr"), 422, "file-not-allowed")


def test_req14_imaging_workdir_dot_rule(nf_task: NfTask) -> None:
    """A work directory refuses every dot part: a Zarr v2 key is refused there, a v3 key served;
    a TIFF range is served from it too."""
    store = nf_task.dir / "i.ome.zarr"
    (store / "0").mkdir(parents=True)
    (store / ".zattrs").write_text("{}")
    (store / "zarr.json").write_text("{}")
    (store / "0" / "zarr.json").write_text("{}")
    Path(nf_task.dir / "a.tif").write_bytes(TIFF)
    base = f"{API}/tasks/{nf_task.task_id}/attempts/1/workdir/raw"

    def ask(rel: str, as_: str, rng: str | None = None) -> Any:
        headers = {**FETCH, **({"Range": rng} if rng else {})}
        return nf_task.client.get(f"{base}/{rel}", params={"as": as_}, headers=headers)

    problem(ask("i.ome.zarr/.zattrs", "zarr"), 422, "file-not-allowed")
    for rel in ("i.ome.zarr/zarr.json", "i.ome.zarr/0/zarr.json"):
        found = ask(rel, "zarr")
        assert (found.status_code, found.content) == (200, b"{}"), rel
    ranged(ask("a.tif", "tiff", "bytes=0-3"), 0, 3, len(TIFF), b"II*\x00")
