from __future__ import annotations

import os

from PySide6 import QtWidgets

from easy_tracer.ui.dialogs.category_dialog import CategorySummaryWidget


def _build_app() -> QtWidgets.QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_category_summary_uses_edit_button_without_clipping():
    app = _build_app()
    widget = CategorySummaryWidget()

    try:
        widget.update_summary(
            ["am", "binder_driver", "binder_lock", "dalvik", "freq", "gfx"],
            45,
            "Standard",
        )
        widget.show()
        app.processEvents()

        assert widget._btn.text() == "Edit"
        assert widget._btn.maximumWidth() >= widget._btn.sizeHint().width()
    finally:
        widget.close()


def test_category_summary_places_edit_button_next_to_badge():
    app = _build_app()
    widget = CategorySummaryWidget()

    try:
        widget.update_summary(
            ["am", "binder_driver", "binder_lock", "dalvik", "freq", "gfx"],
            45,
            "Standard",
        )
        widget.show()
        app.processEvents()

        header = widget.layout().itemAt(0).layout()
        assert header is not None

        assert header.itemAt(0).widget() is widget._title
        assert header.itemAt(1).widget() is widget._label
        assert header.itemAt(2).widget() is widget._btn
        assert header.itemAt(3).spacerItem() is not None
    finally:
        widget.close()


def test_category_summary_shows_all_selected_chips_without_overflow():
    app = _build_app()
    widget = CategorySummaryWidget()

    try:
        selected = ["am", "binder_driver", "binder_lock", "dalvik", "freq", "gfx"]
        widget.update_summary(selected, 45, "Standard")
        widget.show()
        app.processEvents()

        chips = widget._chip_container.findChildren(QtWidgets.QLabel, "summaryChip")
        overflow = widget._chip_container.findChild(QtWidgets.QLabel, "summaryOverflowChip")

        assert [chip.text() for chip in chips] == sorted(selected)
        assert overflow is None
        assert widget._label.text() == "Standard | 6/45"
    finally:
        widget.close()


def test_category_summary_refresh_replaces_old_chips():
    app = _build_app()
    widget = CategorySummaryWidget()

    try:
        widget.update_summary(
            ["am", "binder_driver", "binder_lock", "dalvik", "freq", "gfx"],
            45,
            "Standard",
        )
        widget.update_summary(
            ["sched", "view", "wm"],
            45,
            "Custom",
        )
        widget.show()
        app.processEvents()

        chips = widget._chip_container.findChildren(QtWidgets.QLabel, "summaryChip")
        overflow = widget._chip_container.findChild(QtWidgets.QLabel, "summaryOverflowChip")

        assert [chip.text() for chip in chips] == ["sched", "view", "wm"]
        assert overflow is None
    finally:
        widget.close()
