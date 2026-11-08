"""`spectio open` on the laptop, with the fake ssh of `fakebin/` (P1 Task 24; dev-env §15.3
"Access", req. 8). The fake runs each remote command through `/bin/sh -c` as sshd does, with a
fake login shell (`rshell`) and a fake remote `spectio`, so both quoting layers are real."""

import json
import os
import shlex
import shutil
import socket
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from spectio.cli.main import app

FAKE = Path(__file__).parent / "fakebin" / "ssh"
TICKET = "T" * 40 + "abc"  # 43 characters of the ticket alphabet
PY = sys.executable

# The remote login shell: logs its argv, then runs the script with /bin/sh.
RSHELL = f"""#!{PY}
import json, os, sys
with open(os.path.join(os.environ["FAKE_SSH_DIR"], "shell.jsonl"), "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
assert sys.argv[1] == "-lc", sys.argv
os.execv("/bin/sh", ["/bin/sh", "-c", sys.argv[2]])
"""

# The remote spectio: logs its argv and SPECTIO_X; init, serve --detach and login answer as the
# real commands do; `login.out` in $FAKE_SSH_DIR replaces what login prints, and `dead` makes
# login fail as it does when the server of server.json has stopped. `starting` (a number N) makes
# serve --detach exit 3, as when its server is still booting, and the next N logins fail.
RSPECTIO = f"""#!{PY}
import json, os, sys
d = os.environ["FAKE_SSH_DIR"]
home = os.environ["HOME"]
with open(os.path.join(d, "spectio.jsonl"), "a") as f:
    f.write(json.dumps({{"argv": sys.argv[1:], "node": os.environ["FAKE_NODE"],
                        "x": os.environ.get("SPECTIO_X")}}) + "\\n")
cmd = sys.argv[1:]
if cmd == ["init"]:
    os.makedirs(os.path.join(home, ".spectio"), mode=0o700)
elif cmd == ["serve", "--detach", "--no-link"]:
    record = {{"host": os.environ["FAKE_NODE"], "port": 8123, "pid": 4242,
              "db_dir": "/scratch/spectio-1000", "started_at": "2026-11-07T10:00:00Z"}}
    with open(os.path.join(home, ".spectio", "server.json"), "w") as f:
        json.dump(record, f)
    print("Spectio is running; a link: spectio login --print-link")
    if os.path.exists(os.path.join(d, "starting")):
        sys.exit(3)
elif cmd == ["login", "--print-link", "--json"]:
    out = os.path.join(d, "login.out")
    if os.path.exists(os.path.join(d, "dead")):
        sys.exit("spectio login: no server answers")
    starting = os.path.join(d, "starting")
    if os.path.exists(starting):
        left = int(open(starting).read())
        if left > 0:
            open(starting, "w").write(str(left - 1))
            sys.exit("spectio login: the server on port 8123 gave no link")
    if os.path.exists(out):
        print(open(out).read())
    else:
        print('spectio-ticket-v1 {{"ticket": "{TICKET}"}}')
elif cmd != ["--help"]:
    sys.exit("fake spectio: unexpected " + repr(cmd))
"""


