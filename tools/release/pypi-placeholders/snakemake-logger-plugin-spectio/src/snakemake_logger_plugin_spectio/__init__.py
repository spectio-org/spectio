"""Snakemake logger plugin: one JSON line per log event, for Spectio."""

import json
import logging
import os
import stat
from dataclasses import dataclass, field

from snakemake_interface_logger_plugins.base import LogHandlerBase
from snakemake_interface_logger_plugins.settings import LogHandlerSettingsBase

# Attributes every LogRecord has; anything else on a record is an event field set by Snakemake.
_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


@dataclass
class LogHandlerSettings(LogHandlerSettingsBase):
    file: str = field(
        default="spectio-events.jsonl",
        metadata={"help": "File the JSON lines are appended to."},
    )


class LogHandler(LogHandlerBase):
    def __post_init__(self) -> None:
        # The CLI always passes settings; the interface's type allows None (an API caller).
        settings = self.settings or LogHandlerSettings()
        # Snakemake reads baseFilename from file-writing handlers, as on logging.FileHandler.
        self.baseFilename = os.path.abspath(settings.file)
        # O_NOFOLLOW: a symlink planted at the path is refused, never followed.
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_nlink != 1:
            os.close(fd)
            raise PermissionError(f"refusing {self.baseFilename}: not a regular file of ours with one link")
        os.fchmod(fd, 0o600)
        self._out = os.fdopen(fd, "a", encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = {
                "time": record.created,
                "level": record.levelname,
                "event": str(getattr(record, "event", "")) or None,
                "message": record.getMessage(),
            }
            for key, value in vars(record).items():
                if key not in _STANDARD and key not in line:
                    line[key] = value
            self._out.write(json.dumps(line, default=str) + "\n")
            self._out.flush()
        except Exception:
            self.handleError(record)

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
        return False

    @property
    def has_formatter(self) -> bool:
        return False

    @property
    def needs_rulegraph(self) -> bool:
        return False
