from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from easy_tracer.framework.adb_helper import AdbHelper
from easy_tracer.framework.perfetto_adapter import PerfettoAdapter
from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter
from easy_tracer.framework.systrace_adapter import SystraceAdapter
from easy_tracer.framework.traceview_adapter import TraceviewAdapter
from easy_tracer.models.device import Device
from easy_tracer.services.capture_service import CaptureService
from easy_tracer.services.combo_service import ComboService
from easy_tracer.services.device_service import DeviceService
from easy_tracer.services.perfetto_service import PerfettoService
from easy_tracer.services.simpleperf_service import SimpleperfService
from easy_tracer.services.traceview_service import TraceviewService


@dataclass(frozen=True)
class RuntimeContext:
    adb: AdbHelper
    systrace_adapter: SystraceAdapter
    simpleperf_adapter: SimpleperfAdapter
    perfetto_adapter: PerfettoAdapter
    traceview_adapter: TraceviewAdapter
    device_service: DeviceService
    capture_service: CaptureService
    simpleperf_service: SimpleperfService
    perfetto_service: PerfettoService
    traceview_service: TraceviewService
    combo_service: ComboService


def get_app_root(module_file: str) -> Path:
    path = Path(module_file).resolve()
    for parent in path.parents:
        if parent.name == "src" and (parent / "easy_tracer").exists():
            return parent.parent
    return path.parents[2]


def resolve_target_device(devices: list[Device], requested_serial: str | None = None) -> str:
    ready_devices = [device for device in devices if device.status == "device"]
    if requested_serial:
        for device in ready_devices:
            if device.serial == requested_serial:
                return device.serial
        raise RuntimeError(f"Requested device not available: {requested_serial}")

    if not ready_devices:
        raise RuntimeError("No ready Android device connected")

    return ready_devices[0].serial


def build_runtime_context(adb_path: str, output_dir: str) -> RuntimeContext:
    adb = AdbHelper(adb_path=adb_path)

    systrace_adapter = SystraceAdapter(adb=adb)
    simpleperf_adapter = SimpleperfAdapter(adb=adb)
    perfetto_adapter = PerfettoAdapter(adb=adb)
    traceview_adapter = TraceviewAdapter(adb=adb)

    device_service = DeviceService(adb)
    capture_service = CaptureService(systrace_adapter, output_dir=output_dir, adb_helper=adb)
    simpleperf_service = SimpleperfService(simpleperf_adapter, output_dir=output_dir)
    perfetto_service = PerfettoService(perfetto_adapter, output_dir=output_dir)
    traceview_service = TraceviewService(traceview_adapter, output_dir=output_dir)
    combo_service = ComboService(
        systrace_service=capture_service,
        simpleperf_service=simpleperf_service,
        perfetto_service=perfetto_service,
        traceview_service=traceview_service,
        output_dir=output_dir,
    )

    return RuntimeContext(
        adb=adb,
        systrace_adapter=systrace_adapter,
        simpleperf_adapter=simpleperf_adapter,
        perfetto_adapter=perfetto_adapter,
        traceview_adapter=traceview_adapter,
        device_service=device_service,
        capture_service=capture_service,
        simpleperf_service=simpleperf_service,
        perfetto_service=perfetto_service,
        traceview_service=traceview_service,
        combo_service=combo_service,
    )


def current_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return get_app_root(__file__)
