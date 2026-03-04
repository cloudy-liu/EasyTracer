"""Perfetto trace capture CLI command.

Usage:
    easytracer perfetto -d 10 -o trace.perfetto-trace
    easytracer perfetto --preset scheduling -d 5
    easytracer perfetto --config custom.pbtx
"""

from __future__ import annotations

import click

from easy_tracer.cli.output import OutputContext, output_error, output_success, output_progress


@click.command()
@click.option("-s", "--serial", default=None, help="Device serial (default: first device)")
@click.option("-d", "--duration", default=10, type=int, help="Capture duration in seconds")
@click.option("-b", "--buffer", default=32768, type=int, help="Buffer size in KB")
@click.option(
    "-c", "--categories",
    default=None,
    help="Comma-separated atrace categories (used when no preset/config)"
)
@click.option(
    "--preset",
    type=click.Choice(["standard", "graphics", "memory", "full"]),
    default=None,
    help="Use a built-in preset configuration"
)
@click.option("--config", "config_file", default=None, type=click.Path(exists=True), help="Custom config file path")
@click.option("-o", "--output", default=None, help="Output file path")
@click.pass_context
def perfetto(
    ctx: click.Context,
    serial: str | None,
    duration: int,
    buffer: int,
    categories: str | None,
    preset: str | None,
    config_file: str | None,
    output: str | None,
) -> None:
    """Capture Perfetto trace from an Android device."""
    from easy_tracer.framework.adb_helper import AdbHelper
    from easy_tracer.framework.perfetto_adapter import PerfettoAdapter
    from easy_tracer.services.perfetto_service import PerfettoService

    adb: AdbHelper = ctx.obj["adb"]
    output_ctx: OutputContext = ctx.obj["output"]
    output_dir: str = ctx.obj["output_dir"]

    if not adb.is_available():
        output_error("ADB not available.", output_ctx)
        ctx.exit(1)

    device_serial = serial
    if not device_serial:
        devices = adb.list_devices()
        if not devices:
            output_error("No devices connected.", output_ctx)
            ctx.exit(1)
        device_serial = devices[0].serial
        output_progress(f"Using device: {device_serial}", output_ctx)

    category_list = None
    if categories:
        category_list = [c.strip() for c in categories.split(",") if c.strip()]

    adapter = PerfettoAdapter(adb=adb)
    service = PerfettoService(adapter, output_dir=output_dir)

    mode = "preset" if preset else ("config" if config_file else "categories")
    output_progress(f"Starting Perfetto capture ({duration}s, mode={mode})...", output_ctx)

    try:
        output_path = service.record_trace(
            device_serial=device_serial,
            duration_seconds=duration,
            buffer_size_kb=buffer,
            categories=category_list,
            output_dir=output if output else None,
            preset=preset,
        )

        if output_ctx.json_mode:
            from easy_tracer.cli.output import output_json
            output_json({"status": "success", "output": output_path})
        else:
            output_success(f"Trace saved: {output_path}", output_ctx)

    except Exception as e:
        output_error(str(e), output_ctx)
        ctx.exit(1)
