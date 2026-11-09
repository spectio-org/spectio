"""The environments file (FU-P3-86b; api §5.4, Where definitions live; dev-env §15.3 req. 18):
`environments.toml` next to `spectio.toml`, read without following a link, owner and mode
checked, at most 64 KiB, in five states; written whole, through the directory's descriptor, only
over a file whose identity is that of the read."""

import errno
import os
import stat
from pathlib import Path

import pytest

from spectio import envfile
from spectio.environments import Environment
from spectio.runner.types import Stalled

NAMES = frozenset({"local", "slurm"})
GOOD = """default = "mylab"

[environments.mylab]
label = "My lab"
executor = "slurm"

[environments.mylab.slurm]
partition = "htc"
time_min = 60

[environments.small]
executor = "local"
local = { cpus = 4 }
"""


@pytest.fixture
def path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    monkeypatch.setenv("SPECTIO_CONFIG", str(data / "spectio.toml"))
    return envfile.environments_path()


def put(path: Path, text: str | bytes, mode: int = 0o600) -> None:
    path.write_bytes(text.encode() if isinstance(text, str) else text)
    path.chmod(mode)


def read(path: Path, names: frozenset[str] = NAMES) -> envfile.EnvFile:
    return envfile.read_file(path, names)


def test_req18_file_path_is_next_to_spectio_toml(path: Path) -> None:
    assert path.name == "environments.toml"
    assert path.parent == Path(os.environ["SPECTIO_CONFIG"]).parent


def test_req18_file_missing_and_ok(path: Path) -> None:
    found = read(path)
    assert (found.state, found.environments, found.default) == ("missing", (), None)
    put(path, GOOD)
    found = read(path)
    assert found.state == "ok" and found.default == "mylab"
    assert [e.name for e in found.environments] == ["mylab", "small"]
    assert found.environments[0].slurm is not None
    assert found.environments[0].slurm.time_min == 60
    assert found.identity is not None and len(found.identity[4]) == 64


def test_req18_file_hand_edit_picked_up(path: Path) -> None:
    """No restart: a later read sees the new text, and an unchanged file is the cached read."""
    put(path, GOOD)
    first = read(path)
    assert envfile.read_file(path, NAMES, cached=first) is first
    put(path, GOOD.replace('"My lab"', '"Ours"'))
    second = envfile.read_file(path, NAMES, cached=first)
    assert second.environments[0].label == "Ours"


@pytest.mark.parametrize(
    "make",
    ["group-writable", "symlink", "fifo", "directory", "dir-writable"],
)
def test_req18_file_refused(path: Path, tmp_path: Path, make: str) -> None:
    if make == "group-writable":
        put(path, GOOD, 0o620)
    elif make == "symlink":
        target = tmp_path / "elsewhere.toml"
        put(target, GOOD)
        path.symlink_to(target)
    elif make == "fifo":
        os.mkfifo(path, 0o600)  # never blocks the read: O_NONBLOCK
    elif make == "directory":
        path.mkdir(mode=0o700)
    else:
        put(path, GOOD)
        path.parent.chmod(0o777)
    found = read(path)
    assert found.state == "refused" and found.environments == ()
    assert found.detail


