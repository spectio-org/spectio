"""The screens of P1 Task 19: `web/dist` served at `/` under the API's rule (inbox #80, #86).

They are served only when `create_app`'s one `no_api` decision mounts the API; otherwise `/` keeps
Task 11's plain page and says why. Files are served without following a symlink or leaving the
directory, with their content type, a Cache-Control and a CSP that allows only this origin.
TODO(P1 Task 16): the screens move behind the session with the API.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio_server import app as app_mod
from spectio_server import static
from spectio_server.store.writer import Writer

from .conftest import client_for

INDEX = '<!doctype html><script type="module" src="/assets/index-AbC1.js"></script>'


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(INDEX)
    (root / "assets" / "index-AbC1.js").write_text("console.log(1)")
    (root / "assets" / "index-AbC1.css").write_text("body{}")
    (root / "assets" / "logo-x1.svg").write_text("<svg/>")
    (root / "assets" / "notes.txt").write_text("not a web type")
    (root / "assets" / ".hidden.js").write_text("hidden")
    return root


@pytest.fixture
def web(settings: Settings, writer: Writer, dist: Path) -> TestClient:
    return client_for(settings, writer, web_dir=dist)


def test_spa_routes_serve_index(web: TestClient) -> None:
    for path in ("/", "/runs", "/launch", "/runs/run_01K8T2F1XTVRES000000000000"):
        r = web.get(path)
        assert r.status_code == 200, path
        assert r.text == INDEX
        assert r.headers["content-type"] == "text/html; charset=utf-8"
        assert r.headers["cache-control"] == "no-cache"
        csp = r.headers["content-security-policy"]
        assert "default-src 'none'" in csp
        assert "script-src 'self' 'wasm-unsafe-eval';" in csp  # no 'unsafe-inline' script
        assert "connect-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert r.headers["x-content-type-options"] == "nosniff"


def test_screens_may_frame_this_origin_only(web: TestClient) -> None:
    """Every screen allows `frame-src 'self'`, for the report viewer's sandboxed report served by
    `/api/v1/runs/{id}/results/raw/...` (P1 Task 31): a CSP is the document's, and the viewer is
    also reached by in-app navigation from another screen (CR-P3T31-02)."""
    for path in ("/", "/runs", "/runs/run_01K8T2F1XTVRES000000000000/report"):
        r = web.get(path)
        assert r.status_code == 200, path
        assert r.text == INDEX
        csp = r.headers["content-security-policy"]
        assert "frame-src 'self'" in csp, path
        assert "frame-ancestors 'none'" in csp, path
        assert "script-src 'self' 'wasm-unsafe-eval';" in csp, path


def test_csp_allows_wasm_and_own_workers_only(web: TestClient) -> None:
    """The imaging viewers' CSP (dev-env §15.3 req. 19): WebAssembly and workers of this origin;
    never `'unsafe-eval'` nor a `blob:` source (SEC-PRE-FU102-R1-08)."""
    csp = web.get("/").headers["content-security-policy"]
    directives = {d.split()[0]: d.split()[1:] for d in csp.split("; ")}
    assert directives["script-src"] == ["'self'", "'wasm-unsafe-eval'"]
    assert directives["worker-src"] == ["'self'"]
    tokens = csp.replace(";", " ").split()
    assert "'unsafe-eval'" not in tokens
    assert not any("blob:" in t for t in tokens)
    assert csp == static.CSP


def test_results_browser_is_a_screen(web: TestClient) -> None:
    """The results browser `/runs/{id}/results` answers the screens (P1 Task 32 part two)."""
    r = web.get("/runs/run_01K8T2F1XTVRES000000000000/results?path=fastqc")
    assert r.status_code == 200
    assert r.text == INDEX
    assert "frame-src 'self'" in r.headers["content-security-policy"]


def test_file_preview_is_a_screen(web: TestClient) -> None:
    """The preview of one results file `/runs/{id}/results/file` answers the screens, with
    `img-src 'self'` for its `<img>` of the raw route (ui-spec §4.4.1, FU-P3-85c)."""
    r = web.get("/runs/run_01K8T2F1XTVRES000000000000/results/file?path=a%3Fb.txt")
    assert r.status_code == 200
    assert r.text == INDEX
    assert "img-src 'self'" in r.headers["content-security-policy"]


def test_environments_pages_are_screens(web: TestClient) -> None:
    """The Environments list and form answer the screens (ui-spec §4.8.1, FU-P3-86f)."""
    for path in ("/environments", "/environments/new?from=slurm", "/environments/mylab-long"):
        r = web.get(path)
        assert r.status_code == 200, path
        assert r.text == INDEX


def test_workdir_pages_are_screens(web: TestClient) -> None:
    """The work directory's folder and file pages answer the screens (ui-spec §4.4.1,
    FU-P3-85e)."""
    query = "task=tsk_01K8T2F1XTVRES000000000000&attempt=1&path=qc"
    for page in ("workdir", "workdir/file"):
        r = web.get(f"/runs/run_01K8T2F1XTVRES000000000000/{page}?{query}")
        assert r.status_code == 200, page
        assert r.text == INDEX
        assert "img-src 'self'" in r.headers["content-security-policy"]


def test_head_on_screens_and_assets(web: TestClient) -> None:
    """A HEAD gets the GET's status and headers, no body (FU-P3-22: it was 405)."""
    for path in ("/", "/runs", "/runs/run_01K8T2F1XTVRES000000000000", "/assets/index-AbC1.js"):
        r = web.head(path)
        assert r.status_code == 200, path
        assert r.content == b""
        assert "content-security-policy" in r.headers
    assert web.head("/nope").status_code == 404


