import unittest
import sys
import os
import tempfile
from pathlib import Path
from PySide6 import QtWidgets

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

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

from easy_tracer.presenters.main_presenter import MainPresenter
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.presenters.combo_presenter import ComboPresenter

from easy_tracer.services.config_service import ConfigService
from easy_tracer.ui.main_window import MainWindow

class SmokeTest(unittest.TestCase):
    def test_application_initialization(self):
        """
        Verifies that all components can be instantiated and wired together
        without raising ImportErrors or TypeErrors.
        """
        print("\nInitializing Infrastructure Layer...")
        adb_adapter = AdbAdapter()
        systrace_adapter = SystraceAdapter()
        simpleperf_adapter = SimpleperfAdapter()
        perfetto_adapter = PerfettoAdapter()
        traceview_adapter = TraceviewAdapter()

        print("Initializing Service Layer...")
        output_dir = "test_output"
        device_service = DeviceService(adb_adapter)
        capture_service = CaptureService(systrace_adapter, output_dir=output_dir)
        simpleperf_service = SimpleperfService(simpleperf_adapter, output_dir=output_dir)
        perfetto_service = PerfettoService(perfetto_adapter, output_dir=output_dir)
        traceview_service = TraceviewService(traceview_adapter, output_dir=output_dir)
        combo_service = ComboService(
            capture_service,
            simpleperf_service,
            perfetto_service,
            traceview_service,
            output_dir=output_dir
        )

        print("Initializing Presenter Layer...")
        main_presenter = MainPresenter(device_service)
        systrace_presenter = SystracePresenter(capture_service)
        simpleperf_presenter = SimpleperfPresenter(simpleperf_service)
        perfetto_presenter = PerfettoPresenter(perfetto_service)
        traceview_presenter = TraceviewPresenter(traceview_service)
        combo_presenter = ComboPresenter(combo_service)

        print("Initializing UI Layer (MainWindow)...")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            config_service = ConfigService(
                config_path=Path(temp_dir) / "config.json",
                default_adb_path="adb",
                default_output_dir=Path(temp_dir) / "output",
            )

            main_window = MainWindow(
                main_presenter,
                systrace_presenter,
                simpleperf_presenter,
                perfetto_presenter,
                traceview_presenter,
                combo_presenter,
                config_service,
            )

            self.assertIsNotNone(main_window)
            app.processEvents()
        print("Application initialization successful.")

if __name__ == '__main__':
    unittest.main()
