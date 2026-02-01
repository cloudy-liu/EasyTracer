import pytest
import tempfile
import shutil
import os
import sys
from pathlib import Path

# Add src to path so we can import modules even without installing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.adb_adapter import AdbAdapter

def pytest_configure(config):
    config.addinivalue_line("markers", "real_device: requires connected Android device")
    config.addinivalue_line("markers", "slow: test duration > 10 seconds")

def get_connected_device():
    """Returns first connected device serial or None."""
    try:
        adapter = AdbAdapter()
        devices = adapter.list_devices()
        for d in devices:
            if d.status == "device":
                return d.serial
    except Exception:
        pass
    return None

@pytest.fixture(scope="session")
def device_serial():
    """Session-scoped fixture providing device serial."""
    serial = get_connected_device()
    if serial is None:
        pytest.skip("No Android device connected")
    return serial

@pytest.fixture
def temp_output_dir():
    """Provides a temporary directory, cleaned up after test."""
    d = tempfile.mkdtemp(prefix="easytracer_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)

@pytest.fixture
def systrace_adapter():
    from easy_tracer.framework.systrace_adapter import SystraceAdapter
    return SystraceAdapter()

@pytest.fixture
def perfetto_adapter():
    from easy_tracer.framework.perfetto_adapter import PerfettoAdapter
    return PerfettoAdapter()

def pytest_collection_modifyitems(config, items):
    """Auto-skip real_device tests when no device connected."""
    skip_real = pytest.mark.skip(reason="No real device connected")

    # Check for device once at collection time
    device = get_connected_device()

    for item in items:
        if "real_device" in item.keywords and device is None:
            item.add_marker(skip_real)
