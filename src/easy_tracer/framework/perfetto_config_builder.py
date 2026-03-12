"""
Perfetto Config Builder
=======================
Generates Perfetto text-proto (pbtx) configuration files from structured options.

Reference: https://ui.perfetto.dev/#!/record
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from easy_tracer.models.category_registry import ATRACE_PRESETS


# =============================================================================
# PRESET DEFINITIONS
# =============================================================================

@dataclass
class PerfettoPreset:
    """Defines a preset configuration for common use cases."""
    name: str
    description: str
    buffer_size_kb: int
    duration_ms: int
    atrace_categories: List[str]
    ftrace_events: List[str]
    data_sources: List[str]
    meminfo_counters: List[str] = field(default_factory=list)


PRESETS: Dict[str, PerfettoPreset] = {
    "standard": PerfettoPreset(
        name="Standard",
        description="Basic system tracing with CPU scheduling and atrace",
        buffer_size_kb=32768,  # 32 MB
        duration_ms=10000,
        atrace_categories=list(ATRACE_PRESETS["standard"]),
        ftrace_events=[
            "sched/sched_switch",
            "sched/sched_wakeup",
            "power/cpu_frequency",
            "power/cpu_idle",
            "task/task_newtask",
            "task/task_rename",
        ],
        data_sources=["linux.ftrace", "linux.process_stats"],
    ),
    "graphics": PerfettoPreset(
        name="Graphics",
        description="Standard + SurfaceFlinger frame timeline and GPU memory",
        buffer_size_kb=65536,  # 64 MB
        duration_ms=10000,
        atrace_categories=list(ATRACE_PRESETS["graphics"]),
        ftrace_events=[
            "sched/sched_switch",
            "sched/sched_wakeup",
            "power/cpu_frequency",
            "power/cpu_idle",
            "power/gpu_frequency",
            "task/task_newtask",
            "task/task_rename",
        ],
        data_sources=[
            "linux.ftrace",
            "linux.process_stats",
            "android.surfaceflinger.frametimeline",
            "android.gpu.memory",
        ],
    ),
    "memory": PerfettoPreset(
        name="Memory",
        description="Standard + detailed memory tracking and heap profiling",
        buffer_size_kb=65536,  # 64 MB
        duration_ms=10000,
        atrace_categories=list(ATRACE_PRESETS["memory"]),
        ftrace_events=[
            "sched/sched_switch",
            "sched/sched_wakeup",
            "power/cpu_frequency",
            "power/cpu_idle",
            "task/task_newtask",
            "task/task_rename",
            "kmem/rss_stat",
        ],
        data_sources=[
            "linux.ftrace",
            "linux.process_stats",
            "linux.sys_stats",
        ],
        meminfo_counters=[
            "MEMINFO_MEM_TOTAL",
            "MEMINFO_MEM_FREE",
            "MEMINFO_MEM_AVAILABLE",
            "MEMINFO_BUFFERS",
            "MEMINFO_CACHED",
            "MEMINFO_SWAP_CACHED",
            "MEMINFO_ACTIVE",
            "MEMINFO_INACTIVE",
        ],
    ),
    "full": PerfettoPreset(
        name="Full",
        description="Complete system tracing with all data sources",
        buffer_size_kb=307200,  # 300 MB
        duration_ms=10000,
        atrace_categories=list(ATRACE_PRESETS["full"]),
        ftrace_events=[
            "sched/sched_switch",
            "sched/sched_wakeup",
            "sched/sched_waking",
            "sched/sched_process_exit",
            "power/cpu_frequency",
            "power/cpu_idle",
            "power/gpu_frequency",
            "power/suspend_resume",
            "task/task_newtask",
            "task/task_rename",
            "ftrace/print",
        ],
        data_sources=[
            "linux.ftrace",
            "linux.process_stats",
            "linux.sys_stats",
            "linux.system_info",
            "android.surfaceflinger.frametimeline",
            "android.gpu.memory",
            "android.packages_list",
            "android.log",
        ],
        meminfo_counters=[
            "MEMINFO_MEM_TOTAL",
            "MEMINFO_MEM_FREE",
            "MEMINFO_MEM_AVAILABLE",
            "MEMINFO_BUFFERS",
            "MEMINFO_CACHED",
            "MEMINFO_SWAP_CACHED",
            "MEMINFO_ACTIVE",
            "MEMINFO_INACTIVE",
            "MEMINFO_ACTIVE_ANON",
            "MEMINFO_INACTIVE_ANON",
            "MEMINFO_ACTIVE_FILE",
            "MEMINFO_INACTIVE_FILE",
            "MEMINFO_SWAP_TOTAL",
            "MEMINFO_SWAP_FREE",
            "MEMINFO_DIRTY",
            "MEMINFO_MAPPED",
            "MEMINFO_SHMEM",
        ],
    ),
}


# =============================================================================
# CONFIG BUILDER
# =============================================================================

@dataclass
class PerfettoConfig:
    """Configuration options for Perfetto trace recording."""
    duration_ms: int = 10000
    buffer_size_kb: int = 32768
    fill_policy: str = "RING_BUFFER"  # RING_BUFFER or DISCARD
    flush_period_ms: int = 30000
    write_period_ms: int = 2500

    # Atrace categories
    atrace_categories: List[str] = field(default_factory=list)
    atrace_apps: List[str] = field(default_factory=lambda: ["*"])

    # Ftrace events
    ftrace_events: List[str] = field(default_factory=list)
    ftrace_buffer_kb: int = 24576
    ftrace_drain_period_ms: int = 1000

    # Data sources
    enable_ftrace: bool = True
    enable_process_stats: bool = True
    enable_sys_stats: bool = False
    enable_system_info: bool = False
    enable_surfaceflinger: bool = False
    enable_gpu_memory: bool = False
    enable_packages_list: bool = False
    enable_android_log: bool = False

    # Process stats config
    proc_stats_poll_ms: int = 60000

    # Sys stats config
    meminfo_period_ms: int = 1000
    stat_period_ms: int = 1000
    meminfo_counters: List[str] = field(default_factory=list)


def build_config(config: PerfettoConfig) -> str:
    """Generate a Perfetto text-proto configuration string."""
    lines = []

    # Buffer configuration
    lines.append("buffers {")
    lines.append(f"  size_kb: {config.buffer_size_kb}")
    lines.append(f"  fill_policy: {config.fill_policy}")
    lines.append("}")
    lines.append("")

    # Duration
    lines.append(f"duration_ms: {config.duration_ms}")
    lines.append(f"flush_period_ms: {config.flush_period_ms}")
    lines.append(f"write_into_file: true")
    lines.append(f"file_write_period_ms: {config.write_period_ms}")
    lines.append("")

    # Ftrace data source
    if config.enable_ftrace:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "linux.ftrace"')
        lines.append("    ftrace_config {")
        lines.append(f"      ftrace_events: \"ftrace/print\"")
        for event in config.ftrace_events:
            lines.append(f'      ftrace_events: "{event}"')
        for cat in config.atrace_categories:
            lines.append(f'      atrace_categories: "{cat}"')
        for app in config.atrace_apps:
            lines.append(f'      atrace_apps: "{app}"')
        lines.append(f"      buffer_size_kb: {config.ftrace_buffer_kb}")
        lines.append(f"      drain_period_ms: {config.ftrace_drain_period_ms}")
        lines.append("    }")
        lines.append("  }")
        lines.append("}")
        lines.append("")

    # Process stats data source
    if config.enable_process_stats:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "linux.process_stats"')
        lines.append("    process_stats_config {")
        lines.append("      scan_all_processes_on_start: true")
        lines.append(f"      proc_stats_poll_ms: {config.proc_stats_poll_ms}")
        lines.append("    }")
        lines.append("  }")
        lines.append("}")
        lines.append("")

    # Sys stats data source
    if config.enable_sys_stats:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "linux.sys_stats"')
        lines.append("    sys_stats_config {")
        lines.append(f"      meminfo_period_ms: {config.meminfo_period_ms}")
        lines.append(f"      stat_period_ms: {config.stat_period_ms}")
        for counter in config.meminfo_counters:
            lines.append(f"      meminfo_counters: {counter}")
        lines.append("    }")
        lines.append("  }")
        lines.append("}")
        lines.append("")

    # System info
    if config.enable_system_info:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "linux.system_info"')
        lines.append("  }")
        lines.append("}")
        lines.append("")

    # SurfaceFlinger frame timeline
    if config.enable_surfaceflinger:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "android.surfaceflinger.frametimeline"')
        lines.append("  }")
        lines.append("}")
        lines.append("")

    # GPU memory
    if config.enable_gpu_memory:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "android.gpu.memory"')
        lines.append("  }")
        lines.append("}")
        lines.append("")

    # Packages list
    if config.enable_packages_list:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "android.packages_list"')
        lines.append("  }")
        lines.append("}")
        lines.append("")

    # Android log
    if config.enable_android_log:
        lines.append("data_sources {")
        lines.append("  config {")
        lines.append('    name: "android.log"')
        lines.append("    android_log_config {")
        lines.append("      log_ids: LID_DEFAULT")
        lines.append("      log_ids: LID_SYSTEM")
        lines.append("      log_ids: LID_EVENTS")
        lines.append("      log_ids: LID_CRASH")
        lines.append("    }")
        lines.append("  }")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def config_from_preset(preset_name: str, duration_ms: int = None) -> PerfettoConfig:
    """Create a PerfettoConfig from a named preset."""
    preset = PRESETS.get(preset_name, PRESETS["standard"])

    config = PerfettoConfig(
        duration_ms=duration_ms or preset.duration_ms,
        buffer_size_kb=preset.buffer_size_kb,
        atrace_categories=list(preset.atrace_categories),
        ftrace_events=list(preset.ftrace_events),
        meminfo_counters=list(preset.meminfo_counters),
    )

    # Enable data sources based on preset
    for ds in preset.data_sources:
        if ds == "linux.ftrace":
            config.enable_ftrace = True
        elif ds == "linux.process_stats":
            config.enable_process_stats = True
        elif ds == "linux.sys_stats":
            config.enable_sys_stats = True
        elif ds == "linux.system_info":
            config.enable_system_info = True
        elif ds == "android.surfaceflinger.frametimeline":
            config.enable_surfaceflinger = True
        elif ds == "android.gpu.memory":
            config.enable_gpu_memory = True
        elif ds == "android.packages_list":
            config.enable_packages_list = True
        elif ds == "android.log":
            config.enable_android_log = True

    return config
