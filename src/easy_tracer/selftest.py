from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

from easy_tracer.framework import adb_helper as adb_helper_module
from easy_tracer.framework import perfetto_adapter as perfetto_adapter_module
from easy_tracer.framework import simpleperf_adapter as simpleperf_adapter_module
from easy_tracer.framework import systrace_adapter as systrace_adapter_module
from easy_tracer.services import capture_service as capture_service_module
from easy_tracer.services import perfetto_service as perfetto_service_module
from easy_tracer.services import simpleperf_service as simpleperf_service_module


@dataclass(frozen=True)
class _StepResult:
    name: str
    ok: bool
    details: str = ""


def _pick_device(adb: adb_helper_module.AdbHelper, requested: str | None) -> str:
    if requested:
        return requested
    devices = [d for d in adb.list_devices() if d.status == "device"]
    if not devices:
        raise RuntimeError("No connected Android device found (adb devices -l returned none).")
    return devices[0].serial


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _validate_systrace_html(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Systrace output not found: {path}")
    content = path.read_text(encoding="utf-8", errors="ignore")
    # The viewer HTML is always present; validate the embedded trace payload exists.
    if 'class="trace-data"' not in content and "class='trace-data'" not in content:
        raise RuntimeError("Systrace HTML missing trace-data script block.")
    if "# tracer" not in content:
        raise RuntimeError("Systrace trace payload missing/corrupted (expected '# tracer' header).")


def _validate_perfetto_trace(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Perfetto output not found: {path}")
    size = path.stat().st_size
    if size < 1024:
        raise RuntimeError(f"Perfetto output too small ({size} bytes): {path}")


def _validate_html_report(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Simpleperf report not found: {path}")
    head = path.read_text(encoding="utf-8", errors="ignore")[:2000].lower()
    if "<html" not in head and "<!doctype" not in head:
        raise RuntimeError("Simpleperf report does not look like HTML.")


def run_selftest(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="easy_tracer --selftest", add_help=True)
    parser.add_argument("--adb", default="adb", help="adb executable (default: adb)")
    parser.add_argument("--device", default="", help="device serial (default: first connected)")
    parser.add_argument("--output", default="", help="output dir (default: ./output/selftest_TIMESTAMP)")
    parser.add_argument("--package", default="com.android.settings", help="package for simpleperf app profiling")

    parser.add_argument("--systrace-seconds", type=int, default=2)
    parser.add_argument("--perfetto-seconds", type=int, default=2)
    parser.add_argument("--simpleperf-seconds", type=int, default=3)
    parser.add_argument("--simpleperf-frequency", type=int, default=1000)
    parser.add_argument("--skip-simpleperf", action="store_true", help="skip simpleperf step (for devices w/ restrictions)")

    args = parser.parse_args(argv)

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output).expanduser().resolve() if args.output else (Path.cwd() / "output" / f"selftest_{ts}")
    _ensure_dir(out_dir)
    report_path = out_dir / "selftest_report.txt"

    log_lines: list[str] = []

    def log(msg: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        line = f"[{stamp}] {msg}"
        log_lines.append(line)
        # In GUI builds (console=False), stdout may be invisible; the report file
        # is the primary artifact.
        try:
            print(line, flush=True)
        except Exception:
            pass

    results: list[_StepResult] = []
    try:
        log(f"Output dir: {out_dir}")
        adb = adb_helper_module.AdbHelper(adb_path=args.adb)
        if not adb.is_available():
            raise RuntimeError(f"adb not available: {args.adb}")

        serial = _pick_device(adb, args.device.strip() or None)
        log(f"Device serial: {serial}")

        # Systrace
        try:
            log("Systrace: capture start")
            systrace_adapter = systrace_adapter_module.SystraceAdapter(adb_path=args.adb)
            systrace_service = capture_service_module.CaptureService(systrace_adapter, output_dir=str(out_dir))
            sy_path = Path(
                systrace_service.start_capture(
                    device_serial=serial,
                    categories=["sched", "freq", "idle", "am", "wm", "view"],
                    duration_seconds=max(1, int(args.systrace_seconds)),
                    buffer_size_kb=8192,
                    app_name=None,
                    output_dir=str(out_dir),
                )
            )
            _validate_systrace_html(sy_path)
            results.append(_StepResult("systrace", True, str(sy_path)))
            log(f"Systrace: OK -> {sy_path}")
        except Exception as e:
            results.append(_StepResult("systrace", False, str(e)))
            log(f"Systrace: FAIL -> {e}")

        # Perfetto
        try:
            log("Perfetto: capture start")
            perfetto_adapter = perfetto_adapter_module.PerfettoAdapter(adb_path=args.adb)
            perfetto_service = perfetto_service_module.PerfettoService(perfetto_adapter, output_dir=str(out_dir))
            pf_path = Path(
                perfetto_service.record_trace(
                    device_serial=serial,
                    duration_seconds=max(1, int(args.perfetto_seconds)),
                    buffer_size_kb=40 * 1024,
                    categories=["sched", "freq", "idle", "am", "wm", "view", "gfx"],
                    output_dir=str(out_dir),
                )
            )
            _validate_perfetto_trace(pf_path)
            results.append(_StepResult("perfetto", True, str(pf_path)))
            log(f"Perfetto: OK -> {pf_path}")
        except Exception as e:
            results.append(_StepResult("perfetto", False, str(e)))
            log(f"Perfetto: FAIL -> {e}")

        # Simpleperf
        if args.skip_simpleperf:
            results.append(_StepResult("simpleperf", True, "SKIPPED"))
            log("Simpleperf: SKIPPED (--skip-simpleperf)")
        else:
            try:
                log("Simpleperf: app profiling start")
                simpleperf_adapter = simpleperf_adapter_module.SimpleperfAdapter(adb_path=args.adb)
                simpleperf_service = simpleperf_service_module.SimpleperfService(simpleperf_adapter, output_dir=str(out_dir))
                rep_path = Path(
                    simpleperf_service.profile_app(
                        device_serial=serial,
                        app_name=args.package,
                        duration_seconds=max(1, int(args.simpleperf_seconds)),
                        frequency=max(100, int(args.simpleperf_frequency)),
                        generate_report=True,
                        output_dir=str(out_dir),
                    )
                )
                _validate_html_report(rep_path)
                results.append(_StepResult("simpleperf", True, str(rep_path)))
                log(f"Simpleperf: OK -> {rep_path}")
            except Exception as e:
                results.append(_StepResult("simpleperf", False, str(e)))
                log(f"Simpleperf: FAIL -> {e}")

    finally:
        # Always write a report for post-mortem (especially in windowed EXE).
        try:
            lines = []
            lines.append(f"EasyTracer selftest report ({time.strftime('%Y-%m-%d %H:%M:%S')})")
            lines.append(f"Output dir: {out_dir}")
            lines.append("")
            for r in results:
                lines.append(f"{r.name}: {'PASS' if r.ok else 'FAIL'}")
                if r.details:
                    lines.append(f"  {r.details}")
            lines.append("")
            lines.extend(log_lines)
            report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    overall_ok = all(r.ok for r in results if r.name != "simpleperf" or not args.skip_simpleperf)
    if overall_ok:
        log(f"SELFTEST PASS (report: {report_path})")
        return 0
    log(f"SELFTEST FAIL (report: {report_path})")
    return 1
