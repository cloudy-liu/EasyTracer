"""Traceview (method tracing) CLI command.

Usage:
    easytracer traceview -a com.example.app -d 5
    easytracer traceview -a com.example.app --sampling --interval 1000
"""

from __future__ import annotations

import time
import click

from easy_tracer.cli.output import OutputContext, output_error, output_success, output_progress
from easy_tracer.models.requests import TraceviewStartRequest
from easy_tracer.runtime import resolve_target_device


@click.command()
@click.option("-s", "--serial", default=None, help="Device serial (default: first device)")
@click.option("-a", "--app", required=True, help="Target application package name")
@click.option("-d", "--duration", default=5, type=int, help="Tracing duration in seconds")
@click.option("--sampling", is_flag=True, help="Use sampling mode instead of method tracing")
@click.option("--interval", default=1000, type=int, help="Sampling interval in microseconds")
@click.option("-o", "--output", default=None, help="Output directory")
@click.pass_context
def traceview(
    ctx: click.Context,
    serial: str | None,
    app: str,
    duration: int,
    sampling: bool,
    interval: int,
    output: str | None,
) -> None:
    """Method tracing with traceview."""
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

    mode = "sampling" if sampling else "method tracing"
    output_progress(f"Starting traceview ({duration}s, {mode})...", output_ctx)

    try:
        session = runtime.traceview_service.start_session(
            TraceviewStartRequest(
                device_serial=device_serial,
                package_name=app,
                sampling=sampling,
                interval=interval,
                output_dir=output,
            )
        )
        output_progress(f"Tracing started, waiting {duration}s...", output_ctx)

        time.sleep(duration)

        result = session.stop(output_dir=output)

        if output_ctx.json_mode:
            from easy_tracer.cli.output import output_json
            output_json({"status": "success", "output": result.output_path})
        else:
            output_success(f"Trace saved: {result.output_path}", output_ctx)

    except Exception as e:
        output_error(str(e), output_ctx)
        ctx.exit(1)
