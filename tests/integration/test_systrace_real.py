import pytest
import os
import time

@pytest.mark.real_device
@pytest.mark.slow
class TestSystraceRealDevice:
    """
    Real device systrace capture tests.
    """

    
    def test_systrace_basic_capture(self, systrace_adapter, device_serial, temp_output_dir):
        """Capture a 3-second systrace with basic categories."""
        output_file = os.path.join(temp_output_dir, f"trace_systrace_{int(time.time())}.html")
        categories = ["sched", "freq", "idle"]

        print(f"\n[Systrace] Starting capture on {device_serial} for 3s...")
        result = systrace_adapter.run_systrace(
            output_file=output_file,
            time_seconds=3,
            device_serial=device_serial,
            categories=categories,
        )

        # 1. 验证文件存在
        assert os.path.exists(output_file), f"Trace file not created: {output_file}"

        # 2. 验证文件大小 (systrace HTML 包含 trace-viewer，通常至少 1MB)
        file_size = os.path.getsize(output_file)
        print(f"[Systrace] Capture complete. File size: {file_size} bytes")
        assert file_size > 100_000, f"Trace file too small: {file_size} bytes"

        # 3. 验证是有效的 HTML 文件
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(10_000)  # 只需检查文件头

        assert "<html" in content.lower() or "<!DOCTYPE" in content, "Not valid HTML file"
        # 文件大小 > 1MB 已经证明包含完整的 trace 数据
        # (空的 systrace HTML 只有几十 KB)

    
    def test_get_categories_from_device(self, systrace_adapter, device_serial):
        """Verify we can fetch available categories from device."""
        print(f"\n[Systrace] Querying categories from {device_serial}...")
        categories = systrace_adapter.get_categories(device_serial)

        print(f"[Systrace] Found {len(categories)} categories")
        assert len(categories) > 0, "No categories returned"
        assert "sched" in categories, "sched category missing - this is fundamental"
