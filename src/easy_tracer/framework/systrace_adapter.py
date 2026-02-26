"""Adapter for running systrace and querying Android device trace data."""

import contextlib
import io
import logging
import os
import re
import sys
import threading

from easy_tracer.framework import subprocess_utils
from easy_tracer.framework import adb_helper
from easy_tracer.framework.external.systrace import systrace as systrace_module
from easy_tracer.framework.external.systrace import util as systrace_util

logger = logging.getLogger(__name__)

_SYSTRACE_LOCK = threading.Lock()
_DEVNULL: io.TextIOWrapper | None = None


def _ensure_stdio() -> None:
    """Guard against None stdout/stderr in frozen GUI builds (PyInstaller)."""
    global _DEVNULL
    if sys.stdout is None or sys.stderr is None:
        if _DEVNULL is None or _DEVNULL.closed:
            _DEVNULL = open(os.devnull, "w", encoding="utf-8", errors="ignore")
        if sys.stdout is None:
            sys.stdout = _DEVNULL
        if sys.stderr is None:
            sys.stderr = _DEVNULL


class _TeeStream:
    """Write-through stream that captures text AND forwards to the original stream."""

    def __init__(self, original: object, buffer: io.StringIO) -> None:
        self._original = original
        self._buffer = buffer
        self.encoding = getattr(original, "encoding", "utf-8")

    def write(self, data: str) -> int:
        self._buffer.write(data)
        if self._original is not None:
            try:
                self._original.write(data)
                self._original.flush()
            except Exception:
                pass
        return len(data)

    def flush(self) -> None:
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return False


class SystraceAdapter:
    """Adapter for running systrace and querying Android device trace metadata."""

    def __init__(self, adb_path: str = "adb") -> None:
        self.adb_path = adb_path

    def _set_adb(self) -> None:
        systrace_util.ADB_EXECUTABLE = self.adb_path or "adb"

    def _import_and_run_systrace(self, args: list[str], *, tee: bool = False) -> str:
        """Run vendored systrace with captured stdio output.

        When *tee* is True the captured text is also forwarded to the
        original stdout/stderr so that it appears in the UI log panel
        in real-time (via the logging-bridge _QtTextStream).
        """
        output_capture = io.StringIO()
        with _SYSTRACE_LOCK:
            prev_adb = systrace_util.ADB_EXECUTABLE
            try:
                self._set_adb()
                _ensure_stdio()
                if tee:
                    tee_out = _TeeStream(sys.stdout, output_capture)
                    tee_err = _TeeStream(sys.stderr, output_capture)
                    ctx = contextlib.redirect_stdout(tee_out)
                    ctx2 = contextlib.redirect_stderr(tee_err)
                else:
                    ctx = contextlib.redirect_stdout(output_capture)
                    ctx2 = contextlib.redirect_stderr(output_capture)
                with ctx, ctx2:
                    systrace_module.main_impl(["systrace.py"] + args)
            except SystemExit as exc:
                if exc.code not in (0, None):
                    raise RuntimeError(f"Systrace exited with code {exc.code}") from exc
            finally:
                systrace_util.ADB_EXECUTABLE = prev_adb
        return output_capture.getvalue()

    def run_systrace(
        self,
        output_file: str,
        time_seconds: int,
        device_serial: str,
        categories: list[str],
        buffer_size_kb: int | None = None,
        app_name: str | None = None,
    ) -> str:
        """Run systrace and write output to the specified file."""
        args = ["-o", output_file, "-t", str(time_seconds), "-e", device_serial]
        if buffer_size_kb:
            args.extend(["-b", str(buffer_size_kb)])
        if app_name:
            args.extend(["-a", app_name])
        args.extend(categories)

        logger.info("Running systrace with args: %s", " ".join(args))
        return self._import_and_run_systrace(args, tee=True)

    def get_categories(self, device_serial: str) -> list[str]:
        """Query available atrace categories."""
        out = self._import_and_run_systrace(["-l", "-e", device_serial])

        categories: list[str] = []
        seen: set[str] = set()
        cat_re = re.compile(r"^\s*([A-Za-z0-9_]+)\s*-\s+.+$")
        for line in out.splitlines():
            m = cat_re.match(line)
            if m and (cat := m.group(1)) not in seen:
                seen.add(cat)
                categories.append(cat)
        return categories

    def get_ftrace_events(self, device_serial: str) -> list[str]:
        """Query available ftrace events from the device."""
        cmd = [self.adb_path, "-s", device_serial, "shell",
               "cat", "/sys/kernel/tracing/available_events"]
        out = subprocess_utils.check_output(cmd)
        return [line.strip() for line in out.splitlines() if line.strip()]

    def get_device_sdk_version(self, device_serial: str) -> int | None:
        if not device_serial:
            return None
        try:
            self._set_adb()
            sdk = systrace_util.get_device_sdk_version(device_serial)
        except (SystemExit, Exception):
            return None
        return sdk if isinstance(sdk, int) and sdk > 0 else None

    def get_device_model(self, device_serial: str) -> str:
        """Compatibility passthrough to centralized ADB helper."""
        return adb_helper.AdbHelper(self.adb_path).get_device_model(device_serial)