def test_req18_file_refused_other_owner(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    put(path, GOOD)
    monkeypatch.setattr(os, "geteuid", lambda: os.getuid() + 1)
    assert read(path).state == "refused"


def test_req18_file_refused_symlinked_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    put(real / "environments.toml", GOOD)
    (tmp_path / "link").symlink_to(real)
    monkeypatch.setenv("SPECTIO_CONFIG", str(tmp_path / "link" / "spectio.toml"))
    assert read(envfile.environments_path()).state == "refused"


@pytest.mark.parametrize(
    ("text", "names"),
    [
        ("a=" + "[" * 30000 + "]" * 30000, NAMES),  # RecursionError in tomllib (3.13)
        ('default = "gone"\n', NAMES),  # a dangling default
        ('default = "slurm"\n', frozenset({"local"})),  # a built-in this server lacks
        ("[environments.x]\nexecutor = 'local'\nqos = 'normal'\n", NAMES),  # unknown key
        ("[environments.x]\nexecutor = 'local'\nlocal = { cpus = 0 }\n", NAMES),
        ("[environments.x]\nexecutor = 'local'\nlocal = { cpus = '2' }\n", NAMES),
        ("[environments.local]\nexecutor = 'local'\n", NAMES),  # a built-in name
        ("[environments.new]\nexecutor = 'local'\n", NAMES),
        ("[environments.X]\nexecutor = 'local'\n", NAMES),
        ("[environments.x]\nname = 'y'\nexecutor = 'local'\n", NAMES),
        ("other = 1\n", NAMES),
        ("[environments.x\n", NAMES),
        (b"\xff\xfe", NAMES),
        ("x" * (64 * 1024 + 1), NAMES),
        ("".join(f"[environments.e{i}]\nexecutor = 'local'\n" for i in range(33)), NAMES),
    ],
)
def test_req18_file_invalid(path: Path, text: str | bytes, names: frozenset[str]) -> None:
    put(path, text)
    found = read(path, names)
    assert found.state == "invalid" and found.environments == ()
    assert found.detail and len(found.detail) <= 200


def test_req18_file_invalid_detail_has_no_file_bytes(path: Path) -> None:
    """The detail is the parser's message and a place, cleaned, never bytes of the file."""
    put(path, "[environments.x]\nexecutor = 'local'\nlabel = 'secret‮'\n")
    found = read(path)
    assert found.state == "invalid" and found.detail is not None
    assert "secret" not in found.detail and "‮" not in found.detail
    put(path, "[environments.x]\nexecutor = 'local'\nlocal = { cpus = 'secret' }\n")
    detail = read(path).detail or ""
    assert "secret" not in detail and "environments.x.local.cpus" in detail
    key = "SECRETa'b\\\"cTOKEN"  # both quote kinds: its repr holds a backslash escape
    put(path, f'[environments."{key}"]\n[environments."{key}"]\n')
    detail = read(path).detail or ""
    assert detail.endswith("(at line 2, column 34)")
    assert not any(part in detail for part in ("SECRET", "TOKEN", "'", '"', "\\"))


@pytest.mark.parametrize("where", ["directory", "file"])
def test_req18_file_open_io_error_unreachable(
    path: Path, monkeypatch: pytest.MonkeyPatch, where: str
) -> None:
    """ESTALE at open time, of the file or of its directory, is `unreachable` as at read time,
    not `refused`; a write raises Stalled (CR-P3FU86BCD-03)."""
    put(path, GOOD)
    target = path.parent if where == "directory" else path.name
    real_open = os.open

    def stale(name: object, *args: object, **kwargs: object) -> int:
        if name == target:
            raise OSError(errno.ESTALE, os.strerror(errno.ESTALE))
        return real_open(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", stale)
    found = read(path)
    assert found.state == "unreachable" and found.detail
    with pytest.raises(Stalled):
        envfile.update(path, NAMES, lambda current: (None, []))


def test_req18_file_write_renders_and_renames(path: Path) -> None:
    mine = Environment.model_validate(
        {
            "name": "mylab",
            "label": 'a "quoted" label',
            "executor": "slurm",
            "slurm": {"account": "lab"},
        }
    )

    def change(current: envfile.EnvFile) -> tuple[str | None, list[Environment]]:
        assert current.state == "missing"
        return "mylab", [mine]

    written = envfile.update(path, NAMES, change)
    assert written.state == "ok" and written.environments == (mine,)
    st = path.stat()
    assert stat.S_IMODE(st.st_mode) == 0o600
    assert read(path).environments == (mine,) and read(path).default == "mylab"
    assert [p.name for p in path.parent.iterdir()] == ["environments.toml"]  # no temporary left


@pytest.mark.parametrize("make", ["invalid", "refused"])
def test_req18_file_never_overwrites_unusable(path: Path, make: str) -> None:
    put(path, "[broken\n", 0o600 if make == "invalid" else 0o660)
    before = path.read_bytes()
    with pytest.raises(envfile.Unusable) as exc:
        envfile.update(path, NAMES, lambda current: (None, []))
    assert exc.value.state == make
    assert path.read_bytes() == before


def test_req18_file_write_after_same_size_hand_edit_refused(path: Path) -> None:
    """The identity holds the SHA-256: a hand edit of the same size, with the same mtime, between
    the read and the rename is seen and nothing is written."""
    put(path, GOOD)
    edited = GOOD.replace("htc", "gpu")
    mtime = path.stat().st_mtime_ns

    def change(current: envfile.EnvFile) -> tuple[str | None, list[Environment]]:
        put(path, edited)
        os.utime(path, ns=(mtime, mtime))
        return current.default, list(current.environments)

    with pytest.raises(envfile.Changed):
        envfile.update(path, NAMES, change)
    assert path.read_text() == edited


def test_req18_file_render_round_trip() -> None:
    envs = [
        Environment.model_validate(
            {
                "name": "a",
                "executor": "local",
                "local": {"cpus": 2, "mem_mib": 8192},
                "profiles": {"nextflow": "test", "snakemake": None},
            }
        ),
        Environment.model_validate({"name": "b", "executor": "slurm", "label": "x\\yé"}),
    ]
    found = envfile.parse(envfile.render("b", envs), NAMES)
    assert found.state == "ok" and found.environments == tuple(envs) and found.default == "b"
