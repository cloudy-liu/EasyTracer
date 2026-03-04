"""EasyTracer CLI - Android Performance Tracing Toolkit.

Usage:
    easytracer --help
    easytracer devices list
    easytracer systrace -c gfx,sched -d 5
    easytracer perfetto --preset standard -d 10
    easytracer simpleperf -a com.example.app -d 10
    easytracer traceview -a com.example.app -d 5
    easytracer combo --systrace --perfetto -d 5
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import click

from easy_tracer.cli.output import OutputContext


# =============================================================================
# VERSION
# =============================================================================

def get_version() -> str:
    """Get version from package metadata or fallback."""
    try:
        from importlib.metadata import version
        return version("easy_tracer")
    except Exception:
        return "0.1.0"


# =============================================================================
# MAIN CLI GROUP
# =============================================================================

@click.group()
@click.option(
    "--adb-path",
    envvar="EASYTRACER_ADB",
    default=None,
    help="Path to adb executable"
)
@click.option(
    "--output-dir", "-O",
    envvar="EASYTRACER_OUTPUT",
    default=None,
    help="Default output directory"
)
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format")
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress messages")
@click.version_option(version=get_version(), prog_name="easytracer")
@click.pass_context
def cli(
    ctx: click.Context,
    adb_path: str | None,
    output_dir: str | None,
    json_mode: bool,
    quiet: bool,
) -> None:
    """EasyTracer - Android Performance Tracing Toolkit.

    A CLI for capturing systrace, Perfetto, simpleperf, and traceview traces
    from Android devices.
    """
    from easy_tracer.framework.adb_helper import AdbHelper

    ctx.ensure_object(dict)

    # Resolve ADB path
    resolved_adb = adb_path or _resolve_default_adb()
    ctx.obj["adb"] = AdbHelper(adb_path=resolved_adb)

    # Resolve output directory
    ctx.obj["output_dir"] = output_dir or _resolve_default_output_dir()

    # Output context
    ctx.obj["output"] = OutputContext(json_mode=json_mode, quiet=quiet)


def _resolve_default_adb() -> str:
    """Resolve default ADB path with bundled fallback."""
    if shutil.which("adb"):
        return "adb"

    # Check bundled adb in app root
    app_root = _get_app_root()
    bundled = app_root / "bin" / "adb" / ("adb.exe" if sys.platform == "win32" else "adb")
    if bundled.exists():
        return str(bundled)

    return "adb"


def _resolve_default_output_dir() -> str:
    """Resolve default output directory."""
    app_root = _get_app_root()
    output_dir = app_root / "output"
    output_dir.mkdir(exist_ok=True)
    return str(output_dir)


def _get_app_root() -> Path:
    """Get application root directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


# =============================================================================
# REGISTER COMMANDS
# =============================================================================

from easy_tracer.cli.commands.devices import devices
from easy_tracer.cli.commands.systrace import systrace
from easy_tracer.cli.commands.perfetto import perfetto
from easy_tracer.cli.commands.simpleperf import simpleperf
from easy_tracer.cli.commands.traceview import traceview
from easy_tracer.cli.commands.combo import combo

cli.add_command(devices)
cli.add_command(systrace)
cli.add_command(perfetto)
cli.add_command(simpleperf)
cli.add_command(traceview)
cli.add_command(combo)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
