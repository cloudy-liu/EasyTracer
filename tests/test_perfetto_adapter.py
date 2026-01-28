import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.perfetto_adapter import PerfettoAdapter

class TestPerfettoAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = PerfettoAdapter()

    @patch('subprocess.run')
    def test_record_trace_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        device_serial = "12345"
        output_path = "local.trace"

        path = self.adapter.record_trace(
            device_serial=device_serial,
            output_path=output_path,
            duration_seconds=5
        )

        self.assertEqual(path, output_path)

        # Expect 3 calls: shell perfetto, pull, shell rm
        self.assertEqual(mock_run.call_count, 3)

        # 1. Start Capture
        args1 = mock_run.call_args_list[0][0][0]
        self.assertEqual(args1[0], "adb")
        self.assertEqual(args1[3], "shell")
        self.assertEqual(args1[4], "perfetto")
        self.assertIn("-t", args1)
        self.assertIn("5s", args1)

        # 2. Pull
        args2 = mock_run.call_args_list[1][0][0]
        self.assertEqual(args2[0], "adb")
        self.assertEqual(args2[3], "pull")
        self.assertEqual(args2[5], output_path)

        # 3. Cleanup
        args3 = mock_run.call_args_list[2][0][0]
        self.assertEqual(args3[0], "adb")
        self.assertEqual(args3[3], "shell")
        self.assertEqual(args3[4], "rm")

if __name__ == '__main__':
    unittest.main()
