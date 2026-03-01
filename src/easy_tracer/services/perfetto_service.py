import os
import time
from typing import List, Optional
from easy_tracer.framework import perfetto_adapter
from easy_tracer.framework.perfetto_config_builder import (
    PerfettoConfig, build_config, config_from_preset
)

class PerfettoService:
    def __init__(
        self,
        perfetto_adapter: perfetto_adapter.PerfettoAdapter,
        output_dir: str = "output",
    ):
        self.perfetto_adapter = perfetto_adapter
        self.output_dir = output_dir

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def record_trace(
        self,
        device_serial: str,
        duration_seconds: int = 10,
        buffer_size_kb: int = 32768,
        categories: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
        preset: Optional[str] = None,
        config: Optional[PerfettoConfig] = None,
    ) -> str:
        """
        Records a Perfetto trace.

        Args:
            device_serial: Target device
            duration_seconds: Trace duration
            buffer_size_kb: Buffer size (used only if no preset/config)
            categories: Atrace categories (used only if no preset/config)
            output_dir: Output directory
            preset: Named preset ("standard", "graphics", "memory", "full")
            config: Custom PerfettoConfig object

        Returns:
            Path to the output trace file
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"perfetto_{timestamp}.perfetto-trace"
        base_dir = output_dir or self.output_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(base_dir, filename)
        output_path = os.path.abspath(output_path)

        config_text = None

        if config:
            # Use provided config
            config_text = build_config(config)
        elif preset:
            # Use preset
            cfg = config_from_preset(preset, duration_ms=duration_seconds * 1000)
            config_text = build_config(cfg)
        # else: use simple command-line method (categories + buffer)

        self.perfetto_adapter.record_trace(
            device_serial=device_serial,
            output_path=output_path,
            duration_seconds=duration_seconds,
            buffer_size_kb=buffer_size_kb,
            categories=categories,
            config_text=config_text,
        )

        return output_path
