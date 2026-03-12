"""
Atrace Category Registry
========================
Single source of truth for all atrace category metadata and presets.
Zero UI dependency -- importable from framework, presenters, and UI layers.
"""

# =============================================================================
# CATEGORY DESCRIPTIONS
# =============================================================================

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "adb": "ADB",
    "aidl": "AIDL calls",
    "am": "Activity Manager",
    "audio": "Audio",
    "binder_driver": "Binder Kernel driver",
    "binder_lock": "Binder global lock trace",
    "bionic": "Bionic C Library",
    "camera": "Camera",
    "dalvik": "Dalvik VM",
    "database": "Database",
    "disk": "Disk I/O",
    "freq": "CPU Frequency",
    "gfx": "Graphics",
    "hal": "Hardware Modules",
    "hwui": "Hardware UI",
    "i2c": "I2C Events",
    "idle": "CPU Idle",
    "input": "Input",
    "ion": "ION allocation",
    "irq": "IRQ Events",
    "memory": "Memory",
    "memreclaim": "Kernel Memory Reclaim",
    "mmc": "eMMC commands",
    "network": "Network",
    "nnapi": "Neural Network API",
    "pagecache": "Pagecache",
    "pm": "Power Management",
    "power": "Power Management",
    "regulators": "Voltage and Current Regulators",
    "res": "Resource Loading",
    "rro": "Runtime Resource Overlay",
    "rs": "RenderScript",
    "sched": "CPU Scheduling",
    "sm": "Sync Manager",
    "ss": "System Server",
    "sync": "Synchronization",
    "thermal": "Thermal event",
    "vibrator": "Vibrator",
    "video": "Video",
    "view": "View System",
    "webview": "WebView",
    "wm": "Window Manager",
    "workq": "Workqueue",
}

# =============================================================================
# UNIFIED PRESETS
# =============================================================================

ATRACE_PRESETS: dict[str, list[str]] = {
    "standard": sorted([
        "sched", "freq", "idle", "am", "wm", "gfx", "view",
        "input", "dalvik", "binder_driver", "binder_lock",
    ]),
    "graphics": sorted([
        "sched", "freq", "idle", "am", "wm", "gfx", "view",
        "input", "dalvik", "binder_driver", "binder_lock",
        "hal", "hwui", "res", "rs", "webview",
    ]),
    "memory": sorted([
        "sched", "freq", "idle", "am", "wm", "gfx", "view", "dalvik",
    ]),
    "system": sorted([
        "sched", "freq", "idle", "am", "wm", "gfx", "view",
        "input", "dalvik", "binder_driver", "binder_lock",
        "hal", "ss", "pm", "power", "thermal",
        "disk", "sync", "memory", "memreclaim",
    ]),
    "full": sorted(CATEGORY_DESCRIPTIONS.keys()),
}

DEFAULT_ATRACE_CATEGORIES = ATRACE_PRESETS["standard"]

PRESET_ORDER = ["standard", "graphics", "memory", "system", "full"]


def detect_preset_name(selected: set[str]) -> str:
    """Match selected categories against known presets.

    Returns capitalized preset name on match, empty string otherwise.
    """
    for key in PRESET_ORDER:
        if selected == set(ATRACE_PRESETS[key]):
            return key.capitalize()
    return ""
