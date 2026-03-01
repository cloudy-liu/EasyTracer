"""Perfetto trace recording adapter.

Delegates all ADB operations to adb_helper for unified resource management.
"""

from __future__ import annotations

import logging
import time

from easy_tracer.framework import adb_helper

logger = logging.getLogger(__name__)


class PerfettoAdapter:
    def __init__(
        self,
        adb: adb_helper.AdbHelper | None = None,
        adb_path: str = "adb",
    ):
        self.adb = adb if adb else adb_helper.AdbHelper(adb_path)

    def record_trace(
        self,
        device_serial: str,
        output_path: str,
        duration_seconds: int = 10,
        categories: list[str] | None = None,
        buffer_size_kb: int = 32768,
        config_text: str | None = None,
    ) -> str:
        """Records a Perfetto trace on the device and pulls it to the local machine.

        If config_text is provided, it will be used as the Perfetto configuration.
        Otherwise, a simple command-line based trace will be recorded.

        Returns the local path to the trace file.
        """
        device_output_path = f"/data/misc/perfetto-traces/trace_{int(time.time())}.perfetto-trace"

        if config_text:
            self._record_with_config(device_serial, device_output_path, config_text)
        else:
            self._record_simple(device_serial, device_output_path, duration_seconds, categories, buffer_size_kb)

        logger.info("Pulling trace from device...")
        self.adb.pull_file(device_serial, device_output_path, output_path)
        self.adb.remove_file(device_serial, device_output_path)

        return output_path

    def _record_with_config(self, device_serial: str, device_output_path: str, config_text: str) -> None:
        """Record trace using config file method."""
        device_config_path = "/data/local/tmp/perfetto_cfg.pbtx"

        logger.info("Pushing Perfetto config to device...")
        self.adb.run_shell(
            device_serial,
            f"cat > {device_config_path} << 'EOFCONFIG'\n{config_text}\nEOFCONFIG"
        )

        logger.info("Starting Perfetto trace...")
        self.adb.run_shell(
            device_serial,
            f"cat {device_config_path} | perfetto --txt -c - -o {device_output_path}"
        )

        self.adb.remove_file(device_serial, device_config_path)

    def _record_simple(
        self,
        device_serial: str,
        device_output_path: str,
        duration_seconds: int,
        categories: list[str] | None,
        buffer_size_kb: int,
    ) -> None:
        """Record trace using simple command-line method."""
        if categories is None:
            categories = [
                "sched", "gfx", "view", "wm", "am", "hal", "res",
                "dalvik", "freq", "idle", "binder_driver", "binder_lock",
            ]

        cmd_parts = [
            "perfetto",
            "-o", device_output_path,
            "-t", f"{duration_seconds}s",
            "-b", f"{buffer_size_kb}kb",
        ] + categories

        logger.info(f"Starting Perfetto trace ({duration_seconds}s)...")
        self.adb.run_shell(device_serial, *cmd_parts, timeout=duration_seconds + 30)
