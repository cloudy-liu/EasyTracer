from PySide6 import QtWidgets, QtCore

class BaseSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, title="Advanced Settings"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 300)
        self.layout = QtWidgets.QVBoxLayout(self)

        self.content_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(self.content_layout)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def add_row(self, label: str, widget: QtWidgets.QWidget):
        self.content_layout.addRow(label, widget)

    def add_widget(self, widget: QtWidgets.QWidget):
        self.content_layout.addRow(widget)
