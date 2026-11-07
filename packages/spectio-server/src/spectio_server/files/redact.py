"""What a served file shows: `.command.run` with its values hidden, and text with no terminal
escape sequences (dev-env §15.3 req. 13, SEC-155, SEC-158; architecture §13.7).

`redact_command_run` reads the wrapper with a shell lexer, not a line pattern: POSIX quoting,
quoted values over several lines, `$'…'`, `$(…)`, `${…}`, backquotes and here-documents (whose
body is read as shell too: Nextflow writes the container environment as `export` lines inside
`cat << EOF`, `SimpleFileCopyStrategy.groovy:398-415`, v26.10.4). It hides the value of every
word that holds an assignment, wherever it stands, so that no command word before it (`export`,
`env`, `exec`, `sudo`, `nohup`, a redirection, a function's `{`) lets a value through
(SEC-P3T28-03, CR-P3T28-03):

- a word with an `=` outside `$(…)`, `${…}` and backquotes: `FOO=bar`, `"NAME=value"`,
  `"NAME"=value`, `NAME"=value"`, an array value `NAME=(…)`, a `beforeScript` assignment,
  `SINGULARITYENV_X=…`, `key=value` as an argument. It becomes `NAME=«hidden»` (the name with
  its quotes removed), or keeps its text before the `=` when that is not a name;
- an option with one dash and an `=`, the value attached: `-eTOKEN=v`, `-Dprop=v`;
- an option `--opt=NAME=value`: `--env=`, `--set-env=` (the value of `--opt=value` alone, with
  no name in it, is kept);
- in a scheduler directive line (`#SBATCH`, `#PBS`, `#$`, `#BSUB`), the value of each
  `NAME=value` item of `--export`, `-v` and `-env`; a value with a quote or a backslash in it
  hides the rest of the line (inbox #94 rule 8, option b; SEC-P3T31-02). Other comments are
  kept.

Each value becomes `«hidden»`. It fails closed: from the line where the lexer meets something it
cannot read (a quote or a here-document left open, or constructs nested more than `MAX_NESTING`
deep), every line is `«hidden»`. Values inside a command substitution or a parameter expansion
(`${X:+NAME=v}`) are not looked into; that the wrappers of every container engine fit these
forms is [to be validated] (req. 13).
"""

import re

HIDDEN = "«hidden»"
MAX_NESTING = 64  # `$(`, `${`, `"` and here-documents inside one another (SEC-P3T28-04)

# A name (with an optional array index) and `=` or `+=`, at the very start of a word.
_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\[[^\]\n]*\])?\+?=")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\[[^\]\n]*\])?\+?")
_UNQUOTE = re.compile(r"\$(?=')|[\"'\\]")
# A scheduler directive, and in it the options that carry `NAME=value` lists.
_DIRECTIVE = re.compile(r"#(SBATCH|PBS|\$|BSUB)\s")
# An option starts after any `\s`, as wide as `_DIRECTIVE`, while a value ends only at an ASCII
# space or tab (`_VALUE_END`): asymmetric on purpose, both fail closed (SEC-P3T31-10).
_EXPORT_OPTION = re.compile(r"(?<=\s)(--export(=|\s+)|-v\s*|-env\s*)")
_QUOTING = "'\"\\"
_VALUE_END = re.compile(r"[ \t'\"\\]")  # an ASCII space ends a directive value; a quoting hides it
_OPS = ";&|()<>"
_SPACE = " \t"

# CSI (ESC [ or the 8-bit CSI, … final), OSC (ESC ] or the 8-bit OSC, … BEL, ST or ESC \),
# other two-character escapes, the C0 and C1 controls left except tab and newline, and the bidi
# and other format controls, line and paragraph separators (SEC-P3T28-07 r1, SEC-P3T28-08 r3).
FORMAT_CHARS = r"\u061c\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb"
_ESCAPES = re.compile(
    r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]"
    r"|(?:\x1b\]|\x9d)[^\x07\x1b\x9c]*(?:\x07|\x1b\\|\x9c)?"
    r"|\x1b[@-_]?"
    r"|[\x00-\x08\x0b-\x1f\x7f-\x9f]"
    rf"|[{FORMAT_CHARS}]"
)


