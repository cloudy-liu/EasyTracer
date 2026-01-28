import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter

class TestSimpleperfAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = SimpleperfAdapter()

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_run_app_profiler_success(self, mock_makedirs, mock_exists, mock_run):
        # Mock paths existing
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        device_serial = "12345"
        app_name = "com.example.app"
        output_dir = "out"

        path = self.adapter.run_app_profiler(
            device_serial=device_serial,
            app_name=app_name,
            output_dir=output_dir,
            duration_seconds=5
        )

        expected_path = os.path.join(output_dir, "perf.data")
        self.assertEqual(path, expected_path)

        # Verify command args
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], sys.executable)
        self.assertIn("app_profiler.py", args[1])
        self.assertIn("-p", args)
        self.assertIn(app_name, args)
        self.assertIn("--serial", args)
        self.assertIn(device_serial, args)

    @patch('subprocess.run')
    def test_run_simpleperf_record_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        output_path = "local_perf.data"
        self.adapter.run_simpleperf_record(
            device_serial="123",
            output_path=output_path,
            duration_seconds=5
        )

        # Should have called adb shell simpleperf record ...
        # And then adb pull ...
        self.assertEqual(mock_run.call_count, 2)

        # Check first call (record)
        args1 = mock_run.call_args_list[0][0][0]
        self.assertEqual(args1[0], "adb")
        self.assertIn("simpleperf record", args1[4])

        # Check second call (pull)
        args2 = mock_run.call_args_list[1][0][0]
        self.assertEqual(args2[0], "adb")
        self.assertEqual(args2[3], "pull")

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_generate_html_report_success(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        html_path = self.adapter.generate_html_report("perf.data", "report.html")
        self.assertEqual(html_path, "report.html")

        args = mock_run.call_args[0][0]
        self.assertIn("report_html.py", args[1])
        self.assertIn("-i", args)
        self.assertIn("perf.data", args)

if __name__ == '__main__':
    unittest.main()
