"""Simpleperf CPU profiling CLI command.

Usage:
    easytracer simpleperf -a com.example.app -d 10
    easytracer simpleperf -a com.example.app --cold-start -d 10
    easytracer simpleperf --system -d 5
"""

from __future__ import annotations

import click

from easy_tracer.cli.output import OutputContext, output_error, output_success, output_progress


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
    from easy_tracer.framework.adb_helper import AdbHelper
    from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter
    from easy_tracer.services.simpleperf_service import SimpleperfService

    adb: AdbHelper = ctx.obj["adb"]
    output_ctx: OutputContext = ctx.obj["output"]
    output_dir: str = ctx.obj["output_dir"]

    if not adb.is_available():
        output_error("ADB not available.", output_ctx)
        ctx.exit(1)

    if not app and not system:
        output_error("Either --app or --system is required.", output_ctx)
        ctx.exit(1)

    device_serial = serial
    if not device_serial:
        devices = adb.list_devices()
        if not devices:
            output_error("No devices connected.", output_ctx)
            ctx.exit(1)
        device_serial = devices[0].serial
        output_progress(f"Using device: {device_serial}", output_ctx)

    adapter = SimpleperfAdapter(adb=adb)
    service = SimpleperfService(adapter, output_dir=output_dir)

    mode = "system-wide" if system else f"app ({app})"
    output_progress(f"Starting simpleperf profiling ({duration}s, {mode})...", output_ctx)

    try:
        if system:
            output_path = service.profile_system(
                device_serial=device_serial,
                duration_seconds=duration,
                frequency=frequency,
                generate_report=not no_report,
                output_dir=output,
            )
        else:
            output_path = service.profile_app(
                device_serial=device_serial,
                app_name=app,
                duration_seconds=duration,
                frequency=frequency,
                generate_report=not no_report,
                output_dir=output,
                cold_start=cold_start,
            )

        if output_ctx.json_mode:
            from easy_tracer.cli.output import output_json
            output_json({"status": "success", "output": output_path})
        else:
            output_success(f"Profile saved: {output_path}", output_ctx)

    except Exception as e:
        output_error(str(e), output_ctx)
        ctx.exit(1)
