from __future__ import annotations

import logging
import sys
from typing import Callable

from PySide6 import QtCore


class _QtLogEmitter(QtCore.QObject):
    message = QtCore.Signal(str)


class QtLogHandler(logging.Handler):
    """Logging handler that forwards messages to a Qt signal (thread-safe)."""

    def __init__(self, on_message: Callable[[str], None]):
        super().__init__()
        self._emitter = _QtLogEmitter()
        # Queued connection ensures cross-thread safety.
        self._emitter.message.connect(on_message, QtCore.Qt.QueuedConnection)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            # Never crash logging.
            msg = record.getMessage()
        self._emitter.message.emit(msg)


class _QtTextStream:
    """File-like stream that forwards text to a Qt callback."""

    def __init__(self, on_message: Callable[[str], None], passthrough: object | None):
        self._emitter = _QtLogEmitter()
        self._emitter.message.connect(on_message, QtCore.Qt.QueuedConnection)
        self._passthrough = passthrough
        self.encoding = getattr(passthrough, "encoding", "utf-8")

    def write(self, data: object) -> int:
        text = str(data)
        if not text:
            return 0

        if self._passthrough is not None:
            try:
                self._passthrough.write(text)
                self._passthrough.flush()
            except Exception:
                pass

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        self._emitter.message.emit(normalized)
        return len(text)

    def flush(self) -> None:
        if self._passthrough is not None:
            try:
                self._passthrough.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return False


def install_qt_logging(
    on_message: Callable[[str], None],
    level: int = logging.INFO,
    fmt: str = "%(asctime)s %(levelname)s %(name)s: %(message)s",
) -> QtLogHandler:
    """Install a Qt log handler on the root logger (idempotent-ish).

    Returns the handler so the caller can keep it alive.
    """
    handler = QtLogHandler(on_message)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)

    # Avoid duplicated default handlers if any were previously configured.
    # (We keep existing handlers; this just prevents basicConfig re-adding.)
    return handler


def install_qt_stdio(
    on_message: Callable[[str], None],
) -> tuple[_QtTextStream, _QtTextStream]:
    """Redirect global stdout/stderr to the Qt log area."""
    stdout_stream = _QtTextStream(on_message, sys.stdout)
    stderr_stream = _QtTextStream(on_message, sys.stderr)
    sys.stdout = stdout_stream
    sys.stderr = stderr_stream
    return stdout_stream, stderr_stream

