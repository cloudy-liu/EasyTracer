import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.traceview_adapter import TraceviewAdapter

class TestTraceviewAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = TraceviewAdapter()

    @patch('subprocess.run')
    def test_start_tracing_default(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        device_serial = "123"
        package = "com.example"

        self.adapter.start_tracing(device_serial, package)

        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "adb")
        self.assertEqual(args[3], "shell")
        self.assertEqual(args[4], "am")
        self.assertEqual(args[5], "profile")
        self.assertEqual(args[6], "start")
        self.assertIn(package, args)
        # Verify no sampling flag
        self.assertNotIn("--sampling", args)

    @patch('subprocess.run')
    def test_start_tracing_sampling(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        self.adapter.start_tracing("123", "com.example", sampling=True, sampling_interval=1000)

        args = mock_run.call_args[0][0]
        self.assertIn("--sampling", args)
        self.assertIn("1000", args)

    @patch('time.sleep')
    @patch('subprocess.run')
    def test_stop_tracing_success(self, mock_run, mock_sleep):
        mock_run.return_value = MagicMock(returncode=0)

        output_path = "trace.trace"
        path = self.adapter.stop_tracing("123", "com.example", output_path)

        self.assertEqual(path, output_path)

        # Expected calls: stop, pull, rm
        self.assertEqual(mock_run.call_count, 3)

        # 1. Stop
        args1 = mock_run.call_args_list[0][0][0]
        self.assertEqual(args1[6], "stop")

        # 2. Pull
        args2 = mock_run.call_args_list[1][0][0]
        self.assertEqual(args2[3], "pull")

        # 3. Cleanup
        args3 = mock_run.call_args_list[2][0][0]
        self.assertEqual(args3[4], "rm")

if __name__ == '__main__':
    unittest.main()
