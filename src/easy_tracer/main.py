from __future__ import annotations

import atexit
from pathlib import Path
import subprocess
import shutil
import sys

# Dev convenience: allow running the app directly from the repo without installing.
# In frozen (PyInstaller) builds, sys.path is already configured and we should not
# mutate it (extra path entries slow down imports and can affect module discovery).
if not getattr(sys, "frozen", False):
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir.parent  # .../src
    if src_dir.name == "src" and (src_dir / "easy_tracer").exists():
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

from PySide6 import QtWidgets
from easy_tracer.ui.theme import generate_app_stylesheet
from easy_tracer.framework import adb_helper as adb_helper_module
from easy_tracer.framework import systrace_adapter as systrace_adapter_module
from easy_tracer.framework import simpleperf_adapter as simpleperf_adapter_module
from easy_tracer.framework import perfetto_adapter as perfetto_adapter_module
from easy_tracer.framework import traceview_adapter as traceview_adapter_module
from easy_tracer.framework import subprocess_utils
from easy_tracer.services import device_service as device_service_module
from easy_tracer.services import capture_service as capture_service_module
from easy_tracer.services import simpleperf_service as simpleperf_service_module
from easy_tracer.services import perfetto_service as perfetto_service_module
from easy_tracer.services import traceview_service as traceview_service_module
from easy_tracer.services import combo_service as combo_service_module
from easy_tracer.services import config_service as config_service_module
from easy_tracer.presenters import main_presenter as main_presenter_module
from easy_tracer.presenters import systrace_presenter as systrace_presenter_module
from easy_tracer.presenters import simpleperf_presenter as simpleperf_presenter_module
from easy_tracer.presenters import perfetto_presenter as perfetto_presenter_module
from easy_tracer.presenters import traceview_presenter as traceview_presenter_module
from easy_tracer.presenters import combo_presenter as combo_presenter_module
from easy_tracer.ui import main_window as main_window_module


def _kill_adb_server(adb_path: str) -> None:
    """Kill ADB server on application exit to release file locks.

    ADB uses a client-server architecture. When any adb command runs,
    it starts a background ADB server daemon that persists independently.
    This daemon holds a lock on the adb.exe in the dist directory,
    preventing deletion. We must explicitly kill it on exit.
    """
    try:
        subprocess_utils.check_output([adb_path, "kill-server"], timeout=5)
    except Exception:
        pass  # Best effort cleanup


def _get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def run() -> None:
    # Self-test mode (headless) - useful for packaged EXE closed-loop validation.
    if "--selftest" in sys.argv:
        from easy_tracer import selftest as selftest_module

        argv = [a for a in sys.argv[1:] if a != "--selftest"]
        sys.exit(selftest_module.run_selftest(argv))

    # Warmup mode: used by the release script to pay the "first launch" cost
    # (Windows Defender / DLL cold-cache) during packaging instead of the first
    # interactive run.
    warmup = "--warmup" in sys.argv
    if warmup:
        sys.argv = [a for a in sys.argv if a != "--warmup"]

    # =========================================================================
    # FAST STARTUP: Create QApplication and show window FIRST
    # Heavy service initialization is deferred to avoid blocking UI display
    # =========================================================================
    app = QtWidgets.QApplication(sys.argv)

    # Apply global stylesheet for consistent visual design
    app.setStyleSheet(generate_app_stylesheet())

    app_root = _get_app_root()
    bundled_adb = app_root / "bin" / "adb" / ("adb.exe" if sys.platform == "win32" else "adb")
    # Prefer system adb (PATH) first; fallback to bundled adb if missing.
    default_adb_path = "adb" if shutil.which("adb") else (str(bundled_adb) if bundled_adb.exists() else "adb")
    config_service = config_service_module.ConfigService(
        config_path=app_root / "config.json",
        default_adb_path=default_adb_path,
        default_output_dir=app_root / "output",
    )

    # Register cleanup handler to kill ADB server on exit (avoid file locks).
    # Skip in warmup runs to keep them side-effect free and fast.
    if not warmup:
        atexit.register(lambda: _kill_adb_server(config_service.adb_path))

    # =========================================================================
    # UNIFIED ADB HELPER - Single source of truth for all ADB operations
    # =========================================================================
    adb = adb_helper_module.AdbHelper(adb_path=config_service.adb_path)

    # Adapters - share the same AdbHelper instance for unified resource management
    systrace_adapter = systrace_adapter_module.SystraceAdapter(adb=adb)
    simpleperf_adapter = simpleperf_adapter_module.SimpleperfAdapter(adb=adb)
    perfetto_adapter = perfetto_adapter_module.PerfettoAdapter(adb=adb)
    traceview_adapter = traceview_adapter_module.TraceviewAdapter(adb=adb)

    # Services - lightweight wrappers
    device_service = device_service_module.DeviceService(adb)
    capture_service = capture_service_module.CaptureService(
        systrace_adapter,
        output_dir=config_service.output_dir,
        adb_helper=adb,
    )
    simpleperf_service = simpleperf_service_module.SimpleperfService(simpleperf_adapter, output_dir=config_service.output_dir)
    perfetto_service = perfetto_service_module.PerfettoService(perfetto_adapter, output_dir=config_service.output_dir)
    traceview_service = traceview_service_module.TraceviewService(traceview_adapter, output_dir=config_service.output_dir)
    combo_service = combo_service_module.ComboService(
        systrace_service=capture_service,
        simpleperf_service=simpleperf_service,
        perfetto_service=perfetto_service,
        traceview_service=traceview_service,
        output_dir=config_service.output_dir,
    )

    # Presenters - pass capture_service for auxiliary dump functionality
    main_presenter = main_presenter_module.MainPresenter(device_service)
    systrace_presenter = systrace_presenter_module.SystracePresenter(capture_service)
    simpleperf_presenter = simpleperf_presenter_module.SimpleperfPresenter(
        simpleperf_service,
        capture_service=capture_service,
    )
    perfetto_presenter = perfetto_presenter_module.PerfettoPresenter(
        perfetto_service,
        capture_service=capture_service,
    )
    traceview_presenter = traceview_presenter_module.TraceviewPresenter(traceview_service)
    combo_presenter = combo_presenter_module.ComboPresenter(combo_service)

    # Create and show window immediately
    window = main_window_module.MainWindow(
        main_presenter,
        systrace_presenter,
        simpleperf_presenter,
        perfetto_presenter,
        traceview_presenter,
        combo_presenter,
        config_service,
        auto_refresh_devices=not warmup,
    )
    if warmup:
        # Force-create all tabs without touching ADB; then exit immediately.
        try:
            window.warmup_ui()
            app.processEvents()
        except Exception:
            pass
        return

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