@dataclass
class FakeSsh:
    dir: Path
    home: Path  # the cluster's shared home

    def calls(self) -> list[list[str]]:
        return self._lines("calls.jsonl")

    def shells(self) -> list[list[str]]:
        return self._lines("shell.jsonl")

    def spectio(self) -> list[dict[str, Any]]:
        return self._lines("spectio.jsonl")

    def state(self, record: dict[str, Any]) -> None:
        (self.home / ".spectio").mkdir(mode=0o700, exist_ok=True)
        (self.home / ".spectio" / "server.json").write_text(json.dumps(record))

    def tool(self, name: str, text: str) -> None:
        path = self.dir / "bin" / name
        path.write_text(text)
        path.chmod(0o755)

    def _lines(self, name: str) -> list[Any]:
        path = self.dir / name
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def fake_ssh(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeSsh:
    """The fake ssh first on the laptop's PATH, a cluster with `rshell` and `spectio` on its
    PATH, and a browser that records the URL it is given and closes the tunnel."""
    state = tmp_path / "ssh"
    (state / "bin").mkdir(parents=True)
    (state / "home").mkdir()
    laptop = tmp_path / "laptop-bin"
    laptop.mkdir()
    shutil.copy(FAKE, laptop / "ssh")
    monkeypatch.setenv("PATH", f"{laptop}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_SSH_DIR", str(state))
    fake = FakeSsh(state, state / "home")
    fake.tool("rshell", RSHELL)
    fake.tool("spectio", RSPECTIO)

    def browser(url: str) -> bool:
        (state / "opened").write_text(url)
        (state / "close").touch()
        return True

    monkeypatch.setattr(webbrowser, "open", browser)
    return fake


STATE = {
    "host": "login3",
    "port": 8123,
    "pid": 4242,
    "db_dir": "/scratch/spectio-1000",
    "started_at": "2026-11-07T10:00:00Z",
}


def spectio_open(*args: str) -> Any:
    return CliRunner().invoke(app, ["open", *args])


def tunnel(fake: FakeSsh) -> list[str]:
    (call,) = [c for c in fake.calls() if c[0] == "-N"]
    return call


def opened(fake: FakeSsh) -> str:
    return (fake.dir / "opened").read_text()


def clusters_toml(home: Path, text: str) -> None:
    path = home / ".config" / "spectio" / "clusters.toml"
    path.parent.mkdir(parents=True, mode=0o700)
    path.write_text(text)
    path.chmod(0o600)


def test_reads_state_file_and_reaches_its_node(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    result = spectio_open("cluster")
    assert result.exit_code == 0, result.output
    dests = [c[c.index("--") + 1] for c in fake_ssh.calls()]
    assert dests == ["cluster", "login3", "login3"]  # state read, tunnel, ticket
    assert tunnel(fake_ssh)[-1] == "login3"
    assert [s["node"] for s in fake_ssh.spectio()] == ["cluster", "login3"]
    assert [s["argv"] for s in fake_ssh.spectio()][-1] == ["login", "--print-link", "--json"]


def test_node_flag_for_first_start(fake_ssh: FakeSsh) -> None:
    result = spectio_open("cluster", "--node", "login2")
    assert result.exit_code == 0, result.output
    started = [(s["node"], s["argv"]) for s in fake_ssh.spectio()]
    assert ("login2", ["init"]) in started
    assert ("login2", ["serve", "--detach", "--no-link"]) in started
    assert started.index(("login2", ["init"])) < started.index(
        ("login2", ["serve", "--detach", "--no-link"])
    )
    assert tunnel(fake_ssh)[-1] == "login2"
    assert "127.0.0.1:8123" in tunnel(fake_ssh)[tunnel(fake_ssh).index("-L") + 1]


def test_first_start_asks_no_link_from_serve(fake_ssh: FakeSsh) -> None:
    """The link of `serve --detach` would land in ssh's captured stdout: --no-link (SEC-PRE-10);
    the ticket comes from spectio login, as for a running server."""
    result = spectio_open("cluster")
    assert result.exit_code == 0, result.output
    assert [s["argv"] for s in fake_ssh.spectio()][-2:] == [
        ["serve", "--detach", "--no-link"],
        ["login", "--print-link", "--json"],
    ]


def test_first_start_still_starting_retries_the_ticket(
    fake_ssh: FakeSsh, monkeypatch: pytest.MonkeyPatch
) -> None:
    """serve --detach exits 3 while its server boots: the ticket is asked again (CON-PRE-02)."""
    monkeypatch.setattr("spectio.cli.open.TICKET_RETRY_S", 0)
    (fake_ssh.dir / "starting").write_text("2")
    result = spectio_open("cluster")
    assert result.exit_code == 0, result.output
    logins = [s for s in fake_ssh.spectio() if s["argv"][0] == "login"]
    assert len(logins) == 3
    assert TICKET in opened(fake_ssh)


def test_first_start_ticket_retries_end(fake_ssh: FakeSsh, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("spectio.cli.open.TICKET_RETRY_S", 0)
    monkeypatch.setattr("spectio.cli.open.TICKET_WAIT_S", 0.5)
    (fake_ssh.dir / "starting").write_text("1000000")
    result = spectio_open("cluster")
    assert result.exit_code == 3, result.output
    assert "gave no link" in result.output
    assert not (fake_ssh.dir / "opened").exists()


def test_first_start_keeps_existing_data_dir(fake_ssh: FakeSsh) -> None:
    (fake_ssh.home / ".spectio").mkdir(mode=0o700)
    result = spectio_open("cluster")
    assert result.exit_code == 0, result.output
    started = [s["argv"] for s in fake_ssh.spectio()]
    assert ["init"] not in started
    assert ["serve", "--detach", "--no-link"] in started
    assert tunnel(fake_ssh)[-1] == "cluster"  # the node serve recorded


def test_login_shell_and_remote_cmd(fake_ssh: FakeSsh, home: Path) -> None:
    fake_ssh.tool("module", "#!/bin/sh\nexit 0\n")
    clusters_toml(home, '[cluster]\nremote_cmd = "module load spectio && spectio"\n')
    fake_ssh.state(STATE)
    result = spectio_open("cluster")
    assert result.exit_code == 0, result.output
    remote = [c for c in fake_ssh.calls() if c[0] != "-N"]
    assert remote and all(c[-1].startswith('"$SHELL" -lc ') for c in remote)
    shells = fake_ssh.shells()
    assert len(shells) == len(remote)
    assert all(s[1].startswith("{ module load spectio && spectio ") for s in shells)


def test_first_start_with_compound_remote_cmd_keeps_data_dir(fake_ssh: FakeSsh, home: Path) -> None:
    """`&&` in remote_cmd must not escape the `[ -d ~/.spectio ] ||` guard (CR-P3T24-01)."""
    fake_ssh.tool("module", "#!/bin/sh\nexit 0\n")
    clusters_toml(home, '[cluster]\nremote_cmd = "module load spectio && spectio"\n')
    (fake_ssh.home / ".spectio").mkdir(mode=0o700)
    result = spectio_open("cluster")
    assert result.exit_code == 0, result.output
    started = [s["argv"] for s in fake_ssh.spectio()]
    assert ["init"] not in started
    assert ["serve", "--detach", "--no-link"] in started


def test_stale_state_file_named_in_error(fake_ssh: FakeSsh) -> None:
    """A server.json whose server has stopped is not checked for liveness yet (FU-P3-48): the
    exit-3 message says the file may be stale (CR-P3T24-02)."""
    fake_ssh.state(STATE)
    (fake_ssh.dir / "dead").touch()
    result = spectio_open("cluster")
    assert result.exit_code == 3, result.output
    assert "may be stale" in result.output
    assert not (fake_ssh.dir / "opened").exists()


def test_no_stale_hint_for_another_node(fake_ssh: FakeSsh) -> None:
    """With --node on another node than server.json's, a failed login is not the file's fault:
    no hint to remove the lock of a live server (CR-P3T24-03)."""
    fake_ssh.state(STATE)
    (fake_ssh.dir / "dead").touch()
    result = spectio_open("cluster", "--node", "login2")
    assert result.exit_code == 3, result.output
    assert "may be stale" not in result.output


def test_no_stale_hint_after_first_start(fake_ssh: FakeSsh) -> None:
    """server.json was just written by serve --detach: it is not stale (CR-P3T24-03)."""
    (fake_ssh.dir / "dead").touch()
    result = spectio_open("cluster")
    assert result.exit_code == 3, result.output
    assert "may be stale" not in result.output


def test_remote_cmd_flag_beats_clusters_toml(fake_ssh: FakeSsh, home: Path) -> None:
    clusters_toml(home, '[cluster]\nremote_cmd = "nope"\n')
    fake_ssh.state(STATE)
    result = spectio_open("cluster", "--remote-cmd", "spectio")
    assert result.exit_code == 0, result.output


def test_clusters_toml_writable_by_others_refused(fake_ssh: FakeSsh, home: Path) -> None:
    clusters_toml(home, '[cluster]\nremote_cmd = "spectio"\n')
    (home / ".config" / "spectio" / "clusters.toml").chmod(0o622)
    result = spectio_open("cluster")
    assert result.exit_code == 3
    assert fake_ssh.calls() == []


def test_missing_remote_spectio_prints_install(fake_ssh: FakeSsh) -> None:
    (fake_ssh.dir / "bin" / "spectio").unlink()
    result = spectio_open("cluster")
    assert result.exit_code == 2, result.output
    assert "uv tool install spectio==0.0.1" in result.output
    assert len(fake_ssh.calls()) == 1  # the probe only: nothing installed, no tunnel


@pytest.mark.parametrize(
    "node", ["-oProxyCommand=x", "a b", "x;y", "\x1b]0;", "lögin1", "", "a" * 254, 7]
)
def test_rejects_bad_node_from_state_file(fake_ssh: FakeSsh, node: object) -> None:
    fake_ssh.state({**STATE, "host": node})
    result = spectio_open("cluster")
    assert result.exit_code == 3, result.output
    assert len(fake_ssh.calls()) == 1  # the state read; ssh never reaches that node


@pytest.mark.parametrize(
    "change", [{"port": 80}, {"port": 70000}, {"port": "8123"}, {"port": True}, {"pid": "1"}]
)
def test_rejects_bad_port_or_pid_from_state_file(fake_ssh: FakeSsh, change: dict[str, Any]) -> None:
    fake_ssh.state({**STATE, **change})
    result = spectio_open("cluster")
    assert result.exit_code == 3, result.output
    assert len(fake_ssh.calls()) == 1


@pytest.mark.parametrize(
    "args", [["--", "-oProxyCommand=x"], ["cluster", "--node", "a;b"], ["a b"]]
)
def test_rejects_bad_host_or_node_flag(fake_ssh: FakeSsh, args: list[str]) -> None:
    result = spectio_open(*args)
    assert result.exit_code == 3, result.output
    assert fake_ssh.calls() == []


def test_ssh_argv_has_double_dash(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    assert spectio_open("cluster").exit_code == 0
    for call in fake_ssh.calls():
        dash = call.index("--")
        assert call[dash + 1] in ("cluster", "login3")
        options = call[:dash]
        for i, word in enumerate(options):
            if word == "-o":
                assert "login3" not in options[i + 1]
                assert "cluster" not in options[i + 1]


def test_tunnel_argv_hardened(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    assert spectio_open("cluster", "--local-port", "18555").exit_code == 0
    assert tunnel(fake_ssh) == [
        "-N",
        "-o",
        "ExitOnForwardFailure=yes",
        "-L",
        "127.0.0.1:18555:127.0.0.1:8123",
        "--",
        "login3",
    ]
    for call in fake_ssh.calls():
        assert not any("HostKey" in w or "KnownHosts" in w for w in call)


def test_remote_quoting_two_layers(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    cmd = """SPECTIO_X='it'"'"'s "q" $HOME `x`' spectio"""
    result = spectio_open("cluster", "--remote-cmd", cmd)
    assert result.exit_code == 0, result.output
    assert all(s[1].startswith("{ " + cmd + " ") for s in fake_ssh.shells())
    assert {s["x"] for s in fake_ssh.spectio()} == {"""it's "q" $HOME `x`"""}
    login = [c for c in fake_ssh.calls() if c[0] != "-N"][-1][-1]
    assert login == '"$SHELL" -lc ' + shlex.quote(
        "{ " + cmd + " " + shlex.join(["login", "--print-link", "--json"]) + "; }"
    )


def test_url_built_locally(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    (fake_ssh.dir / "login.out").write_text(
        f"http://evil.example/auth/link#{TICKET}\n"
        f'spectio-ticket-v1 {{"ticket": "{TICKET}"}}\n'
        "http://evil.example/\n"
    )
    result = spectio_open("cluster", "--local-port", "18556")
    assert result.exit_code == 0, result.output
    assert opened(fake_ssh) == f"http://127.0.0.1:18556/auth/link#{TICKET}"
    assert "evil" not in result.output


@pytest.mark.parametrize(
    "out",
    [
        f"http://127.0.0.1:8123/auth/link#{TICKET}",  # a URL, no ticket line
        'spectio-ticket-v1 {"ticket": "short"}',
        'spectio-ticket-v1 {"ticket": "' + "a" * 42 + '\\u001b"}',
        "spectio-ticket-v1 not json",
    ],
)
def test_bad_ticket_line_refused(fake_ssh: FakeSsh, out: str) -> None:
    fake_ssh.state(STATE)
    (fake_ssh.dir / "login.out").write_text(out + "\n")
    result = spectio_open("cluster")
    assert result.exit_code == 3, result.output
    assert not (fake_ssh.dir / "opened").exists()


def test_free_local_port_and_link(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    result = spectio_open("cluster")
    assert result.exit_code == 0, result.output
    forward = tunnel(fake_ssh)[tunnel(fake_ssh).index("-L") + 1]
    bind, lport, rhost, rport = forward.split(":")
    assert (bind, rhost, rport) == ("127.0.0.1", "127.0.0.1", "8123")
    assert 1024 <= int(lport) <= 65535
    assert opened(fake_ssh) == f"http://127.0.0.1:{lport}/auth/link#{TICKET}"


def test_no_browser_prints_link(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    (fake_ssh.dir / "linger").write_text("2")  # no browser closes it: it ends on its own
    result = spectio_open("cluster", "--no-browser", "--local-port", "18557")
    assert result.exit_code == 0, result.output
    assert not (fake_ssh.dir / "opened").exists()
    assert f"http://127.0.0.1:18557/auth/link#{TICKET}" in result.output


def test_ssh_failure_exits_3(fake_ssh: FakeSsh) -> None:
    (fake_ssh.dir / "down").touch()
    result = spectio_open("cluster")
    assert result.exit_code == 3, result.output
    assert "Connection refused" in result.output


def test_tunnel_that_fails_exits_3(fake_ssh: FakeSsh) -> None:
    fake_ssh.state(STATE)
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        port = busy.getsockname()[1]
        result = spectio_open("cluster", "--local-port", str(port))
    assert result.exit_code == 3, result.output
    assert not (fake_ssh.dir / "opened").exists()
