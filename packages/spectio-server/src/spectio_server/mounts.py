"""The paths a Snakemake launch's containers would not see (built 2026-11-25; api §5.2).

Seen on a cluster: data under a scratch file system was not mounted in the containers, so the
rules failed with "No such file or directory" after the environments were built and the jobs
were submitted. `unmounted_paths` answers, from the launch body and the environment's Apptainer
options alone, which of the paths the run uses would not be visible inside the containers; the
launch refuses them until they are bound or the user confirms.

What it reads: the launch's `params` and the `bind path` lines of the site's Apptainer
configuration. No container is started, no path is stat'd, and a path a Snakefile builds while
it runs is not seen: the check reads configuration only.
"""

import os
from pathlib import Path

MAX_VALUES = 10_000  # scalar values of `params` read at most
MAX_DEPTH = 32  # of `params`, as the launch body is checked too
MAX_CONF_BYTES = 256 * 1024  # of the site's Apptainer configuration, read at most
# The site's configuration, in this order: the first readable file decides (api §5.2).
CONFIG_FILES = ("/etc/apptainer/apptainer.conf", "/etc/singularity/singularity.conf")


def env_binds() -> str:
    """`APPTAINER_BIND`, else `SINGULARITY_BIND`, else empty (api §5.2)."""
    return os.environ.get("APPTAINER_BIND") or os.environ.get("SINGULARITY_BIND") or ""


def _paths(params: object) -> list[str]:
    """The string values of `params`, the dicts and lists walked (bounded: MAX_VALUES values,
    MAX_DEPTH levels); a deeper or larger `params` is read only this far."""
    found: list[str] = []
    seen = [0]

    def walk(node: object, level: int) -> None:
        if isinstance(node, dict):
            if level >= MAX_DEPTH:
                return
            for value in node.values():
                if seen[0] >= MAX_VALUES:
                    return
                walk(value, level + 1)
        elif isinstance(node, list):
            if level >= MAX_DEPTH:
                return
            for value in node:
                if seen[0] >= MAX_VALUES:
                    return
                walk(value, level + 1)
        else:
            seen[0] += 1
            if isinstance(node, str):
                found.append(node)

    walk(params, 0)
    return found


def _is_candidate(value: str) -> bool:
    """An absolute path: starts with `/` (a URL never does) and holds no control character."""
    return value.startswith("/") and not any(ord(c) < 0x20 or ord(c) == 0x7F for c in value)


def _sources(value: str) -> list[str]:
    """A bind value as a comma list of `src[:dst[:opts]]`, each `src` kept."""
    return [part.split(":", 1)[0].strip() for part in value.split(",")]


def _args_roots(apptainer_args: str) -> list[str]:
    """The `src` of every `-B x`, `--bind x`, `-B=x` and `--bind=x` in `apptainer_args`."""
    words = apptainer_args.split()
    roots = []
    for i, word in enumerate(words):
        if word in ("-B", "--bind") and i + 1 < len(words):
            roots.extend(_sources(words[i + 1]))
        elif word.startswith("-B="):
            roots.extend(_sources(word[len("-B=") :]))
        elif word.startswith("--bind="):
            roots.extend(_sources(word[len("--bind=") :]))
    return roots


def _under(candidate: str, root: str) -> bool:
    """`candidate` equals `root` or is under it by path components, so `/scratchy` is not under
    `/scratch`."""
    return candidate == root or root == "/" or candidate.startswith(root + "/")


def unmounted_paths(
    params: object,
    apptainer_args: str,
    *,
    home: Path,
    launch_dir: Path,
    site_binds: list[str],
    env_binds: str,
) -> list[str]:
    """The run's absolute paths the containers would not see, sorted and unique.

    The visible roots are the user's home, `/tmp` and the launch directory (Apptainer mounts
    these by default; https://apptainer.org/docs/user/latest/bind_paths_and_mounts.html), every
    `src` of a bind in the environment's `apptainer_args`, and every `src` of the site's
    configuration and of `env_binds`. A `params` value is a candidate when it is an absolute
    path without a control character, normalised; a candidate under no root is returned."""
    sources = [source for value in (*site_binds, env_binds) for source in _sources(value)]
    roots = [
        os.path.normpath(root)
        for root in (
            str(home),
            "/tmp",  # noqa: S108 - a root Apptainer mounts by default, not a file this code uses
            str(launch_dir),
            *_args_roots(apptainer_args),
            *sources,
        )
        if root
    ]
    candidates = {os.path.normpath(v) for v in _paths(params) if _is_candidate(v)}
    return sorted(p for p in candidates if not any(_under(p, root) for root in roots))


def suggested_binds(paths: list[str]) -> list[str]:
    """The binds to suggest for `paths`: each path's first path component, sorted and unique."""
    return sorted({"/" + path.strip("/").split("/", 1)[0] for path in paths if path.strip("/")})


def site_bind_paths() -> list[str]:
    """The site's `bind path = <src[:dst]>` values, from the first readable file of
    `CONFIG_FILES` (api §5.2): comments and other directives ignored; nothing readable, or a
    value past MAX_CONF_BYTES, gives an empty list. Compute nodes share the login node's file
    [to be validated]."""
    for name in CONFIG_FILES:
        try:
            with open(name, "rb") as f:
                raw = f.read(MAX_CONF_BYTES)
        except OSError:
            continue
        found: list[str] = []
        for line in raw.decode(errors="ignore").splitlines():
            text = line.strip()
            if text.startswith("#") or "=" not in text:
                continue
            key, _, value = text.partition("=")
            if key.strip() == "bind path" and value.strip():
                found.append(value.strip())
        return found
    return []
