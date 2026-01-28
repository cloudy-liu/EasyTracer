from __future__ import annotations

from typing import Any, Callable
from PySide6 import QtCore


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(str)
    result = QtCore.Signal(object)


class Worker(QtCore.QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as exc:  # pragma: no cover - pass-through errors
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


def run_in_thread(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Worker:
    worker = Worker(fn, *args, **kwargs)
    QtCore.QThreadPool.globalInstance().start(worker)
    return worker
