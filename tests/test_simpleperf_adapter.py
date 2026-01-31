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

    @patch('os.chdir')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_run_app_profiler_success(self, mock_makedirs, mock_exists, mock_run, mock_chdir):
        # Mock paths existing
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        device_serial = "12345"
        app_name = "com.example.app"
        output_dir = "out"

        # Mock _import_and_run_script to avoid actual execution
        with patch.object(self.adapter, '_import_and_run_script') as mock_run_script:
            path = self.adapter.run_app_profiler(
                device_serial=device_serial,
                app_name=app_name,
                output_dir=output_dir,
                duration_seconds=5
            )

            expected_path = os.path.join(output_dir, "perf.data")
            self.assertEqual(path, expected_path)

            # Verify arguments passed to the script runner
            args = mock_run_script.call_args[0]
            self.assertIn("app_profiler.py", args[0])
            self.assertEqual(args[1], "app_profiler")
            script_args = args[2]
            self.assertIn("-p", script_args)
            self.assertIn(app_name, script_args)
            self.assertIn("--serial", script_args)
            self.assertIn(device_serial, script_args)

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

    @patch('easy_tracer.framework.simpleperf_adapter.SimpleperfAdapter._import_and_run_script')
    @patch('os.path.exists')
    def test_generate_html_report_success(self, mock_exists, mock_run_script):
        mock_exists.return_value = True
        
        html_path = self.adapter.generate_html_report("perf.data", "report.html")
        self.assertEqual(html_path, "report.html")

        args = mock_run_script.call_args[0]
        # args: (script_path, module_name, script_args)
        self.assertIn("report_html.py", args[0])
        self.assertEqual(args[1], "report_html")
        self.assertIn("-i", args[2])
        self.assertIn("perf.data", args[2])

if __name__ == '__main__':
    unittest.main()
