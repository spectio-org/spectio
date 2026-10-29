"""Snakemake logger plugin: one JSON line per log event, for Spectio."""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from snakemake_interface_logger_plugins.base import LogHandlerBase
from snakemake_interface_logger_plugins.settings import LogHandlerSettingsBase

# Attributes every LogRecord has; anything else on a record is an event field set by Snakemake.
_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


@dataclass
class LogHandlerSettings(LogHandlerSettingsBase):
    file: Optional[str] = field(
        default=None,
        metadata={"help": "File the JSON lines are appended to (default: spectio-events.jsonl)."},
    )


class LogHandler(LogHandlerBase):
    def __post_init__(self) -> None:
        path = (self.settings and self.settings.file) or "spectio-events.jsonl"
        # Snakemake reads baseFilename from file-writing handlers, as on logging.FileHandler.
        self.baseFilename = os.path.abspath(path)
        self._out = open(self.baseFilename, "a", encoding="utf-8")

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
