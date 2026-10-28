"""Spike T2: minimal Snakemake logger plugin that writes every LogRecord as one JSON line.

Interface: snakemake-interface-logger-plugins 2.1.0 (the version locked in dev/snakemake.lock.txt):
LogHandlerBase in base.py (emit + five abstract properties), discovered by module prefix
`snakemake_logger_plugin_` (common.py, registry/__init__.py), so putting this directory on
PYTHONPATH and passing `--logger spectio` is enough; no install.
Output file: $SPECTIO_EVENTS (default spectio-events.jsonl in the working directory).
"""
import json
import logging
import os
import time

from snakemake_interface_logger_plugins.base import LogHandlerBase

# Attributes every LogRecord has; anything else was passed by Snakemake as `extra=`.
_STD = set(vars(logging.LogRecord("x", 0, "x", 0, "", None, None))) | {"message", "asctime"}


def _plain(o):
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if hasattr(o, "_names") and callable(getattr(o, "items", None)):  # snakemake.io.Namedlist (Resources)
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set, frozenset)):
        return [_plain(v) for v in o]
    return {"__type__": type(o).__name__, "repr": str(o)}


class LogHandler(LogHandlerBase):
    def __post_init__(self) -> None:
        self._seq = 0
        # Snakemake 9.27.1 reads `baseFilename` from every handler whose writes_to_file is True
        # (snakemake/logging.py:661-663); the interface (base.py) does not declare it.
        self.baseFilename = os.path.abspath(os.environ.get("SPECTIO_EVENTS", "spectio-events.jsonl"))
        self._out = open(self.baseFilename, "a", buffering=1)

    def emit(self, record: logging.LogRecord) -> None:
        self._seq += 1
        extra = {k: _plain(v) for k, v in vars(record).items() if k not in _STD}
        line = {
            "seq": self._seq,
            "t": time.time(),
            "level": record.levelname,
            "event": str(extra.pop("event", None)),
            "msg": record.getMessage() if record.msg is not None else None,
            "extra": extra,
        }
        self._out.write(json.dumps(line, sort_keys=True) + "\n")

    def close(self) -> None:
        self._out.close()
        super().close()

    @property
    def writes_to_stream(self) -> bool:
        return False

    @property
    def writes_to_file(self) -> bool:
        return True

    @property
    def has_filter(self) -> bool:
        return True  # see everything, including what --quiet would drop (synthesis.md §2bis pitfall)

    @property
    def has_formatter(self) -> bool:
        return True

    @property
    def needs_rulegraph(self) -> bool:
        return True  # ask for the RULEGRAPH event too, to record it
