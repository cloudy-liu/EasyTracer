from __future__ import annotations

import os
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from easy_tracer.framework.adb_adapter import AdbAdapter
from easy_tracer.framework.perfetto_adapter import PerfettoAdapter
from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter
from easy_tracer.framework.systrace_adapter import SystraceAdapter
from easy_tracer.framework.traceview_adapter import TraceviewAdapter
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.presenters.main_presenter import MainPresenter
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.services.capture_service import CaptureService
from easy_tracer.services.combo_service import ComboService
from easy_tracer.services.config_service import ConfigService
from easy_tracer.services.device_service import DeviceService
from easy_tracer.services.perfetto_service import PerfettoService
from easy_tracer.services.simpleperf_service import SimpleperfService
from easy_tracer.services.traceview_service import TraceviewService
from easy_tracer.ui.main_window import MainWindow
from easy_tracer.ui.theme.stylesheet import generate_app_stylesheet


def _build_window(tmp_path: Path) -> MainWindow:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    adb_adapter = AdbAdapter()
    systrace_adapter = SystraceAdapter()
    simpleperf_adapter = SimpleperfAdapter()
    perfetto_adapter = PerfettoAdapter()
    traceview_adapter = TraceviewAdapter()

    output_dir = tmp_path / "output"
    config_service = ConfigService(
        config_path=tmp_path / "config.json",
        default_adb_path="adb",
        default_output_dir=output_dir,
    )

    device_service = DeviceService(adb_adapter)
    capture_service = CaptureService(systrace_adapter, output_dir=str(output_dir))
    simpleperf_service = SimpleperfService(simpleperf_adapter, output_dir=str(output_dir))
    perfetto_service = PerfettoService(perfetto_adapter, output_dir=str(output_dir))
    traceview_service = TraceviewService(traceview_adapter, output_dir=str(output_dir))
    combo_service = ComboService(
        capture_service,
        simpleperf_service,
        perfetto_service,
        traceview_service,
        output_dir=str(output_dir),
    )

    window = MainWindow(
        MainPresenter(device_service),
        SystracePresenter(capture_service),
        SimpleperfPresenter(simpleperf_service),
        PerfettoPresenter(perfetto_service),
        TraceviewPresenter(traceview_service),
        ComboPresenter(combo_service),
        config_service,
        auto_refresh_devices=False,
    )
    app.processEvents()
    return window


def test_main_window_builds_prototype_shell(tmp_path):
    window = _build_window(tmp_path)

    try:
        assert window.findChild(QtWidgets.QWidget, "primaryToolbarRow") is not None
        assert window.findChild(QtWidgets.QWidget, "secondaryToolbarRow") is not None
        assert window.findChild(QtWidgets.QWidget, "sidebarNav") is not None
        assert window.findChild(QtWidgets.QWidget, "contentStackHost") is not None
        assert window.findChild(QtWidgets.QWidget, "logArea") is not None
        assert window.findChild(QtWidgets.QWidget, "statusBarContainer") is not None

        tracers_label = window.findChild(QtWidgets.QLabel, "navSectionTracers")
        system_label = window.findChild(QtWidgets.QLabel, "navSectionSystem")
        assert tracers_label is not None
        assert tracers_label.text() == "TRACERS"
        assert system_label is not None
        assert system_label.text() == "SYSTEM"
    finally:
        window.close()


def test_main_window_defaults_to_perfetto_panel(tmp_path):
    window = _build_window(tmp_path)

    try:
        current_panel = window.stack.currentWidget()
        assert current_panel is not None
        assert current_panel.property("panel_key") == "perfetto"
    finally:
        window.close()


def test_log_panel_can_collapse_and_expand(tmp_path):
    window = _build_window(tmp_path)

    try:
        log_panel = window.log_panel
        assert hasattr(log_panel, "is_collapsed")

        toggle = window.findChild(QtWidgets.QToolButton, "logToggleButton")
        assert toggle is not None
        assert log_panel.is_collapsed() is False

        toggle.click()
        assert log_panel.is_collapsed() is True

        toggle.click()
        assert log_panel.is_collapsed() is False
    finally:
        window.close()


def test_main_window_places_content_and_log_panel_in_vertical_splitter(tmp_path):
    window = _build_window(tmp_path)

    try:
        splitter = window.main_splitter
        assert splitter.orientation() == QtCore.Qt.Orientation.Vertical
        assert splitter.parentWidget().objectName() == "mainColumn"
        assert splitter.widget(0) is window.content_stack_host
        assert splitter.widget(1) is window.log_panel
    finally:
        window.close()


def test_log_panel_uses_compact_minimum_heights(tmp_path):
    window = _build_window(tmp_path)

    try:
        log_panel = window.log_panel
        assert log_panel.minimumHeight() == 96

        log_panel.toggle_collapsed()
        assert log_panel.minimumHeight() == 32
    finally:
        window.close()


def test_navigation_buttons_switch_stack_panels(tmp_path):
    window = _build_window(tmp_path)

    try:
        window._nav_buttons[6].click()
        assert window.stack.currentWidget().property("panel_key") == "settings"

        window._nav_buttons[0].click()
        assert window.stack.currentWidget().property("panel_key") == "device"
    finally:
        window.close()


def test_record_button_starts_disabled_without_ready_panel(tmp_path):
    window = _build_window(tmp_path)

    try:
        assert window.record_button.isEnabled() is False
    finally:
        window.close()


def test_window_uses_compact_default_height(tmp_path):
    window = _build_window(tmp_path)

    try:
        assert window.height() == 760
    finally:
        window.close()


def test_simpleperf_panel_removes_explanatory_info_card(tmp_path):
    window = _build_window(tmp_path)

    try:
        window._activate_stack_index(3)
        panel = window.simpleperf_panel
        assert panel is not None
        assert not hasattr(panel, "info_card")
    finally:
        window.close()


def test_traceview_panel_removes_explanatory_info_card(tmp_path):
    window = _build_window(tmp_path)

    try:
        window._activate_stack_index(4)
        panel = window.traceview_panel
        assert panel is not None
        assert not hasattr(panel, "info_card")
    finally:
        window.close()


def test_global_stylesheet_contains_combo_arrow_and_checkbox_states():
    stylesheet = generate_app_stylesheet()

    assert "QComboBox::down-arrow" in stylesheet
    assert "chevron-down.svg" in stylesheet
    assert "QCheckBox::indicator:checked" in stylesheet
    assert "background-color: #2196f3" in stylesheet
    assert "check-white.svg" in stylesheet
