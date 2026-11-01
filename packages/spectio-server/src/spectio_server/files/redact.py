"""What a served file shows: `.command.run` with its values hidden, and text with no terminal
escape sequences (dev-env §15.3 req. 13, SEC-155, SEC-158; architecture §13.7).

`redact_command_run` reads the wrapper with a shell lexer, not a line pattern: POSIX quoting,
quoted values over several lines, `$'…'`, `$(…)`, `${…}`, backquotes and here-documents (whose
body is read as shell too: Nextflow writes the container environment as `export` lines inside
`cat << EOF`, `SimpleFileCopyStrategy.groovy:398-415`, v26.10.4). It hides the value of every
assignment word:

- at the start of a simple command (`FOO=bar cmd`, a `beforeScript` assignment,
  `SINGULARITYENV_X=…`, `APPTAINERENV_X=…`), an array value `NAME=(…)` included;
- after `export`, `declare`, `local`, `readonly`, `typeset` and `env`, the word quoted or not;
- after `-e` or `--env`, or in `--env=NAME=value` (Docker, Podman), the word quoted or not.

Each becomes `NAME=«hidden»`. It fails closed: from the line where the lexer meets something it
cannot read (a quote or a here-document left open, or constructs nested more than `MAX_NESTING`
deep), every line is `«hidden»`. Values inside a
command substitution or a parameter expansion (`${X:+NAME=v}`) are not looked into; that the
wrappers of every container engine fit these forms is [to be validated] (req. 13).
"""

import re

HIDDEN = "«hidden»"
MAX_NESTING = 64  # `$(`, `${`, `"` and here-documents inside one another (SEC-P3T28-04)

# A name (with an optional array index) and `=` or `+=`, at the very start of a word.
_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\[[^\]\n]*\])?\+?=")
_DECLARE = frozenset({"export", "declare", "local", "readonly", "typeset", "env"})
_ENV_FLAGS = frozenset({"-e", "--env"})
# Words after which a new command starts.
_RESERVED = frozenset(
    {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "!", "{", "}", "time"}
)
_OPS = ";&|()<>"
_SPACE = " \t"

# CSI (ESC [ … final), OSC (ESC ] … BEL or ESC \), other two-character escapes, then the C0
# and C1 controls left, except tab and newline.
_ESCAPES = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?"
    r"|\x1b[@-_]?"
    r"|[\x00-\x08\x0b-\x1f\x7f-\x9f]"
)


def strip_escapes(text: str) -> str:
    """`text` with terminal escape sequences and control characters removed (tab and newline
    kept)."""
    return _ESCAPES.sub("", text)


class _Unreadable(Exception):
    def __init__(self, pos: int) -> None:
        super().__init__(pos)
        self.pos = pos


