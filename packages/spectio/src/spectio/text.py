"""Text shown from files and engine output: terminal escapes, control and format characters
removed (dev-env §15.3 req. 13). One implementation for the server's file views and the
runner's failure messages (SEC-NFERR-02); `spectio_server.files.redact` re-exports it."""

import re

# CSI (ESC [ or the 8-bit CSI, … final), OSC (ESC ] or the 8-bit OSC, … BEL, ST or ESC \),
# other two-character escapes, the C0 and C1 controls left except tab and newline, and the bidi
# and other format controls, line and paragraph separators (SEC-P3T28-07 r1, SEC-P3T28-08 r3).
# An OSC is removed whole only when its terminator comes within `OSC_MAX` characters; else its
# introducer alone goes (by the C1 branch below for the 8-bit one), not the rest of the text
# (SEC-PRE-FU85-R1-11). Its body stops at an ESC or another OSC and is possessive, so each
# character is read once.
FORMAT_CHARS = r"\u061c\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb"
OSC_MAX = 4096
_ESCAPES = re.compile(
    r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]"
    rf"|(?:\x1b\]|\x9d)[^\x07\x1b\x9c\x9d]{{0,{OSC_MAX}}}+(?:\x07|\x1b\\|\x9c)"
    r"|\x1b[@-_]?"
    r"|[\x00-\x08\x0b-\x1f\x7f-\x9f]"
    rf"|[{FORMAT_CHARS}]"
)


def strip_escapes(text: str) -> str:
    """`text` with terminal escape sequences, control and format characters removed (tab and
    newline kept)."""
    return _ESCAPES.sub("", text)
