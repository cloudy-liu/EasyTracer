from typing import List, Dict
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QScrollArea,
    QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class SystraceAdvancedDialog(QDialog):
    """Dialog for advanced Systrace settings."""

    def __init__(self, parent=None) -> None:
        """Initialize the SystraceAdvancedDialog.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        uic.loadUi('ui/systrace_advanced_dialog.ui', self)
        
        # Set window modality and remove the "?" button
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Center the dialog on the parent window
        if parent:
            self.move(parent.frameGeometry().center() - self.frameGeometry().center())
        
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.select_all_button.clicked.connect(self.select_all_categories)
        self.deselect_all_button.clicked.connect(self.deselect_all_categories)

        # Adjust the style of select all and deselect all buttons
        self.adjust_button_styles()

        # Fake ftrace options for testing
        self.ftrace_options = [
            "function", "function_graph", "sched_switch", "sched_wakeup",
            "irq", "irq_off", "preemptirq", "preemptoff", "wakeup_dl",
            "wakeup_rt", "wakeup", "timer", "workqueue", "memblock"
        ]
        self.setup_ftrace_options()

    def adjust_button_styles(self):
        """Adjust the style of select all and deselect all buttons."""
        for button in [self.select_all_button, self.deselect_all_button]:
            button.setStyleSheet("""
                QPushButton {
                    padding: 5px;
                    font-size: 11px;
                    min-width: 80px;
                    max-width: 120px;
                }
            """)
            button.setFont(QFont("Arial", 9))

    def set_categories(self, categories: List[str], selected_categories: List[str]) -> None:
        """Set the list of categories in the dialog.

        Args:
            categories: A list of all category names.
            selected_categories: A list of previously selected category names.
        """
        for i in reversed(range(self.categories_layout.count())):
            self.categories_layout.itemAt(i).widget().deleteLater()
        for category in categories:
            checkbox = QCheckBox(category)
            checkbox.setChecked(category in selected_categories)
            self.categories_layout.addWidget(checkbox)

    def get_selected_categories(self) -> List[str]:
        """Get the list of selected categories.

        Returns:
            A list of selected category names.
        """
        return [
            checkbox.text()
            for checkbox in self.categories_widget.findChildren(QCheckBox)
            if checkbox.isChecked()
        ]

    def select_all_categories(self) -> None:
        """Select all atrace categories."""
        for checkbox in self.categories_widget.findChildren(QCheckBox):
            checkbox.setChecked(True)

    def deselect_all_categories(self) -> None:
        """Deselect all atrace categories."""
        for checkbox in self.categories_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def setup_ftrace_options(self) -> None:
        """Set up the ftrace options."""
        for i, option in enumerate(self.ftrace_options):
            checkbox = QCheckBox(option)
            self.ftrace_layout.addWidget(checkbox, i // 2, i % 2)

    def get_ftrace_options(self) -> List[str]:
        """Get the list of selected ftrace options."""
        return [
            checkbox.text()
            for checkbox in self.ftrace_group.findChildren(QCheckBox)
            if checkbox.isChecked()
        ]

    def get_commands(self) -> Dict[str, str]:
        """Get the pre-trace and post-trace commands."""
        return {
            'pre_command': self.pre_command_input.text(),
            'post_command': self.post_command_input.text()
        }