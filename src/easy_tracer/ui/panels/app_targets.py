"""Shared app-scope presets for trace capture panels."""

from __future__ import annotations

from typing import Optional


ALL_APPS_TARGET = "All Apps (*)"
TOP_APP_TARGET = "Top App (Foreground)"
CUSTOM_PACKAGE_TARGET = "Custom Package"

APP_TARGET_OPTIONS = [
    ALL_APPS_TARGET,
    TOP_APP_TARGET,
    "Launcher",
    "SystemUI",
    "Settings",
    CUSTOM_PACKAGE_TARGET,
]

_NAMED_TARGET_APPS = {
    "Launcher": "com.android.launcher3",
    "SystemUI": "com.android.systemui",
    "Settings": "com.android.settings",
}


def resolve_target_package(selection: str, custom_value: str) -> Optional[str]:
    """Resolve a target preset to a concrete package when available."""
    if selection == CUSTOM_PACKAGE_TARGET:
        return custom_value.strip() or None
    return _NAMED_TARGET_APPS.get(selection)


def resolve_atrace_apps(selection: str, custom_value: str) -> list[str]:
    """Resolve the selected app scope into Perfetto atrace app filters."""
    if selection == ALL_APPS_TARGET:
        return ["*"]

    package = resolve_target_package(selection, custom_value)
    if package:
        return [package]

    # Foreground-app resolution is not wired yet, so unsupported presets
    # fall back to the wildcard scope instead of generating an empty config.
    return ["*"]
