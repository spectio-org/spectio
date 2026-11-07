"""Who listens on a loopback port (CR-P3T12-01): login dials 127.0.0.1, so a user's own socket
on 127.0.0.2 coming first in /proc/net/tcp must not hide another uid's listener on 127.0.0.1."""

from pathlib import Path

from spectio.ports import port_owners

HEAD = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid\n"
ROW = "   {n}: {addr}:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000  {uid} 0 1\n"


def test_port_owners_lists_every_uid(tmp_path: Path) -> None:
    table = tmp_path / "tcp"
    table.write_text(
        HEAD
        + ROW.format(n=0, addr="0200007F", uid=1000)  # the user's own, 127.0.0.2:8080
        + ROW.format(n=1, addr="0100007F", uid=1001)  # another uid's, 127.0.0.1:8080
    )
    assert port_owners(8080, (str(table), str(tmp_path / "absent"))) == {1000, 1001}
    assert port_owners(8081, (str(table),)) == set()
