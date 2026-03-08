"""Systrace capture CLI command.

Usage:
    easytracer systrace -c gfx,sched -d 5 -o trace.html
    easytracer systrace --categories gfx,sched,view --duration 10
"""

from __future__ import annotations

import click

from easy_tracer.cli.output import OutputContext, output_error, output_success, output_progress
from easy_tracer.models.requests import SystraceRequest
from easy_tracer.runtime import resolve_target_device


@click.command()
@click.option("-s", "--serial", default=None, help="Device serial (default: first device)")
@click.option(
    "-c", "--categories",
    required=True,
    help="Comma-separated trace categories (e.g., gfx,sched,view,wm)"
)
@click.option("-d", "--duration", default=5, type=int, help="Capture duration in seconds")
@click.option("-b", "--buffer", default=16384, type=int, help="Buffer size in KB")
@click.option("-a", "--app", default=None, help="Target application package name")
@click.option("-o", "--output", default=None, help="Output file path")
@click.pass_context
def systrace(
    ctx: click.Context,
    serial: str | None,
    categories: str,
    duration: int,
    buffer: int,
    app: str | None,
    output: str | None,
) -> None:
    """Capture systrace from an Android device."""
    runtime = ctx.obj["runtime"]
    adb = runtime.adb
    output_ctx: OutputContext = ctx.obj["output"]

    if not adb.is_available():
        output_error("ADB not available.", output_ctx)
        ctx.exit(1)

    try:
        device_serial = resolve_target_device(adb.list_devices(), serial)
    except RuntimeError as exc:
        output_error(str(exc), output_ctx)
        ctx.exit(1)

    if not serial:
        output_progress(f"Using device: {device_serial}", output_ctx)

    category_list = [c.strip() for c in categories.split(",") if c.strip()]
    if not category_list:
        output_error("No categories specified.", output_ctx)
        ctx.exit(1)

    output_progress(f"Starting systrace capture ({duration}s)...", output_ctx)
    output_progress(f"Categories: {', '.join(category_list)}", output_ctx)

    try:
        result = runtime.capture_service.run(
            SystraceRequest(
            device_serial=device_serial,
            categories=category_list,
            duration_seconds=duration,
            buffer_size_kb=buffer,
            app_name=app,
            output_dir=output if output else None,
            )
        )

        if output_ctx.json_mode:
            from easy_tracer.cli.output import output_json
            output_json({"status": "success", "output": result.output_path})
        else:
            output_success(f"Trace saved: {result.output_path}", output_ctx)

    except Exception as e:
        output_error(str(e), output_ctx)
        ctx.exit(1)
