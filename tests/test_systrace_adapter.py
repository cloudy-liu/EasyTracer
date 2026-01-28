import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.systrace_adapter import SystraceAdapter

class TestSystraceAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = SystraceAdapter()

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_run_systrace_success(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(stdout="Tracing complete", returncode=0)

        output_file = "trace.html"
        time_seconds = 5
        device_serial = "12345"
        categories = ["sched", "gfx"]

        result = self.adapter.run_systrace(
            output_file=output_file,
            time_seconds=time_seconds,
            device_serial=device_serial,
            categories=categories
        )

        self.assertEqual(result, "Tracing complete")

        # Verify call args
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], sys.executable)
        self.assertIn("-o", args)
        self.assertIn(output_file, args)
        self.assertIn("-t", args)
        self.assertIn(str(time_seconds), args)
        self.assertIn("-e", args)
        self.assertIn(device_serial, args)
        self.assertIn("sched", args)
        self.assertIn("gfx", args)

    @patch('os.path.exists')
    def test_run_systrace_script_not_found(self, mock_exists):
        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError):
             self.adapter.run_systrace(
                output_file="out.html",
                time_seconds=5,
                device_serial="123",
                categories=[]
            )

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_get_categories_success(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_stdout = """
        gfx - Graphics
        sched - CPU Scheduling
        """
        mock_run.return_value = MagicMock(stdout=mock_stdout, returncode=0)

        cats = self.adapter.get_categories("123")
        self.assertIn("gfx", cats)
        self.assertIn("sched", cats)
        self.assertEqual(len(cats), 2)

if __name__ == '__main__':
    unittest.main()