class _Lexer:
    """Words and operators of one shell text; `edits` collects (start, end, replacement)."""

    def __init__(self, text: str, partial: bool = False, depth: int = 0) -> None:
        self.s = text
        self.partial = partial  # the text is cut: a here-document may end with it
        self.depth = depth  # constructs open around the one being read
        self.i = 0
        self.edits: list[tuple[int, int, str]] = []
        self.heredocs: list[tuple[str, bool]] = []  # (delimiter, strip tabs) to read at newline

    # --- skipping nested constructs: each returns the index past its end ---

    def _nest(self, i: int) -> None:
        self.depth += 1
        if self.depth > MAX_NESTING:
            raise _Unreadable(i)

    def _closing(self, i: int, end: str) -> int:
        """Past the `end` that closes a construct whose body starts at `i` ('…' or $'…')."""
        escapes = end == "$'"
        j = i
        while j < len(self.s):
            c = self.s[j]
            if escapes and c == "\\":
                j += 2
                continue
            if c == "'":
                return j + 1
            j += 1
        raise _Unreadable(i)

    def _double(self, i: int) -> int:
        """Past the `"` that closes a double-quoted text starting at `i` (after its `"`)."""
        self._nest(i)
        j = i
        while j < len(self.s):
            c = self.s[j]
            if c == "\\":
                j += 2
            elif c == '"':
                self.depth -= 1
                return j + 1
            elif c == "$" and self.s.startswith(("$(", "${"), j):
                j = self._dollar(j)
            elif c == "`":
                j = self._backquote(j + 1)
            else:
                j += 1
        raise _Unreadable(i)

    def _backquote(self, i: int) -> int:
        j = i
        while j < len(self.s):
            if self.s[j] == "\\":
                j += 2
            elif self.s[j] == "`":
                return j + 1
            else:
                j += 1
        raise _Unreadable(i)

    def _dollar(self, i: int) -> int:
        """Past `$(…)`, `$((…))` or `${…}` starting at `i` (its `$`)."""
        self._nest(i)
        opener = self.s[i + 1]
        closer = ")" if opener == "(" else "}"
        depth, j = 1, i + 2
        start_of_word = True
        while j < len(self.s):
            c = self.s[j]
            if c == "\\":
                j += 2
            elif c == "'":
                j = self._closing(j + 1, "'")
            elif c == '"':
                j = self._double(j + 1)
            elif c == "`":
                j = self._backquote(j + 1)
            elif c == "$" and self.s.startswith(("$(", "${"), j):
                j = self._dollar(j)
            elif c == "$" and self.s.startswith("$'", j):
                j = self._closing(j + 2, "$'")
            elif c == "#" and closer == ")" and start_of_word:
                newline = self.s.find("\n", j)
                j = len(self.s) if newline < 0 else newline
            elif c == opener:
                depth += 1
                j += 1
            elif c == closer:
                depth -= 1
                j += 1
                if depth == 0:
                    self.depth -= 1
                    return j
            else:
                j += 1
            start_of_word = c in _SPACE + "\n;&|("
        raise _Unreadable(i)

    # --- tokens ---

    def _word(self) -> int:
        """Past the word that starts at `self.i`."""
        j = self.i
        while j < len(self.s):
            c = self.s[j]
            if c in _SPACE or c == "\n" or c in _OPS:
                return j
            if c == "\\":
                j += 2
            elif c == "'":
                j = self._closing(j + 1, "'")
            elif c == '"':
                j = self._double(j + 1)
            elif c == "`":
                j = self._backquote(j + 1)
            elif c == "$" and self.s.startswith(("$(", "${"), j):
                j = self._dollar(j)
            elif c == "$" and self.s.startswith("$'", j):
                j = self._closing(j + 2, "$'")
            else:
                j += 1
        return min(j, len(self.s))

    def _heredoc_bodies(self) -> None:
        """At a newline: read the pending here-documents' bodies, hiding inside them."""
        for delimiter, strip in self.heredocs:
            body = self.i
            j = body
            while True:
                if j >= len(self.s):
                    if self.partial:
                        self.i = j
                        return
                    raise _Unreadable(body)
                newline = self.s.find("\n", j)
                end = len(self.s) if newline < 0 else newline
                line = self.s[j:end]
                if (line.lstrip("\t") if strip else line) == delimiter:
                    break
                if newline < 0:
                    raise _Unreadable(body)
                j = newline + 1
            try:
                inner = _redact(self.s[body:j], self.depth + 1)
            except _Unreadable:  # hide the whole body, not just from the failing line
                raise _Unreadable(body) from None
            self.edits.append((body, j, inner))
            self.i = min(end + 1, len(self.s))
        self.heredocs = []

    def run(self) -> None:
        at_start, declaring, prev = True, False, ""
        redirect = False  # the next word is a redirection's target
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in _SPACE:
                self.i += 1
            elif c == "\\" and self.s.startswith("\\\n", self.i):
                self.i += 2
            elif c == "\n":
                self.i += 1
                at_start, declaring, prev, redirect = True, False, "", False
                if self.heredocs:
                    self._heredoc_bodies()
            elif c == "#":  # at a word's start: a comment (`#SBATCH` lines are kept)
                newline = self.s.find("\n", self.i)
                self.i = len(self.s) if newline < 0 else newline
            elif c in _OPS:
                j = self.i
                while j < len(self.s) and self.s[j] in _OPS:
                    j += 1
                op = self.s[self.i : j]
                self.i = j
                if op.endswith("<<") and not op.endswith("<<<"):
                    strip = self.s.startswith("-", self.i)
                    self.i += strip
                    self._heredoc_start(strip)
                elif any(ch in op for ch in ";|()") or op in ("&", "&&"):
                    at_start, declaring, prev, redirect = True, False, "", False
                else:  # `<`, `>`, `>>`, `>&`, `&>`, `<<<`: the next word is its target
                    redirect = True
            else:
                start = self.i
                self.i = self._word()
                if self.s.startswith("(", self.i) and _ASSIGN.fullmatch(self.s, start, self.i):
                    # an array value `NAME=(…)`: the `=` stands in for `$`, same nesting rules
                    self.i = self._dollar(self.i - 1)
                raw = self.s[start : self.i]
                if redirect:
                    redirect = False
                    continue
                self._assignment(start, raw, at_start, declaring, prev)
                if at_start and not _ASSIGN.match(raw):
                    at_start = raw in _RESERVED
                    declaring = raw in _DECLARE
                prev = raw

    def _heredoc_start(self, strip: bool) -> None:
        while self.s.startswith(tuple(_SPACE), self.i):
            self.i += 1
        start = self.i
        self.i = self._word()
        delimiter = re.sub(r"[\"'\\]", "", self.s[start : self.i])
        if not delimiter:
            raise _Unreadable(start)
        self.heredocs.append((delimiter, strip))

    def _assignment(self, start: int, raw: str, at_start: bool, declaring: bool, prev: str) -> None:
        if raw.startswith("--env="):
            self._hide(start + len("--env="), raw[len("--env=") :])
        elif at_start or declaring:
            self._hide(start, raw, quoted=not at_start)
        elif prev in _ENV_FLAGS:
            self._hide(start, raw)

    def _hide(self, start: int, raw: str, quoted: bool = True) -> None:
        """`NAME=value` → `NAME=«hidden»`; with `quoted`, also `"NAME=value"`."""
        lead = 1 if quoted and raw[:1] in ("'", '"') else 0
        found = _ASSIGN.match(raw, lead)
        if found is not None:
            self.edits.append((start, start + len(raw), raw[lead : found.end()] + HIDDEN))


