from PySide6 import QtWidgets

from easy_tracer.ui.panels.about_panel import AboutPanel


def test_about_panel_uses_hyperlink_label_without_repo_button():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    panel = AboutPanel()

    try:
        assert panel.link_label.openExternalLinks() is True
        assert 'href="https://github.com/cloudy-liu/EasyTracer"' in panel.link_label.text()
        assert panel.findChildren(QtWidgets.QPushButton) == []
    finally:
        panel.deleteLater()
