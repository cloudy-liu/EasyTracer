from PySide6 import QtWidgets

from easy_tracer.ui.components.category_selector import CategorySelector, PRESETS


def _build_selector() -> CategorySelector:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    selector = CategorySelector()
    categories = sorted(set().union(*PRESETS.values()))
    selector.set_categories(categories, set())
    selector.show()
    app.processEvents()
    return selector


def test_clicking_preset_keeps_button_checked():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    selector = _build_selector()
    preset_btn = selector._presets._buttons["minimal"]

    preset_btn.click()
    app.processEvents()

    assert preset_btn.isChecked() is True
    assert set(selector.get_selected()) == PRESETS["minimal"]


def test_manual_selection_change_clears_active_preset():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    selector = _build_selector()
    preset_btn = selector._presets._buttons["minimal"]

    preset_btn.click()
    app.processEvents()

    selector._items["sched"].checkbox.click()
    app.processEvents()

    assert preset_btn.isChecked() is False


def test_clicking_select_all_keeps_action_button_checked():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    selector = _build_selector()

    selector._presets._all_btn.click()
    app.processEvents()

    assert selector._presets._all_btn.isChecked() is True
    assert len(selector.get_selected()) == len(selector._all_categories)


def test_clicking_clear_all_keeps_action_button_checked():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    selector = _build_selector()
    selector._presets._all_btn.click()
    app.processEvents()

    selector._presets._clear_btn.click()
    app.processEvents()

    assert selector._presets._clear_btn.isChecked() is True
    assert selector.get_selected() == []


def test_default_selection_highlights_matching_preset():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    selector = CategorySelector()
    categories = sorted(set().union(*PRESETS.values()))
    selector.set_categories(categories, PRESETS["minimal"])
    selector.show()
    app.processEvents()

    assert selector._presets._buttons["minimal"].isChecked() is True
