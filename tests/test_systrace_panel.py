from types import SimpleNamespace

from PySide6 import QtWidgets

from easy_tracer.ui.panels import systrace_panel as systrace_panel_module
from easy_tracer.ui.panels.systrace_panel import SystracePanel


def _make_presenter(**overrides):
    presenter = {
        "bind_view_update": lambda callback: None,
        "is_loading_categories": False,
        "is_capturing": False,
        "categories": [],
        "error_message": None,
        "last_output_path": None,
        "load_categories": lambda serial: None,
        "run_request": lambda request: None,
    }
    presenter.update(overrides)
    return SimpleNamespace(**presenter)


def _build_panel(monkeypatch, **presenter_overrides) -> SystracePanel:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(systrace_panel_module, "run_in_thread", lambda fn, *args: fn(*args))
    panel = SystracePanel(_make_presenter(**presenter_overrides), "SER123", "output")
    panel.show()
    app.processEvents()
    return panel


def test_systrace_panel_uses_dropdown_buffer_with_custom_value(monkeypatch):
    panel = _build_panel(monkeypatch)

    assert panel.buffer_combo.currentText() == "10240 KB"
    assert panel.buffer_detail_row.isVisible() is False
    assert panel.custom_buffer.isEnabled() is False

    panel.buffer_combo.setCurrentText("Custom")

    assert panel.buffer_detail_row.isVisible() is True
    assert panel.custom_buffer.isVisible() is True
    assert panel.custom_buffer.isEnabled() is True

    panel.custom_buffer.setValue(24576)
    assert panel._get_buffer_size_kb() == 24576


def test_systrace_panel_start_capture_uses_selected_buffer_size(monkeypatch):
    captured = {}
    panel = _build_panel(
        monkeypatch,
        run_request=lambda request: captured.setdefault("request", request),
    )

    panel.buffer_combo.setCurrentText("16384 KB")
    panel.start_capture()

    assert captured["request"].buffer_size_kb == 16384


def test_systrace_panel_custom_target_uses_detail_row_instead_of_inline_expansion(monkeypatch):
    panel = _build_panel(monkeypatch)

    assert (
        panel.target_combo.sizeAdjustPolicy()
        == QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    assert panel.target_combo.minimumContentsLength() == 12
    assert (
        panel.target_combo.sizePolicy().horizontalPolicy()
        == QtWidgets.QSizePolicy.Policy.Maximum
    )
    assert panel.target_detail_row.isVisible() is False
    assert panel.custom_target.parentWidget() is panel.target_detail_row

    panel.target_combo.setCurrentText("Custom Package")

    assert panel.target_detail_row.isVisible() is True
    assert panel.custom_target.isVisible() is True


def test_systrace_panel_output_path_keeps_expanded_width(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    panel = _build_panel(monkeypatch)
    panel.resize(1200, 700)
    app.processEvents()

    assert panel.output_path.parentWidget().width() >= 500


def test_systrace_panel_reports_legacy_status_without_banner(monkeypatch):
    panel = _build_panel(monkeypatch)
    messages = []
    panel.status_message.connect(messages.append)

    panel.update_device("SER123")

    assert not hasattr(panel, "_deprecation")
    assert messages[-1] == (
        "Selected device: SER123. Systrace is legacy; Perfetto is the default tracer."
    )
