"""Simpleperf CPU profiling CLI command.

Usage:
    easytracer simpleperf -a com.example.app -d 10
    easytracer simpleperf -a com.example.app --cold-start -d 10
    easytracer simpleperf --system -d 5
"""

from __future__ import annotations

import click

from easy_tracer.cli.output import OutputContext, output_error, output_success, output_progress
from easy_tracer.models.requests import SimpleperfRequest
from easy_tracer.runtime import resolve_target_device


@click.command()
@click.option("-s", "--serial", default=None, help="Device serial (default: first device)")
@click.option("-a", "--app", default=None, help="Target application package name")
@click.option("--system", is_flag=True, help="System-wide profiling (no app required)")
@click.option("-d", "--duration", default=10, type=int, help="Profiling duration in seconds")
@click.option("-f", "--frequency", default=4000, type=int, help="Sampling frequency in Hz")
@click.option("--cold-start", is_flag=True, help="Enable cold start profiling")
@click.option("--no-report", is_flag=True, help="Skip HTML report generation")
@click.option("-o", "--output", default=None, help="Output directory")
@click.pass_context
def simpleperf(
    ctx: click.Context,
    serial: str | None,
    app: str | None,
    system: bool,
    duration: int,
    frequency: int,
    cold_start: bool,
    no_report: bool,
    output: str | None,
) -> None:
    """CPU profiling with simpleperf."""
    runtime = ctx.obj["runtime"]
    adb = runtime.adb
    output_ctx: OutputContext = ctx.obj["output"]

    if not adb.is_available():
        output_error("ADB not available.", output_ctx)
        ctx.exit(1)

    if not app and not system:
        output_error("Either --app or --system is required.", output_ctx)
        ctx.exit(1)

    try:
        device_serial = resolve_target_device(adb.list_devices(), serial)
    except RuntimeError as exc:
        output_error(str(exc), output_ctx)
        ctx.exit(1)

    if not serial:
        output_progress(f"Using device: {device_serial}", output_ctx)

    mode = "system-wide" if system else f"app ({app})"
    output_progress(f"Starting simpleperf profiling ({duration}s, {mode})...", output_ctx)

    try:
        result = runtime.simpleperf_service.run(
            SimpleperfRequest(
                device_serial=device_serial,
                app_name=None if system else app,
                duration_seconds=duration,
                frequency=frequency,
                output_dir=output,
                cold_start=cold_start,
                generate_report=not no_report,
            )
        )

        if output_ctx.json_mode:
            from easy_tracer.cli.output import output_json
            output_json({"status": "success", "output": result.output_path})
        else:
            output_success(f"Profile saved: {result.output_path}", output_ctx)

    except Exception as e:
        output_error(str(e), output_ctx)
        ctx.exit(1)
