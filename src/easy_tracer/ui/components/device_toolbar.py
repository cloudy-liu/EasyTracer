from __future__ import annotations

from typing import List, Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.models.device import Device


class DeviceToolbar(QtWidgets.QWidget):
    refresh_requested = QtCore.Signal()
    device_changed = QtCore.Signal(object)
    options_changed = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._devices: List[Device] = []
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )

        self.label = QtWidgets.QLabel("Device:")
        self.combo = QtWidgets.QComboBox()
        self.combo.setMinimumWidth(280)
        self.refresh_button = QtWidgets.QPushButton("Refresh")

        self.logcat_cb = QtWidgets.QCheckBox("Logcat")
        self.packages_cb = QtWidgets.QCheckBox("Packages")
        self.ps_cb = QtWidgets.QCheckBox("PS")
        self.meminfo_cb = QtWidgets.QCheckBox("Meminfo")
        self.logcat_cb.setChecked(True)
        self.packages_cb.setChecked(True)

        row1 = QtWidgets.QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.addWidget(self.label)
        row1.addWidget(self.combo, 1)
        row1.addWidget(self.refresh_button)

        row2 = QtWidgets.QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.addWidget(QtWidgets.QLabel("抓取后附加输出:"))
        row2.addWidget(self.logcat_cb)
        row2.addWidget(self.packages_cb)
        row2.addWidget(self.ps_cb)
        row2.addWidget(self.meminfo_cb)
        row2.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row1)
        layout.addLayout(row2)

        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.combo.currentIndexChanged.connect(self._on_selection_changed)
        self.logcat_cb.stateChanged.connect(self.options_changed.emit)
        self.packages_cb.stateChanged.connect(self.options_changed.emit)
        self.ps_cb.stateChanged.connect(self.options_changed.emit)
        self.meminfo_cb.stateChanged.connect(self.options_changed.emit)

    def set_devices(self, devices: List[Device]) -> None:
        self._devices = devices
        self.combo.blockSignals(True)
        self.combo.clear()
        if not devices:
            self.combo.addItem("No devices")
            self.combo.setCurrentIndex(0)
        else:
            for device in devices:
                self.combo.addItem(str(device), device)
            self.combo.setCurrentIndex(0)
        self.combo.blockSignals(False)
        self._emit_current_device()

    def _emit_current_device(self) -> None:
        device = self.current_device()
        self.device_changed.emit(device)

    def _on_selection_changed(self, _index: int) -> None:
        self._emit_current_device()

    def current_device(self) -> Optional[Device]:
        if not self._devices:
            return None
        data = self.combo.currentData()
        if isinstance(data, Device):
            return data
        index = self.combo.currentIndex()
        if index < 0 or index >= len(self._devices):
            return None
        return self._devices[index]

    def output_options(self) -> dict:
        return {
            "logcat": self.logcat_cb.isChecked(),
            "packages": self.packages_cb.isChecked(),
            "ps": self.ps_cb.isChecked(),
            "meminfo": self.meminfo_cb.isChecked(),
        }