def strip_escapes(text: str) -> str:
    """`text` with terminal escape sequences, control and format characters removed (tab and
    newline kept)."""
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
        redirect = False  # the next word is a redirection's target
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in _SPACE:
                self.i += 1
            elif c == "\\" and self.s.startswith("\\\n", self.i):
                self.i += 2
            elif c == "\n":
                self.i += 1
                redirect = False
                if self.heredocs:
                    self._heredoc_bodies()
            elif c == "#":  # at a word's start: a comment, a directive's values hidden
                newline = self.s.find("\n", self.i)
                end = len(self.s) if newline < 0 else newline
                if self.i == 0 or self.s[self.i - 1] == "\n":
                    self._directive(self.i, end)
                self.i = end
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
                    redirect = False
                else:  # `<`, `>`, `>>`, `>&`, `&>`: the next word is its target; a `<<<`
                    redirect = not op.endswith("<<<")  # here-string is data (SEC-P3T31-08)
            else:
                start = self.i
                self.i = self._word()
                if self.s.startswith("(", self.i) and _ASSIGN.fullmatch(self.s, start, self.i):
                    # an array value `NAME=(…)`: the `=` stands in for `$`, same nesting rules
                    self.i = self._dollar(self.i - 1)
                if redirect:
                    redirect = False
                    continue
                self._assignment(start, self.i)

    def _heredoc_start(self, strip: bool) -> None:
        while self.s.startswith(tuple(_SPACE), self.i):
            self.i += 1
        start = self.i
        self.i = self._word()
        delimiter = re.sub(r"[\"'\\]", "", self.s[start : self.i])
        if not delimiter:
            raise _Unreadable(start)
        self.heredocs.append((delimiter, strip))

    def _eq(self, i: int, end: int) -> int | None:
        """The first `=` of the word `[i, end)` outside `$(…)`, `${…}` and backquotes (inside
        quotes or not), or None. The word was read whole already, so nothing here fails."""
        double = False
        while i < end:
            c = self.s[i]
            if self.s.startswith("\\=", i):  # `export T\=v` assigns (CR-P3T31-05)
                return i + 1
            if c == "\\":
                i += 2
            elif c == '"':
                double, i = not double, i + 1
            elif not double and (c == "'" or self.s.startswith("$'", i)):
                body = i + (2 if c == "$" else 1)
                close = self._closing(body, "$'" if c == "$" else "'")
                found = self.s.find("=", body, close - 1)
                if found >= 0:
                    return found
                i = close
            elif self.s.startswith(("$(", "${"), i):
                i = self._dollar(i)
            elif c == "`":
                i = self._backquote(i + 1)
            elif c == "=":
                return i
            else:
                i += 1
        return None

    def _assignment(self, start: int, end: int) -> None:
        """Hide the value of the word `[start, end)` when it holds one (the module's list)."""
        if self.s.startswith("--", start):
            option = self.s.find("=", start, end)
            if option < 0:
                return
            found = self._eq(option + 1, end)
            if found is not None and _NAME.fullmatch(self._unquoted(option + 1, found)):
                self.edits.append((found + 1, end, HIDDEN))
            return
        found = self._eq(start, end)
        if found is None or found == start:
            return
        if self.s.startswith("-", start):
            self.edits.append((found + 1, end, HIDDEN))
            return
        name = self._unquoted(start, found)
        if not _NAME.fullmatch(name):
            name = self.s[start:found]
        self.edits.append((start, end, f"{name}={HIDDEN}"))

    def _unquoted(self, start: int, end: int) -> str:
        return _UNQUOTE.sub("", self.s[start:end])

    def _directive(self, start: int, end: int) -> None:
        """In a scheduler directive line, hide what follows the first `=` of each comma item of
        `--export`, `-v`, `-env` (attached or not), whatever the item's name; a value ends at an
        ASCII space or tab, and one with a quote or a backslash in it is hidden to the end of
        the line, so no tail of a quoted value and no item after a closing quote is shown
        (fails closed: SEC-P3T31-02, SEC-P3T31-07)."""
        line = self.s[start:end]
        if not _DIRECTIVE.match(line):
            return
        spans = []  # in order, apart: each value starts after `done`
        done = 0  # the end of the last value read
        for option in _EXPORT_OPTION.finditer(line):
            at = option.end()
            if at <= done:  # its value ends at `done` too, and its spans are a subset of those
                continue  # read already: skipped, so a line is read in linear time (SEC-P3T31-11)
            stop = _VALUE_END.search(line, at)
            if stop is not None and stop[0] in _QUOTING:
                spans.append((at, len(line)))
                break
            done = len(line) if stop is None else stop.start()
            for item in line[at:done].split(","):  # no regex: no backtracking (CR-P3T31-10)
                name, eq, _ = item.partition("=")
                if eq:
                    spans.append((at + len(name) + 1, at + len(item)))
                at += len(item) + 1
        self.edits += [(start + lo, start + hi, HIDDEN) for lo, hi in spans]


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
