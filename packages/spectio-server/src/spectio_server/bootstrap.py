"""What the `spectio` CLI asks of the server package: the database directory, the rows of a
new install, and doctor's database checks.

The CLI imports this module only, and only inside the commands that need it, so `spectio`
alone still runs (architecture §6); the import-linter contracts name these edges.
"""

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, insert, select, update

from spectio_server.ids import new_id
from spectio_server.store.db import (
    MOUNTINFO,
    NETWORK_FS,
    UnsafeDatabase,
    _owner,
    _private_dir,
    check_sqlite_version,
    default_db_dir,
    fs_type,
    open_db,
    preferred_db_dir,
)
from spectio_server.store.schema import environments, principals, projects, runners
from spectio_server.store.writer import Writer

__all__ = ["UnsafeDatabase", "db_checks", "default_db_dir", "init_store", "preferred_db_dir"]


def init_store(db_dir: Path, *, user: str, kind: str, config: dict[str, Any], version: str) -> bool:
    """The rows of P1 Assumption 18: the user's principal, project `default`, one environment
    (`kind`, `config`) and its runner. Run again, it updates the environment and adds nothing.
    True when the rows were created."""
    engine, _ = open_db(db_dir)
    writer = Writer(engine)
    try:
        return writer.submit(lambda conn: _tenancy(conn, user, kind, config, version)).result()
    finally:
        writer.close()
        engine.dispose()


def _tenancy(conn: Connection, user: str, kind: str, config: dict[str, Any], version: str) -> bool:
    env_id = conn.execute(
        select(environments.c.id).order_by(environments.c.created_at).limit(1)
    ).scalar()
    if env_id is not None:
        conn.execute(
            update(environments).where(environments.c.id == env_id).values(kind=kind, config=config)
        )
        return False
    now = datetime.now(UTC)
    usr, grp, env = new_id("usr"), new_id("grp"), new_id("env")
    # The first principal names itself as creator; there is no `system` row to name.
    conn.execute(
        insert(principals).values(
            id=usr, kind="user", display_name=user, created_at=now, created_by=usr
        )
    )
    mine = {"created_at": now, "created_by": usr}
    conn.execute(
        insert(projects).values(id=new_id("prj"), owning_group_id=grp, name="default", **mine)
    )
    conn.execute(
        insert(environments).values(id=env, owning_group_id=grp, kind=kind, config=config, **mine)
    )
    conn.execute(
        insert(runners).values(
            id=new_id("rnr"), environment_id=env, principal_id=usr, version=version, **mine
        )
    )
    return True


def db_checks(
    db_dir: Path, mountinfo: Path | None = None, *, fallback: bool = False
) -> list[tuple[str, str, str]]:
    """`(status, check, detail)` for the SQLite library and the database directory: the
    network-file-system and 0700 checks (architecture §7.2), or a warning when it is missing,
    since the next start rebuilds it (P1 Assumption 21). `fallback`: `db_dir` is the default,
    so a squatted one is a warning, since the next start uses a `mkdtemp` directory (§15.3)."""
    found = []
    try:
        check_sqlite_version(sqlite3.sqlite_version)
        found.append(("ok", "sqlite", sqlite3.sqlite_version))
    except UnsafeDatabase as exc:
        found.append(("fail", "sqlite", str(exc)))
    if not db_dir.exists() and not db_dir.is_symlink():
        found.append(("warn", "db_dir", f"{db_dir} is missing: the next start rebuilds it"))
        return found
    private, owner = _private_dir(db_dir, os.getuid())
    if not private:
        who = f"(owner {_owner(owner)})"
        found.append(
            (
                "warn",
                "db_dir",
                f"{db_dir} is not a private directory of this user {who}: "
                "the next start uses a mkdtemp directory",
            )
            if fallback
            else (
                "fail",
                "db_dir",
                f"{db_dir} must be a directory of this user with mode 0700 {who}",
            )
        )
        return found
    try:
        kind = fs_type(db_dir, mountinfo or MOUNTINFO)
    except UnsafeDatabase as exc:
        found.append(("fail", "db_dir", str(exc)))
        return found
    if kind in NETWORK_FS:
        found.append(
            (
                "fail",
                "db_dir",
                f"{db_dir} is on a {kind} file system, where SQLite is unsafe: "
                "choose a node-local directory with spectio init --db-dir",
            )
        )
    else:
        found.append(("ok", "db_dir", f"{db_dir} ({kind}, 0700)"))
    return found
