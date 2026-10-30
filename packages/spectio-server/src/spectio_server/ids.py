"""Row IDs: ULID text with a type prefix, such as `run_01K8T2F1XT…` (api §4, §7)."""

import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_id(prefix: str) -> str:
    """`<prefix>_` and a ULID: 48 bits of milliseconds, then 80 random bits, in Crockford base32."""
    value = (time.time_ns() // 1_000_000) << 80 | secrets.randbits(80)
    chars = [_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5)]
    return f"{prefix}_{''.join(chars)}"
