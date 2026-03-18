"""Utilities for subprocess calls to avoid console window on Windows GUI apps."""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any, Dict, Sequence

logger = logging.getLogger(__name__)

# On Windows, use CREATE_NO_WINDOW so child processes (adb, python) don't open a console.
# See: https://docs.python.org/3/library/subprocess.html#windows-constants
CREATE_NO_WINDOW = (
    getattr(subprocess, "CREATE_NO_WINDOW", 0x0800) if sys.platform == "win32" else 0
)


def subprocess_creationflags() -> int:
    """Returns creationflags for subprocess so child processes don't show a console on Windows."""
    return CREATE_NO_WINDOW


def subprocess_hidden_window_kwargs() -> Dict[str, Any]:
    """
    Returns kwargs for subprocess.run/Popen to hide console on Windows (e.g. adb.exe).
    Uses both CREATE_NO_WINDOW and STARTUPINFO with SW_HIDE for maximum effect.
    """
    if sys.platform != "win32":
        return {}
    kwargs: Dict[str, Any] = {
        "creationflags": (
            subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0x0800
        ),
    }
    # STARTUPINFO with SW_HIDE further suppresses console for console-subsystem executables like adb.exe
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
    startupinfo.wShowWindow = subprocess.SW_HIDE  # type: ignore[attr-defined]
    kwargs["startupinfo"] = startupinfo
    return kwargs


def check_output(
    cmd: Sequence[str],
    timeout: float | None = None,
) -> str:
    """Run a command and return combined stdout+stderr output.

    Raises RuntimeError with captured output on failure.
    """
    logger.debug("Executing: %s", " ".join(cmd))
    try:
        return subprocess.check_output(
            list(cmd),
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            **subprocess_hidden_window_kwargs(),
        ).strip()
    except FileNotFoundError as e:
        raise RuntimeError(f"Executable not found: {cmd[0]}") from e
    except subprocess.CalledProcessError as e:
        out = (e.output or "").strip()
        raise RuntimeError(out or f"Command failed with exit code {e.returncode}") from e
