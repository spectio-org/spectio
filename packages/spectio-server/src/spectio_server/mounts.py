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
import re
import stat
from collections.abc import Sequence
from pathlib import Path

MAX_VALUES = 10_000  # scalar values of `params` read at most
MAX_DEPTH = 32  # of `params`, as the launch body is checked too
MAX_CONF_BYTES = 256 * 1024  # of the site's Apptainer configuration, read at most
# The site's configuration, in this order: the first readable file decides (api §5.2).
CONFIG_FILES = ("/etc/apptainer/apptainer.conf", "/etc/singularity/singularity.conf")
# In the image or mounted by Apptainer itself: never refused, whatever the site binds.
SYSTEM_ROOTS = ("/dev", "/proc", "/sys", "/usr", "/opt", "/etc", "/bin", "/sbin", "/lib", "/lib64")
# A `bind` option, not a destination: `src:ro` mounts `src` at its own path.
BIND_OPTIONS = ("ro", "rw")
# A path the refusal may echo and build a suggestion from (SEC-mounts-01): absolute, one line,
# no space, no quote — nothing a terminal would read as two words or an option.
ECHOED = re.compile(r"/[A-Za-z0-9._+@/-]+")  # matched in full


def env_binds() -> str:
    """`APPTAINER_BIND`, else `SINGULARITY_BIND`, else empty (api §5.2)."""
    return os.environ.get("APPTAINER_BIND") or os.environ.get("SINGULARITY_BIND") or ""


def _paths(params: object) -> list[str]:
    """The string values of `params`, the dicts and lists walked (bounded: MAX_VALUES values,
    MAX_DEPTH levels); a deeper or larger `params` is read only this far. The dicts and lists
    between the values are walked but not counted: the launch body's 1 MiB cap (the `413` of a
    write) bounds how many there can be."""
    found: list[str] = []
    seen = 0
    todo: list[tuple[object, int]] = [(params, 0)]
    while todo:
        node, level = todo.pop()
        if isinstance(node, (dict, list)):
            if level < MAX_DEPTH:
                children = node.values() if isinstance(node, dict) else node
                todo.extend((child, level + 1) for child in children)
        else:
            seen += 1
            if seen > MAX_VALUES:
                break
            if isinstance(node, str):
                found.append(node)
    return found


def _is_candidate(value: str) -> bool:
    """An absolute path: starts with `/` (a URL never does) and holds no control character."""
    return value.startswith("/") and not any(ord(c) < 0x20 or ord(c) == 0x7F for c in value)


def _bind_roots(value: str) -> list[str]:
    """A bind value as a comma list of `src[:dst[:opts]]`, each bind's visible root kept: `dst`
    when a second field names a destination (a bare option does not), else `src` — a bind mounts
    `src` at `dst`, so the container sees the files there (CR-02)."""
    roots = []
    for part in value.split(","):
        fields = [field.strip() for field in part.split(":")]
        root = fields[1] if len(fields) > 1 and fields[1] not in ("", *BIND_OPTIONS) else fields[0]
        roots.append(root)
    return roots


def _args_roots(apptainer_args: str) -> list[str]:
    """The roots of every `-B x`, `--bind x`, `-B=x` and `--bind=x` in `apptainer_args`."""
    words = apptainer_args.split()
    roots = []
    for i, word in enumerate(words):
        if word in ("-B", "--bind") and i + 1 < len(words):
            roots.extend(_bind_roots(words[i + 1]))
        elif word.startswith("-B="):
            roots.extend(_bind_roots(word[len("-B=") :]))
        elif word.startswith("--bind="):
            roots.extend(_bind_roots(word[len("--bind=") :]))
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
    extra_roots: Sequence[str] = (),
) -> list[str]:
    """The run's absolute paths the containers would not see, sorted and unique.

    The visible roots are the user's home, `/tmp` and the launch directory (Apptainer mounts
    these by default; https://apptainer.org/docs/user/latest/bind_paths_and_mounts.html), the
    fixed system roots of the image and of Apptainer itself (SYSTEM_ROOTS), every root of a
    bind in the environment's `apptainer_args`, every root of the site's configuration and of
    `env_binds`, and `extra_roots` — roots the caller knows the containers see, passed by value
    and never parsed as binds (the pipeline's directory, CR-05). A `params` value is a
    candidate when it is an absolute path without a control character, normalised; a candidate
    under no root is returned."""
    roots = [
        os.path.normpath(root)
        for root in (
            str(home),
            "/tmp",  # noqa: S108 - a root Apptainer mounts by default, not a file this code uses
            str(launch_dir),
            *SYSTEM_ROOTS,
            *_args_roots(apptainer_args),
            *(root for value in (*site_binds, env_binds) for root in _bind_roots(value)),
            *extra_roots,
        )
    ]
    candidates = {os.path.normpath(v) for v in _paths(params) if _is_candidate(v)}
    return sorted(p for p in candidates if not any(_under(p, root) for root in roots))


def echoed_paths(paths: list[str]) -> list[str]:
    """The paths the refusal may echo and suggest (SEC-mounts-01): those of `ECHOED`. The
    others stay counted, but are never printed nor used for a suggestion."""
    return [p for p in paths if ECHOED.fullmatch(p)]


def suggested_binds(paths: list[str]) -> list[str]:
    """The binds to suggest for `paths`: each path's first path component, sorted and unique."""
    return sorted({"/" + path.strip("/").split("/", 1)[0] for path in paths if path.strip("/")})


def site_bind_paths() -> list[str]:
    """The site's `bind path = <src[:dst]>` values, from the first readable regular file of
    `CONFIG_FILES` (api §5.2): comments and other directives ignored, at most MAX_CONF_BYTES
    read — a read that hit the cap drops its last line, which may be cut in half — and nothing
    readable, or no regular file, gives an empty list. Compute nodes share the login node's
    file [to be validated]."""
    for name in CONFIG_FILES:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        except OSError:
            continue
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                continue
            raw = b""
            while len(raw) < MAX_CONF_BYTES and (chunk := os.read(fd, MAX_CONF_BYTES - len(raw))):
                raw += chunk
        except OSError:
            continue
        finally:
            os.close(fd)
        lines = raw.split(b"\n")
        if len(raw) == MAX_CONF_BYTES:
            lines = lines[:-1]  # the last line may be cut in half by the cap
        found: list[str] = []
        for line in lines:
            text = line.decode(errors="ignore").strip()
            if text.startswith("#") or "=" not in text:
                continue
            key, _, value = text.partition("=")
            if key.strip() == "bind path" and value.strip():
                found.append(value.strip())
        return found
    return []
