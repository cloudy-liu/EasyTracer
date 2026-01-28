from __future__ import annotations

from pathlib import Path
import sys

# Ensure the src directory is in the python path (must happen BEFORE importing easy_tracer.*)
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6 import QtWidgets
from easy_tracer.framework.adb_adapter import AdbAdapter
from easy_tracer.framework.systrace_adapter import SystraceAdapter
from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter
from easy_tracer.framework.perfetto_adapter import PerfettoAdapter
from easy_tracer.framework.traceview_adapter import TraceviewAdapter
from easy_tracer.services.device_service import DeviceService
from easy_tracer.services.capture_service import CaptureService
from easy_tracer.services.simpleperf_service import SimpleperfService
from easy_tracer.services.perfetto_service import PerfettoService
from easy_tracer.services.traceview_service import TraceviewService
from easy_tracer.services.combo_service import ComboService
from easy_tracer.services.config_service import ConfigService
from easy_tracer.presenters.main_presenter import MainPresenter
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.ui.main_window import MainWindow


def _get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def run() -> None:
    app_root = _get_app_root()
    config_service = ConfigService(
        config_path=app_root / "config.json",
        default_adb_path="adb",
        default_output_dir=app_root / "output",
    )

    adb_adapter = AdbAdapter(adb_path=config_service.adb_path)
    device_service = DeviceService(adb_adapter)
    main_presenter = MainPresenter(device_service)

    systrace_adapter = SystraceAdapter(adb_path=config_service.adb_path)
    capture_service = CaptureService(systrace_adapter, output_dir=config_service.output_dir)
    systrace_presenter = SystracePresenter(capture_service)

    simpleperf_adapter = SimpleperfAdapter(adb_path=config_service.adb_path)
    simpleperf_service = SimpleperfService(simpleperf_adapter, output_dir=config_service.output_dir)
    simpleperf_presenter = SimpleperfPresenter(simpleperf_service)

    perfetto_adapter = PerfettoAdapter(adb_path=config_service.adb_path)
    perfetto_service = PerfettoService(perfetto_adapter, output_dir=config_service.output_dir)
    perfetto_presenter = PerfettoPresenter(perfetto_service)

    traceview_adapter = TraceviewAdapter(adb_path=config_service.adb_path)
    traceview_service = TraceviewService(traceview_adapter, output_dir=config_service.output_dir)
    traceview_presenter = TraceviewPresenter(traceview_service)

    combo_service = ComboService(
        systrace_service=capture_service,
        simpleperf_service=simpleperf_service,
        perfetto_service=perfetto_service,
        traceview_service=traceview_service,
        output_dir=config_service.output_dir,
    )
    combo_presenter = ComboPresenter(combo_service)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(
        main_presenter,
        systrace_presenter,
        simpleperf_presenter,
        perfetto_presenter,
        traceview_presenter,
        combo_presenter,
        config_service,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