def _apply(text: str, edits: list[tuple[int, int, str]]) -> str:
    out, at = [], 0
    for start, end, new in sorted(edits):
        out += [text[at:start], new]
        at = end
    out.append(text[at:])
    return "".join(out)


def _redact(text: str, depth: int = 0) -> str:
    if depth > MAX_NESTING:
        raise _Unreadable(0)
    lexer = _Lexer(text, depth=depth)
    lexer.run()
    if lexer.heredocs:  # a here-document whose body never started
        raise _Unreadable(lexer.i)
    return _apply(text, lexer.edits)


def redact_command_run(text: str) -> str:
    """`.command.run` with every assignment value hidden; from the first line the lexer cannot
    read, every line is `«hidden»`."""
    try:
        return _redact(text)
    except _Unreadable as exc:
        line_start = text.rfind("\n", 0, exc.pos) + 1
        lexer = _Lexer(text[:line_start], partial=True)
        try:
            lexer.run()
            head = _apply(text[:line_start], lexer.edits)
        except _Unreadable:  # a construct opened on an earlier line: hide it all
            head, line_start = "", 0
        rest = text[line_start:]
        lines = rest.count("\n") + (0 if rest.endswith("\n") or not rest else 1)
        return head + "".join(f"{HIDDEN}\n" for _ in range(lines))
