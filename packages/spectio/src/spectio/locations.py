"""How a pipeline location and revision are written (api §5, Imports are untrusted input; api
§5.6, SEC-PRE-FU87-02): pure checks shared by the server's inspect and `POST /runs`
(`spectio_server.api.workflows`, which wraps the errors in `Invalid` for its field) and by the
catalog file (`spectio.catalog`). Each raises ValueError with a message that never quotes the
value; none reads a directory or contacts a remote.

A location is an absolute path, or a Git repository: an `owner/repo` name (GitHub), or an
`https://` or `ssh://` URL, with no credentials and plain path parts only. Neither a location
nor a revision may hold a control character (SEC-P3T09-R5-05), and a revision never starts with
`-` (G5).
"""

import re
import unicodedata
from urllib.parse import urlsplit

GIT_SCHEMES: tuple[str, ...] = ("https", "ssh")
MAX_LOCATION = 4096  # characters (FU-P3-17)
GITHUB = "https://github.com"
SHORT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_][A-Za-z0-9._-]{0,99}")
URL_CHARS = re.compile(r"[A-Za-z0-9._~:/@+-]+")  # no space, quote, `%`, `?`, `#` or backslash
HOST = re.compile(r"[a-z0-9]([a-z0-9.-]{0,252}[a-z0-9])?")
PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,99}")  # never "", "." or ".."
REVISION = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._/-]{0,199}")  # never an option, never a path
PARAMS_SUFFIXES = (".json", ".yaml", ".yml")


def refuse_control(value: str) -> None:
    """Control characters, and the format and separator ones (Cf, Zl, Zp: bidi overrides,
    zero-width spaces, line separators) that hide or reorder text (FU-P3-17)."""
    if any(
        ord(c) < 32 or 127 <= ord(c) < 160 or unicodedata.category(c) in ("Cf", "Zl", "Zp")
        for c in value
    ):
        raise ValueError("must not hold control, format or separator characters")


def git_url(location: str, schemes: tuple[str, ...] = GIT_SCHEMES) -> tuple[str, tuple[str, ...]]:
    """The URL of a Git location, and the parts of the directory it is fetched into (`host`,
    then the path)."""
    if SHORT_NAME.fullmatch(location):
        location = f"{GITHUB}/{location}"
    url = urlsplit(location)
    if url.scheme not in schemes or not location.startswith(f"{url.scheme}://"):
        allowed = ", ".join(f"{s}://" for s in schemes)
        raise ValueError(f"give an absolute path, an owner/repo name or a URL ({allowed})")
    if not URL_CHARS.fullmatch(location):
        raise ValueError("the URL holds a character Spectio does not accept")
    try:
        host, user, password = url.hostname or "", url.username, url.password
        url.port  # noqa: B018 - raises ValueError on a bad port
    except ValueError:  # its message quotes the port
        raise ValueError("not a URL: a port is not a number from 0 to 65535") from None
    if password is not None or (user is not None and url.scheme != "ssh"):
        raise ValueError("credentials do not belong in the URL")
    if url.scheme == "file":
        if host not in ("", "localhost"):
            raise ValueError("a file:// URL names no host")
        host = "local"
    elif not HOST.fullmatch(host):
        raise ValueError("the URL names no valid host")
    parts = url.path.strip("/").split("/")
    parts[-1] = parts[-1].removesuffix(".git")
    if len(parts) > 20 or not all(PART.fullmatch(p) for p in parts):
        raise ValueError("the URL's path must be plain names: no '.', '..' or ''")
    return location, (host, *parts)


def check_location(location: str) -> str:
    """A location as `workflows.resolve` takes it, without the fetch and without reading the
    directory (api §5.6)."""
    if len(location) > MAX_LOCATION:
        raise ValueError(f"longer than {MAX_LOCATION} characters")
    refuse_control(location)
    if not location.startswith("/"):
        git_url(location)
    return location


def check_revision(revision: str | None) -> str:
    if not revision:
        raise ValueError("a Git repository needs a revision: a tag, a branch or a commit")
    refuse_control(revision)
    if not REVISION.fullmatch(revision) or ".." in revision or revision.endswith("/"):
        raise ValueError(
            "a tag, a branch or a commit: letters, digits, '.', '_', '-' and '/', "
            "never starting with '-'"
        )
    return revision


def check_params_file(value: str) -> str:
    """A path inside the pipeline: 1 to 8 PART names joined by `/`, ending .json, .yaml or .yml
    (api §5.6)."""
    parts = value.split("/")
    if len(parts) > 8 or not all(PART.fullmatch(p) for p in parts):
        raise ValueError("a path inside the pipeline: 1 to 8 plain names joined by '/'")
    if not value.endswith(PARAMS_SUFFIXES):
        raise ValueError("a .json, .yaml or .yml file")
    return value
