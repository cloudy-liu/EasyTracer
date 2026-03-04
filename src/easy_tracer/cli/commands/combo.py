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
    from easy_tracer.framework.adb_helper import AdbHelper
    from easy_tracer.framework.systrace_adapter import SystraceAdapter
    from easy_tracer.framework.perfetto_adapter import PerfettoAdapter
    from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter
    from easy_tracer.framework.traceview_adapter import TraceviewAdapter
    from easy_tracer.services.capture_service import CaptureService
    from easy_tracer.services.perfetto_service import PerfettoService
    from easy_tracer.services.simpleperf_service import SimpleperfService
    from easy_tracer.services.traceview_service import TraceviewService
    from easy_tracer.services.combo_service import ComboService

    adb: AdbHelper = ctx.obj["adb"]
    output_ctx: OutputContext = ctx.obj["output"]
    output_dir: str = output or ctx.obj["output_dir"]

    if not adb.is_available():
        output_error("ADB not available.", output_ctx)
        ctx.exit(1)

    enabled = any([systrace, perfetto, simpleperf, traceview])
    auxiliary = any([logcat, packages, ps, meminfo])

    if not enabled and not auxiliary:
        output_error("At least one tracer or auxiliary dump must be enabled.", output_ctx)
        ctx.exit(1)

    device_serial = serial
    if not device_serial:
        devices = adb.list_devices()
        if not devices:
            output_error("No devices connected.", output_ctx)
            ctx.exit(1)
        device_serial = devices[0].serial
        output_progress(f"Using device: {device_serial}", output_ctx)

    # Create output directory with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    combo_dir = os.path.join(output_dir, f"combo_{timestamp}")
    os.makedirs(combo_dir, exist_ok=True)

    results: dict[str, str] = {}
    errors: list[str] = []

    # Run tracers via ComboService
    if enabled:
        systrace_adapter = SystraceAdapter(adb=adb)
        perfetto_adapter = PerfettoAdapter(adb=adb)
        simpleperf_adapter = SimpleperfAdapter(adb=adb)
        traceview_adapter = TraceviewAdapter(adb=adb)

        capture_service = CaptureService(systrace_adapter, output_dir=combo_dir, adb_helper=adb)
        perfetto_service = PerfettoService(perfetto_adapter, output_dir=combo_dir)
        simpleperf_service = SimpleperfService(simpleperf_adapter, output_dir=combo_dir)
        traceview_service = TraceviewService(traceview_adapter, output_dir=combo_dir)

        combo_service = ComboService(
            systrace_service=capture_service,
            simpleperf_service=simpleperf_service,
            perfetto_service=perfetto_service,
            traceview_service=traceview_service,
            output_dir=combo_dir,
        )

        enabled_tools = {
            "systrace": systrace,
            "perfetto": perfetto,
            "simpleperf": simpleperf,
            "traceview": traceview,
        }

        configs = {
            "package_name": app,
            "systrace_categories": ["sched", "gfx", "view", "wm", "am"],
        }

        output_progress(f"Starting combo capture ({duration}s)...", output_ctx)
        enabled_list = [k for k, v in enabled_tools.items() if v]
        output_progress(f"Enabled tracers: {', '.join(enabled_list)}", output_ctx)

        try:
            tracer_results = combo_service.start_combo_capture(
                device_serial=device_serial,
                duration=duration,
                enabled_tools=enabled_tools,
                configs=configs,
            )
            results.update(tracer_results)
        except RuntimeError as e:
            errors.append(str(e))

    # Run auxiliary dumps
    if auxiliary:
        output_progress("Collecting auxiliary dumps...", output_ctx)
        output_prefix = os.path.join(combo_dir, "aux")

        dump_options = {
            "logcat": logcat,
            "packages": packages,
            "ps": ps,
            "meminfo": meminfo,
        }

        systrace_adapter = SystraceAdapter(adb=adb)
        capture_service = CaptureService(systrace_adapter, output_dir=combo_dir, adb_helper=adb)

        try:
            aux_results = capture_service.dump_auxiliary_logs(
                device_serial=device_serial,
                output_prefix=output_prefix,
                options=dump_options,
            )
            results.update(aux_results)
        except Exception as e:
            errors.append(f"Auxiliary dump error: {e}")

    # Output results
    if output_ctx.json_mode:
        from easy_tracer.cli.output import output_json
        output_json({
            "status": "success" if not errors else "partial",
            "output_dir": combo_dir,
            "files": results,
            "errors": errors if errors else None,
        })
    else:
        output_success(f"Output directory: {combo_dir}", output_ctx)
        for name, path in results.items():
            click.echo(f"  {name}: {path}")
        if errors:
            for err in errors:
                output_error(err, output_ctx)
