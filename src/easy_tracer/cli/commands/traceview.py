"""Traceview (method tracing) CLI command.

Usage:
    easytracer traceview -a com.example.app -d 5
    easytracer traceview -a com.example.app --sampling --interval 1000
"""

from __future__ import annotations

import time
import click

from easy_tracer.cli.output import OutputContext, output_error, output_success, output_progress


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
    from easy_tracer.framework.adb_helper import AdbHelper
    from easy_tracer.framework.traceview_adapter import TraceviewAdapter
    from easy_tracer.services.traceview_service import TraceviewService

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

    adapter = TraceviewAdapter(adb=adb)
    service = TraceviewService(adapter, output_dir=output_dir)

    mode = "sampling" if sampling else "method tracing"
    output_progress(f"Starting traceview ({duration}s, {mode})...", output_ctx)

    try:
        service.start_tracing(device_serial, app, sampling, interval)
        output_progress(f"Tracing started, waiting {duration}s...", output_ctx)

        time.sleep(duration)

        output_path = service.stop_tracing(
            device_serial=device_serial,
            package_name=app,
            output_dir=output,
        )

        if output_ctx.json_mode:
            from easy_tracer.cli.output import output_json
            output_json({"status": "success", "output": output_path})
        else:
            output_success(f"Trace saved: {output_path}", output_ctx)

    except Exception as e:
        output_error(str(e), output_ctx)
        ctx.exit(1)
