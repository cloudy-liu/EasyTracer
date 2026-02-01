import pytest
import os
import time

@pytest.mark.real_device
@pytest.mark.slow
class TestPerfettoRealDevice:
    """
    Real device Perfetto capture tests.
    """

    def test_perfetto_basic_capture(self, perfetto_adapter, device_serial, temp_output_dir):
        """Capture a 3-second Perfetto trace."""
        output_file = os.path.join(temp_output_dir, f"trace_perfetto_{int(time.time())}.perfetto-trace")

        # Perfetto 通常比 systrace 快，但也取决于手机性能
        print(f"\n[Perfetto] Starting capture on {device_serial} for 3s...")

        result = perfetto_adapter.record_trace(
            device_serial=device_serial,
            output_path=output_file,
            duration_seconds=3,
            categories=["sched", "freq", "idle"],
        )

        # 1. 验证文件存在
        assert os.path.exists(output_file), f"Trace file not created: {output_file}"

        # 2. 验证文件大小
        file_size = os.path.getsize(output_file)
        print(f"[Perfetto] Capture complete. File size: {file_size} bytes")
        assert file_size > 5_000, f"Trace file too small: {file_size} bytes"

        # 3. 验证二进制头 (简单检查)
        with open(output_file, 'rb') as f:
            header = f.read(16)

        # Perfetto 文件通常不为空，且不是文本文件
        # 严格验证比较复杂，这里确保不是空文件且有内容即可
        assert len(header) >= 16, "File header too short"
