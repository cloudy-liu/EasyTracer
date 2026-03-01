import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter
from easy_tracer.framework.adb_helper import AdbHelper


class TestSimpleperfAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_adb = MagicMock(spec=AdbHelper)
        self.mock_adb.run_shell.return_value = ""
        self.adapter = SimpleperfAdapter(adb=self.mock_adb)

    @patch('os.chdir')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_run_app_profiler_success(self, mock_makedirs, mock_exists, mock_chdir):
        mock_exists.return_value = True

        device_serial = "12345"
        app_name = "com.example.app"
        output_dir = "out"

        with patch.object(self.adapter, '_import_and_run_script') as mock_run_script:
            path = self.adapter.run_app_profiler(
                device_serial=device_serial,
                app_name=app_name,
                output_dir=output_dir,
                duration_seconds=5
            )

            # Path should contain perf_ prefix with timestamp
            self.assertTrue(path.startswith(os.path.join(output_dir, "perf_")))
            self.assertTrue(path.endswith(".data"))

            args = mock_run_script.call_args[0]
            self.assertIn("app_profiler.py", args[0])
            self.assertEqual(args[1], "app_profiler")
            script_args = args[2]
            self.assertIn("-p", script_args)
            self.assertIn(app_name, script_args)
            self.assertIn("--serial", script_args)
            self.assertIn(device_serial, script_args)

    def test_run_simpleperf_record_success(self):
        output_path = "local_perf.data"
        self.adapter.run_simpleperf_record(
            device_serial="123",
            output_path=output_path,
            duration_seconds=5
        )

        # Should have called run_shell for simpleperf record
        self.mock_adb.run_shell.assert_called_once()
        args = self.mock_adb.run_shell.call_args[0]
        self.assertEqual(args[0], "123")
        cmd_parts = args[1:]
        self.assertIn("simpleperf", cmd_parts)
        self.assertIn("record", cmd_parts)

        # Should have called pull_file
        self.mock_adb.pull_file.assert_called_once()
        pull_args = self.mock_adb.pull_file.call_args[0]
        self.assertEqual(pull_args[0], "123")
        self.assertEqual(pull_args[2], output_path)

    @patch('easy_tracer.framework.simpleperf_adapter.SimpleperfAdapter._import_and_run_script')
    @patch('os.path.exists')
    def test_generate_html_report_success(self, mock_exists, mock_run_script):
        mock_exists.return_value = True

        html_path = self.adapter.generate_html_report("perf.data", "report.html")
        self.assertEqual(html_path, "report.html")

        args = mock_run_script.call_args[0]
        self.assertIn("report_html.py", args[0])
        self.assertEqual(args[1], "report_html")
        self.assertIn("-i", args[2])
        self.assertIn("perf.data", args[2])


if __name__ == '__main__':
    unittest.main()
