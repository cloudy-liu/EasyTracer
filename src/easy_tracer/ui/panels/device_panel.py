from __future__ import annotations

from typing import List, Optional
from PySide6 import QtWidgets
from easy_tracer.models.device import Device


class DevicePanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.devices: List[Device] = []

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Serial", "Model", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.selected_label = QtWidgets.QLabel("Selected device: None")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Device List"))
        layout.addWidget(self.table, 1)
        layout.addWidget(self.selected_label)

    def set_devices(self, devices: List[Device]) -> None:
        self.devices = devices
        self.table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(device.serial))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(device.model))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(device.status))

    def set_selected_device(self, device: Optional[Device]) -> None:
        if device:
            self.selected_label.setText(f"Selected device: {device}")
        else:
            self.selected_label.setText("Selected device: None")
