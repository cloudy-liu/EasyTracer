from __future__ import annotations

from typing import List, Optional
from PySide6 import QtWidgets

from easy_tracer.models.device import Device
from easy_tracer.ui.theme import Colors, Spacing, Typography


class DevicePanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.devices: List[Device] = []

        title = QtWidgets.QLabel("Connected Devices")
        title.setStyleSheet(
            f"font-size: {Typography.SIZE_TITLE}px; font-weight: 600; color: {Colors.NEUTRAL_800};"
        )
        subtitle = QtWidgets.QLabel("Refresh the toolbar to detect USB and emulator targets.")
        subtitle.setStyleSheet(
            f"color: {Colors.NEUTRAL_600};"
        )

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Serial", "Model", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)

        self.selected_label = QtWidgets.QLabel("Selected device: None")
        self.selected_label.setStyleSheet(f"color: {Colors.NEUTRAL_600};")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)
        layout.addWidget(title)
        layout.addWidget(subtitle)
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
