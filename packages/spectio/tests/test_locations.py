"""The shared location checks (`spectio.locations`, api §5.6, SEC-PRE-FU87-02): every refusal is
a ValueError whose message never quotes the value (SEC-P3FU87A-01)."""

from collections.abc import Callable

import pytest

from spectio import locations

SECRET = "SECRET"  # noqa: S105 - a marker, not a password
FULLWIDTH_AT = chr(0xFF20)  # NFKC turns it into "@"
CHECKS: list[tuple[Callable[[str], object], str]] = [
    (locations.git_url, f"https://u:SECRET{FULLWIDTH_AT}host/r"),  # urlsplit: NFKC netloc error
    (locations.git_url, "https://[SECRET]/r"),  # not an IPv6 address
    (locations.git_url, "https://SECRET.example:99999/r"),  # a port out of range
    (locations.git_url, "https://u:SECRET@host/r"),
    (locations.git_url, "ftp://SECRET/r"),
    (locations.check_location, "https://[SECRET]/r"),
    (locations.check_location, "SECRET‮"),
    (locations.check_revision, "-SECRET"),
    (locations.check_params_file, "SECRET.txt"),
]


@pytest.mark.parametrize(("check", "value"), CHECKS)
def test_refusal_message_never_quotes_the_value(check: Callable[[str], object], value: str) -> None:
    with pytest.raises(ValueError) as caught:
        check(value)
    assert SECRET not in str(caught.value)
