"""Backward-compatible ADB adapter alias.

This module keeps legacy imports working after renaming the implementation
to `adb_helper.AdbHelper`.
"""

from easy_tracer.framework import adb_helper


class AdbAdapter(adb_helper.AdbHelper):
    """Compatibility alias for older code and tests."""

