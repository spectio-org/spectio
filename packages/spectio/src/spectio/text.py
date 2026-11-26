"""Text shown from files and engine output: terminal escapes, control and format characters
removed (dev-env §15.3 req. 13). One implementation for the server's file views and the
runner's failure messages (SEC-NFERR-02); `spectio_server.files.redact` re-exports it."""

import re

from spectio_sdk.events import hide_quoted_commands

HIDDEN = "«hidden»"  # as spectio_server.files.redact
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


_SHELL_HEADER = re.compile(r"([ \t]*)shell:")
# The end of a quote whose `Command '` start is not in the text (a window cut inside it)
_QUOTE_END = re.compile(r"(?s)\A.*' (returned non-zero exit status \d+|died with <[^>]*>)")


def hide_snakemake_commands(text: str) -> str:
    """`text`, the engine's output or a message that quotes it, with the shell commands of a
    Snakemake job hidden (SEC-SMKFAIL-01): the `shell:` block of `Error in rule X:` and of each
    job `printshellcmds` prints, as one `shell: «hidden»` line (to the next less-indented line);
    the `Command '…' returned non-zero exit status N` of a `CalledProcessError`, as the SDK
    hides it from `snakemake.error`. Fails closed: an end with no start hides everything back to
    the text's start, a start with no end hides everything after it."""
    kept: list[str] = []
    inside: int | None = None  # the indent of the `shell:` line whose block is being hidden
    for line in text.split("\n"):
        indent = len(line) - len(line.lstrip())
        if inside is not None and (not line.strip() or indent > inside):
            continue
        header = _SHELL_HEADER.match(line)
        inside = len(header[1]) if header else None
        kept.append(f"{header[1]}shell: {HIDDEN}" if header else line)
    hidden = hide_quoted_commands("\n".join(kept))
    hidden = _QUOTE_END.sub(rf"Command {HIDDEN} \1", hidden)
    lines = hidden.split("\n")
    for i, line in enumerate(lines):
        if "Command '" in line:
            return "\n".join([*lines[:i], f"Command: {HIDDEN}"])
    return hidden
