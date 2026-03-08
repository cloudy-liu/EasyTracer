"""Combo capture CLI command - run multiple tracers simultaneously.

Usage:
    easytracer combo --systrace --perfetto -d 5
    easytracer combo --systrace --logcat -a com.example.app -d 10
"""

from __future__ import annotations

import os
import time

import click

from easy_tracer.cli.output import OutputContext, output_error, output_success, output_progress
from easy_tracer.models.requests import ComboRequest, PerfettoRequest, SimpleperfRequest, SystraceRequest, TraceviewStartRequest
from easy_tracer.runtime import resolve_target_device


@click.command()
@click.option("-s", "--serial", default=None, help="Device serial (default: first device)")
@click.option("-a", "--app", default=None, help="Target application package name")
@click.option("-d", "--duration", default=5, type=int, help="Capture duration in seconds")
@click.option("--systrace/--no-systrace", default=False, help="Enable systrace capture")
@click.option("--perfetto/--no-perfetto", default=False, help="Enable Perfetto capture")
@click.option("--simpleperf/--no-simpleperf", default=False, help="Enable simpleperf profiling")
@click.option("--traceview/--no-traceview", default=False, help="Enable method tracing")
@click.option("--logcat/--no-logcat", default=False, help="Capture logcat dump")
@click.option("--packages/--no-packages", default=False, help="Capture package list")
@click.option("--ps/--no-ps", default=False, help="Capture process list")
@click.option("--meminfo/--no-meminfo", default=False, help="Capture memory info")
@click.option("-o", "--output", default=None, help="Output directory")
@click.pass_context
def combo(
    ctx: click.Context,
    serial: str | None,
    app: str | None,
    duration: int,
    systrace: bool,
    perfetto: bool,
    simpleperf: bool,
    traceview: bool,
    logcat: bool,
    packages: bool,
    ps: bool,
    meminfo: bool,
    output: str | None,
) -> None:
    """Run multiple tracers simultaneously."""
    runtime = ctx.obj["runtime"]
    adb = runtime.adb
    output_ctx: OutputContext = ctx.obj["output"]
    output_dir: str = ctx.obj["output_dir"]

    if not adb.is_available():
        output_error("ADB not available.", output_ctx)
        ctx.exit(1)

    enabled = any([systrace, perfetto, simpleperf, traceview])
    auxiliary = any([logcat, packages, ps, meminfo])

    if not enabled and not auxiliary:
        output_error("At least one tracer or auxiliary dump must be enabled.", output_ctx)
        ctx.exit(1)

    try:
        device_serial = resolve_target_device(adb.list_devices(), serial)
    except RuntimeError as exc:
        output_error(str(exc), output_ctx)
        ctx.exit(1)

    if not serial:
        output_progress(f"Using device: {device_serial}", output_ctx)

    # Create output directory with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    combo_dir = output or os.path.join(output_dir, f"combo_{timestamp}")
    os.makedirs(combo_dir, exist_ok=True)

    auxiliary_options = {
        "logcat": logcat,
        "packages": packages,
        "ps": ps,
        "meminfo": meminfo,
    }

    request = ComboRequest(
        device_serial=device_serial,
        duration_seconds=duration,
        output_dir=combo_dir,
        systrace=(
            SystraceRequest(
                device_serial=device_serial,
                categories=["sched", "gfx", "view", "wm", "am"],
                duration_seconds=duration,
                app_name=app,
                output_dir=combo_dir,
            ) if systrace else None
        ),
        perfetto=(
            PerfettoRequest(
                device_serial=device_serial,
                duration_seconds=duration,
                output_dir=combo_dir,
            ) if perfetto else None
        ),
        simpleperf=(
            SimpleperfRequest(
                device_serial=device_serial,
                app_name=app,
                duration_seconds=duration,
                output_dir=combo_dir,
            ) if simpleperf else None
        ),
        traceview=(
            TraceviewStartRequest(
                device_serial=device_serial,
                package_name=app,
                output_dir=combo_dir,
            ) if traceview and app else None
        ),
        auxiliary_options=auxiliary_options,
    )

    enabled_list = [name for name, is_enabled in {
        "systrace": systrace,
        "perfetto": perfetto,
        "simpleperf": simpleperf,
        "traceview": traceview,
    }.items() if is_enabled]
    if enabled_list:
        output_progress(f"Starting combo capture ({duration}s)...", output_ctx)
        output_progress(f"Enabled tracers: {', '.join(enabled_list)}", output_ctx)
    elif auxiliary:
        output_progress("Collecting auxiliary dumps...", output_ctx)

    try:
        result = runtime.combo_service.run(request)
    except Exception as e:
        output_error(str(e), output_ctx)
        ctx.exit(1)

    # Output results
    if output_ctx.json_mode:
        from easy_tracer.cli.output import output_json
        output_json({
            "status": result.status,
            "output_dir": combo_dir,
            "files": result.files,
            "errors": result.errors or None,
        })
    else:
        output_success(f"Output directory: {combo_dir}", output_ctx)
        for name, path in result.files.items():
            click.echo(f"  {name}: {path}")
        if result.errors:
            for name, message in result.errors.items():
                output_error(f"{name}: {message}", output_ctx)

    if result.status == "error":
        ctx.exit(1)
