from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from easy_tracer.framework.perfetto_config_builder import PerfettoConfig


@dataclass(frozen=True)
class SystraceRequest:
    device_serial: str
    categories: list[str]
    duration_seconds: int = 5
    buffer_size_kb: int = 16384
    app_name: Optional[str] = None
    output_dir: Optional[str] = None
    auxiliary_options: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class PerfettoRequest:
    device_serial: str
    duration_seconds: int = 10
    buffer_size_kb: int = 32768
    categories: Optional[list[str]] = None
    output_dir: Optional[str] = None
    preset: Optional[str] = None
    config: Optional[PerfettoConfig] = None
    config_text: Optional[str] = None
    auxiliary_options: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class SimpleperfRequest:
    device_serial: str
    duration_seconds: int = 10
    frequency: int = 4000
    app_name: Optional[str] = None
    output_dir: Optional[str] = None
    cold_start: bool = False
    generate_report: bool = True
    auxiliary_options: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceviewStartRequest:
    device_serial: str
    package_name: str
    sampling: bool = False
    interval: int = 1000
    output_dir: Optional[str] = None


@dataclass(frozen=True)
class ComboRequest:
    device_serial: str
    duration_seconds: int = 5
    output_dir: Optional[str] = None
    systrace: Optional[SystraceRequest] = None
    perfetto: Optional[PerfettoRequest] = None
    simpleperf: Optional[SimpleperfRequest] = None
    traceview: Optional[TraceviewStartRequest] = None
    auxiliary_options: dict[str, bool] = field(default_factory=dict)