def test_assets_types_and_cache(web: TestClient) -> None:
    types = {
        "index-AbC1.js": "text/javascript; charset=utf-8",
        "index-AbC1.css": "text/css; charset=utf-8",
        "logo-x1.svg": "image/svg+xml",
    }
    for name, media in types.items():
        r = web.get(f"/assets/{name}")
        assert r.status_code == 200, name
        assert r.headers["content-type"] == media
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "content-security-policy" in r.headers


@pytest.mark.parametrize(
    "path",
    [
        "/nope",  # no SPA fallback beyond the four routes
        "/runs/a/b",
        "/launch/x",
        "/index.html",
        "/assets/missing.js",
        "/assets/notes.txt",  # not a web type
        "/assets/.hidden.js",
        "/assets/..%2Findex.html",
        "/assets/%2e%2e/index.html",
        "/assets/sub/x.js",
    ],
)
def test_nothing_else_served(web: TestClient, path: str) -> None:
    assert web.get(path).status_code == 404


def test_symlinks_not_followed(web: TestClient, dist: Path, tmp_path: Path) -> None:
    outside = tmp_path / "secret.js"
    outside.write_text("secret")
    (dist / "assets" / "link.js").symlink_to(outside)
    r = web.get("/assets/link.js")
    assert r.status_code == 404
    assert "secret" not in r.text


def test_symlinked_assets_dir_not_followed(
    settings: Settings, writer: Writer, dist: Path, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "elsewhere"
    (dist / "assets").rename(elsewhere)
    (dist / "assets").symlink_to(elsewhere)
    assert (
        client_for(settings, writer, web_dir=dist).get("/assets/index-AbC1.js").status_code == 404
    )


def test_screens_isolate_referrer_and_opener(web: TestClient) -> None:
    # SEC-P3T19-03: run pages carry run IDs in their URL and may link out (Task 20).
    for path in ("/", "/runs/run_01K8T2F1XTVRES000000000000", "/assets/index-AbC1.js"):
        r = web.get(path)
        assert r.headers["referrer-policy"] == "no-referrer", path
        assert r.headers["cross-origin-opener-policy"] == "same-origin", path


def test_fifo_not_opened(web: TestClient, dist: Path) -> None:
    os.mkfifo(dist / "assets" / "pipe.js")
    assert web.get("/assets/pipe.js").status_code == 404  # and the request does not hang


def test_browser_checks_apply(web: TestClient) -> None:
    assert web.get("/", headers={"Host": "evil.example"}).status_code == 400
    assert web.get("/launch", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_api_still_served(web: TestClient) -> None:
    assert web.get("/api/v1/version").status_code == 200


def test_no_api_keeps_the_plain_page(
    settings: Settings, writer: Writer, dist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_mod, "shared_host", lambda: "a process of uid 1001 runs here")
    shared = client_for(settings, writer, web_dir=dist)
    r = shared.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "looks shared (a process of uid 1001 runs here)" in r.text
    assert "screens" in r.text
    for path in ("/launch", "/runs", "/assets/index-AbC1.js"):
        assert shared.get(path).status_code == 404, path


def test_missing_dist_says_how_to_build(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    missing = client_for(settings, writer, web_dir=tmp_path / "no-dist")
    r = missing.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "npm --prefix web ci --ignore-scripts && npm --prefix web run build" in r.text
    assert missing.get("/launch").status_code == 404
    assert missing.get("/api/v1/version").status_code == 200  # the API does not need the screens


def _layout(top: Path, package: str) -> Path:
    """`static.py` at `top/<package>/spectio_server/`, and a planted `top/web/dist`."""
    module = top / package / "spectio_server" / "static.py"
    module.parent.mkdir(parents=True)
    module.touch()
    (top / "web" / "dist").mkdir(parents=True)
    (top / "web" / "dist" / "index.html").write_text(INDEX)
    return module


def test_installed_wheel_never_uses_a_planted_dist(tmp_path: Path) -> None:
    # `pip install --target <top>/x/y/lib`: four levels up is `top`, which another user may own.
    module = _layout(tmp_path, "x/y/lib")
    found = static.find_dist(module)
    assert found == module.parent / "web"
    assert static.built(found) is False


def test_checkout_dist_needs_an_owned_unwritable_walk(tmp_path: Path) -> None:
    module = _layout(tmp_path, "packages/spectio-server/src")
    (tmp_path / "pyproject.toml").touch()
    assert static.find_dist(module) == tmp_path / "web" / "dist"
    (tmp_path / "web").chmod(0o777)
    assert static.find_dist(module) == module.parent / "web"


def test_refused_checkout_says_why(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    # The screens are built but the walk is refused: say so, not "run npm build" (CR-P3T21-02).
    module = _layout(tmp_path, "packages/spectio-server/src")
    (tmp_path / "pyproject.toml").touch()
    web = tmp_path / "web"
    web.chmod(0o777)
    with caplog.at_level("WARNING", logger="spectio_server.static"):
        assert static.find_dist(module) == module.parent / "web"
    assert [r.getMessage() for r in caplog.records] == [
        f"{web} is group- or world-writable or not yours: chmod g-w,o-w {web}"
    ]
