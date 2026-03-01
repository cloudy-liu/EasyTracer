"""Adapter for running systrace and querying Android device trace data."""

import contextlib
import io
import logging
import os
import re
import sys
import threading

from easy_tracer.framework import adb_helper
from easy_tracer.framework.external.systrace import systrace as systrace_module

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

    def __init__(
        self,
        adb: adb_helper.AdbHelper | None = None,
        adb_path: str = "adb",
    ) -> None:
        self.adb = adb if adb else adb_helper.AdbHelper(adb_path)

    def _import_and_run_systrace(self, args: list[str], *, tee: bool = False) -> str:
        """Run vendored systrace with captured stdio output.

        Injects adb_helper into the options namespace so agents can use unified ADB ops.
        """
        output_capture = io.StringIO()
        with _SYSTRACE_LOCK:
            try:
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
                    self._run_systrace_with_adb(["systrace.py"] + args)
            except SystemExit as exc:
                if exc.code not in (0, None):
                    raise RuntimeError(f"Systrace exited with code {exc.code}") from exc
        return output_capture.getvalue()

    def _run_systrace_with_adb(self, argv: list[str]) -> None:
        """Parse systrace args and inject adb_helper before running."""
        options, categories = systrace_module.parse_options(argv)
        options.adb_helper = self.adb
        agents = systrace_module.create_agents(options, categories)

        if not agents:
            sys.stderr.write('No systrace agent is available.\n')
            sys.exit(1)

        for a in agents:
            a.start()

        for a in agents:
            a.collect_result()
            if not a.expect_trace():
                return

        if options.list_categories:
            return

        systrace_module.write_trace_html(options.output_file, agents)

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
        out = self.adb.run_shell(device_serial, "cat", "/sys/kernel/tracing/available_events")
        return [line.strip() for line in out.splitlines() if line.strip()]

    def get_device_sdk_version(self, device_serial: str) -> int | None:
        if not device_serial:
            return None
        sdk = self.adb.get_sdk_version(device_serial)
        return sdk if sdk > 0 else None

    def get_device_model(self, device_serial: str) -> str:
        """Compatibility passthrough to centralized ADB helper."""
        return self.adb.get_device_model(device_serial)
