import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.services.combo_service import ComboService

class TestComboService(unittest.TestCase):
    def setUp(self):
        self.mock_systrace = MagicMock()
        self.mock_simpleperf = MagicMock()
        self.mock_perfetto = MagicMock()
        self.mock_traceview = MagicMock()
        self.output_dir = "test_output"

        self.service = ComboService(
            self.mock_systrace,
            self.mock_simpleperf,
            self.mock_perfetto,
            self.mock_traceview,
            output_dir=self.output_dir
        )

    @patch('os.makedirs')
    def test_start_combo_capture_all_enabled(self, mock_makedirs):
        # Setup mocks
        self.mock_systrace.start_capture.return_value = "systrace.html"
        self.mock_perfetto.record_trace.return_value = "perfetto.trace"
        self.mock_simpleperf.profile_app.return_value = "simpleperf.html"
        self.mock_traceview.stop_tracing.return_value = "traceview.trace"

        device_serial = "123"
        duration = 1
        enabled_tools = {
            'systrace': True,
            'perfetto': True,
            'simpleperf': True,
            'traceview': True
        }
        configs = {
            'package_name': 'com.example'
        }

        results = self.service.start_combo_capture(
            device_serial,
            duration,
            enabled_tools,
            configs
        )

        # Verify results
        self.assertEqual(results['systrace'], "systrace.html")
        self.assertEqual(results['perfetto'], "perfetto.trace")
        self.assertEqual(results['simpleperf'], "simpleperf.html")
        self.assertEqual(results['traceview'], "traceview.trace")

        # Verify calls
        self.mock_systrace.start_capture.assert_called_once()
        self.mock_perfetto.record_trace.assert_called_once()
        self.mock_simpleperf.profile_app.assert_called_once()

        # Traceview specific: start then stop
        self.mock_traceview.start_tracing.assert_called_once()
        self.mock_traceview.stop_tracing.assert_called_once()

    def test_start_combo_capture_partial(self):
        self.mock_systrace.start_capture.return_value = "systrace.html"

        device_serial = "123"
        duration = 1
        enabled_tools = {
            'systrace': True,
            'perfetto': False,
            'simpleperf': False,
            'traceview': False
        }
        configs = {}

        results = self.service.start_combo_capture(
            device_serial,
            duration,
            enabled_tools,
            configs
        )

        self.assertIn('systrace', results)
        self.assertNotIn('perfetto', results)

        self.mock_perfetto.record_trace.assert_not_called()

if __name__ == '__main__':
    unittest.main()
