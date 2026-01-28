import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import tempfile
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

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

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for outputs
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "output")

        # Real Adapters
        self.adb_adapter = AdbAdapter()
        self.systrace_adapter = SystraceAdapter()
        self.simpleperf_adapter = SimpleperfAdapter()
        self.perfetto_adapter = PerfettoAdapter()
        self.traceview_adapter = TraceviewAdapter()

        # Real Services wired with Adapters
        self.device_service = DeviceService(self.adb_adapter)
        self.systrace_service = CaptureService(self.systrace_adapter, output_dir=self.output_dir)
        self.simpleperf_service = SimpleperfService(self.simpleperf_adapter, output_dir=self.output_dir)
        self.perfetto_service = PerfettoService(self.perfetto_adapter, output_dir=self.output_dir)
        self.traceview_service = TraceviewService(self.traceview_adapter, output_dir=self.output_dir)

        self.combo_service = ComboService(
            self.systrace_service,
            self.simpleperf_service,
            self.perfetto_service,
            self.traceview_service,
            output_dir=self.output_dir
        )

        self.device_serial = "test_device_serial"

    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.test_dir)

    @patch('subprocess.run')
    def test_e2e_device_list(self, mock_run):
        """Test fetching device list end-to-end (mocking only the low-level adb command)"""
        mock_output = """List of devices attached
test_device_serial        device product:test model:Test_Phone device:test
"""
        mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)

        devices = self.device_service.get_connected_devices()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].serial, self.device_serial)
        self.assertEqual(devices[0].model, "Test_Phone")

    @patch('subprocess.run')
    @patch('os.path.exists') # Mock existence of external scripts
    def test_e2e_systrace_capture(self, mock_exists, mock_run):
        """Test Systrace capture orchestration"""
        mock_exists.return_value = True # Pretend scripts exist
        mock_run.return_value = MagicMock(stdout="Trace collected", returncode=0)

        path = self.systrace_service.start_capture(
            device_serial=self.device_serial,
            categories=["sched", "gfx"],
            duration_seconds=1
        )

        # Verify output path structure
        self.assertTrue(path.startswith(self.output_dir))
        self.assertTrue(path.endswith(".html"))

        # Verify underlying command was called (this proves the Service->Adapter flow works)
        args = mock_run.call_args[0][0]
        self.assertIn("run_systrace.py", args[1])
        self.assertIn("-e", args)
        self.assertIn(self.device_serial, args)

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_e2e_perfetto_capture(self, mock_exists, mock_run):
        """Test Perfetto capture orchestration"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        path = self.perfetto_service.record_trace(
            device_serial=self.device_serial,
            duration_seconds=1,
            categories=["sched", "gfx"]
        )

        self.assertTrue(path.startswith(self.output_dir))
        self.assertTrue(path.endswith(".perfetto-trace"))

        # Verify calls (record -> pull -> cleanup)
        self.assertEqual(mock_run.call_count, 3)
        record_args = mock_run.call_args_list[0][0][0]
        self.assertIn("perfetto", record_args)
        self.assertIn("sched", record_args)

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.makedirs') # Mock creating dirs for simpleperf
    def test_e2e_simpleperf_app_profiling(self, mock_makedirs, mock_exists, mock_run):
        """Test Simpleperf App profiling orchestration"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        # We mock generate_html_report to just return the path we pass it,
        # avoiding the second subprocess call for simplicity in this test
        with patch.object(self.simpleperf_adapter, 'generate_html_report', side_effect=lambda d, h: h):
            path = self.simpleperf_service.profile_app(
                device_serial=self.device_serial,
                app_name="com.example.app",
                duration_seconds=1,
                generate_report=True
            )

            self.assertTrue(path.endswith("report.html"))

            # Verify app_profiler was called
            args = mock_run.call_args[0][0]
            self.assertIn("app_profiler.py", args[1])
            self.assertIn("-p", args)
            self.assertIn("com.example.app", args)

    @patch('subprocess.run')
    def test_e2e_traceview_flow(self, mock_run):
        """Test Traceview start/stop flow"""
        mock_run.return_value = MagicMock(returncode=0)

        # Start
        self.traceview_service.start_tracing(
            device_serial=self.device_serial,
            package_name="com.example.app",
            sampling=False,
            interval=1000
        )

        start_args = mock_run.call_args[0][0]
        self.assertIn("start", start_args)
        self.assertIn("com.example.app", start_args)

        # Stop
        path = self.traceview_service.stop_tracing(
            device_serial=self.device_serial,
            package_name="com.example.app"
        )

        self.assertTrue(path.endswith(".trace"))

        # Verify Stop calls (stop, pull, cleanup)
        # Note: call_count accumulates if we don't reset, but let's check the last few calls
        # 1 start call + 3 stop calls = 4 calls total
        self.assertEqual(mock_run.call_count, 4)

        stop_cmd = mock_run.call_args_list[1][0][0]
        self.assertIn("stop", stop_cmd)

        pull_cmd = mock_run.call_args_list[2][0][0]
        self.assertIn("pull", pull_cmd)

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_e2e_combo_capture(self, mock_exists, mock_run):
        """Test Combo Service orchestrating multiple tools"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        # Since combo runs in threads, the order of subprocess calls is non-deterministic.
        # But we can check that we get results for all enabled tools.

        # Mock specific adapter methods to avoid complex thread/subprocess mocking issues
        # We want to verify the orchestrator calls the services.

        with patch.object(self.systrace_service, 'start_capture', return_value="sys.html") as mock_sys, \
             patch.object(self.perfetto_service, 'record_trace', return_value="perf.trace") as mock_perf, \
             patch.object(self.simpleperf_service, 'profile_app', return_value="simp.html") as mock_simp, \
             patch.object(self.traceview_service, 'start_tracing') as mock_tv_start, \
             patch.object(self.traceview_service, 'stop_tracing', return_value="tv.trace") as mock_tv_stop:

            results = self.combo_service.start_combo_capture(
                device_serial=self.device_serial,
                duration=1,
                enabled_tools={
                    'systrace': True,
                    'perfetto': True,
                    'simpleperf': True,
                    'traceview': True
                },
                configs={'package_name': 'com.app'}
            )

            self.assertEqual(results['systrace'], "sys.html")
            self.assertEqual(results['perfetto'], "perf.trace")
            self.assertEqual(results['simpleperf'], "simp.html")
            self.assertEqual(results['traceview'], "tv.trace")

            mock_sys.assert_called_once()
            mock_perf.assert_called_once()
            mock_simp.assert_called_once()
            mock_tv_start.assert_called_once()
            mock_tv_stop.assert_called_once()

if __name__ == '__main__':
    unittest.main()
