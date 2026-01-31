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
        
        # Mock _import_and_run_systrace to avoid running the complex script
        with patch.object(self.adapter, '_import_and_run_systrace', return_value="Tracing complete") as mock_import_run:
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
            
            # Verify args
            args = mock_import_run.call_args[0][0]
            self.assertIn("-o", args)
            self.assertIn(output_file, args)
            self.assertIn("-t", args)
            self.assertIn(str(time_seconds), args)
            self.assertIn("-e", args)
            self.assertIn(device_serial, args)

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
        mock_stdout = "gfx - Graphics\nsched - CPU Scheduling"
        
        with patch.object(self.adapter, '_import_and_run_systrace', return_value=mock_stdout):
            cats = self.adapter.get_categories("123")
            self.assertIn("gfx", cats)
            self.assertIn("sched", cats)
            self.assertEqual(len(cats), 2)

if __name__ == '__main__':
    unittest.main()
