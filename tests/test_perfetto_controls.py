from __future__ import annotations

import os

from PySide6 import QtWidgets

from easy_tracer.ui.components.perfetto_controls import (
    DATA_SOURCE_SECTIONS,
    PerfettoDataSourceTabs,
    AtraceScopeEditor,
)
from easy_tracer.ui.panels.app_targets import CUSTOM_PACKAGE_TARGET


def _build_app() -> QtWidgets.QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_data_source_tabs_own_enabled_state_and_counts():
    app = _build_app()
    tabs = PerfettoDataSourceTabs(DATA_SOURCE_SECTIONS)

    try:
        tabs.set_enabled_keys({"ftrace", "process_stats"})
        tabs.show()
        app.processEvents()

        assert tabs.is_enabled("ftrace") is True
        assert tabs.is_enabled("android_log") is False
        assert tabs.tabText(0) == "Core (2/2)"
        assert tabs.tabText(3) == "System (0/3)"

        tabs.checkbox("android_log").setChecked(True)
        app.processEvents()

        assert tabs.selected_keys() == {"ftrace", "process_stats", "android_log"}
        assert tabs.tabText(3) == "System (1/3)"
    finally:
        tabs.close()


def test_atrace_scope_editor_resolves_categories_and_app_scope():
    app = _build_app()
    editor = AtraceScopeEditor(["sched", "gfx"], total_categories=45)

    try:
        editor.show()
        app.processEvents()

        assert editor.selected_categories() == ["sched", "gfx"]
        assert editor.selected_apps() == ["*"]
        assert editor.category_summary._label.text() == "Custom | 2/45"

        editor.target_combo.setCurrentText(CUSTOM_PACKAGE_TARGET)
        editor.custom_target.setText("com.example.app")
        app.processEvents()

        assert editor.custom_target.isHidden() is False
        assert editor.selected_apps() == ["com.example.app"]
    finally:
        editor.close()
