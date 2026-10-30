"""Row IDs: ULID text with a type prefix, such as `run_01K8T2F1XT…` (api §4, §7).

IDs are monotonic within the process, as in the ULID spec's monotonic mode: one made in the same
millisecond as the last one (or after the clock went back) is the last one plus 1. So the rows one
transaction inserts sort by ID in insertion order, the first-seen order of `/processes`.
"""

import secrets
import threading
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_lock = threading.Lock()
_last = 0


def new_id(prefix: str) -> str:
    """`<prefix>_` and a ULID: 48 bits of milliseconds, then 80 random bits, in Crockford base32."""
    global _last
    with _lock:
        value = max((time.time_ns() // 1_000_000) << 80 | secrets.randbits(80), _last + 1)
        _last = value
    chars = [_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5)]
    return f"{prefix}_{''.join(chars)}"
