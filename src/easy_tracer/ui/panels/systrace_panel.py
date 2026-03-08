"""
Systrace Panel
==============
Configuration and control panel for Android systrace capture.

Architecture:
- CategorySelector: grouped, filterable category selection
- Inline configuration: Duration/Target/Buffer directly in panel (no modal)
- Presenter: handles all capture logic

Removed: Ftrace tab (dead code - UI allowed selection but start_capture never used it)
"""

from typing import Optional, Dict
from PySide6 import QtCore, QtWidgets, QtGui
from easy_tracer.models.requests import SystraceRequest
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.components.category_selector import CategorySelector, PRESETS
from easy_tracer.ui.components.cards import DeprecationBanner
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.theme import Colors, Spacing


# =============================================================================
# DEFAULT CATEGORIES
# =============================================================================

DEFAULT_ATRACE_CATEGORIES = [
    "sched", "freq", "idle", "am", "wm", "view", "gfx",
    "input", "dalvik", "binder_driver", "binder_lock",
]
DEFAULT_ATRACE_SET = set(DEFAULT_ATRACE_CATEGORIES)


# =============================================================================
# UPDATE SIGNAL BRIDGE
# =============================================================================

class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


# =============================================================================
# SYSTRACE PANEL
# =============================================================================

class SystracePanel(BasePanel):
    """Main Systrace configuration panel.

    Layout:
    ┌─ CAPTURE CONFIGURATION ───────────────────────────────────┐
    │ Duration: [5s v]  Target: [Top App v]  Buffer: [10240 KB] │
    │ Output: [...output...]  [📂]   [ ] Enhanced thread names  │
    └───────────────────────────────────────────────────────────┘
    ┌─ TRACE CATEGORIES ────────────────────────────────────────┐
    │ [Filter...                           ] [12 of 45] [Refresh]│
    │ Presets: (Minimal) (Graphics) (System) [All] [Clear]      │
    ├───────────────────────────────────────────────────────────┤
    │ ▼ Scheduling (4/5)    ▼ Graphics (6/8)    ▼ Binder (2/2)  │
    │   [x] sched             [x] gfx             [x] binder    │
    └───────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        presenter: SystracePresenter,
        device_serial: Optional[str],
        default_output_dir: str,
    ):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._auto_loaded_serial: Optional[str] = None
        self._auxiliary_options: Dict[str, bool] = {}

        # Presenter update bridge
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self._setup_ui()
        self.update_device(self.device_serial)

    def set_auxiliary_options(self, options: Dict[str, bool]) -> None:
        """Set auxiliary output options from main window."""
        self._auxiliary_options = options

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.MD)

        # =====================================================================
        # DEPRECATION BANNER
        # =====================================================================
        self._deprecation = DeprecationBanner(
            "Systrace is deprecated. Google recommends Perfetto for devices running Android 10+.",
            link_text="Switch to Perfetto",
        )
        layout.addWidget(self._deprecation)

        # =====================================================================
        # CAPTURE CONFIGURATION GROUP
        # =====================================================================
        config_group = QtWidgets.QGroupBox("Capture Configuration")
        config_layout = QtWidgets.QGridLayout(config_group)
        config_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        config_layout.setHorizontalSpacing(Spacing.LG)
        config_layout.setVerticalSpacing(Spacing.MD)

        # Row 0: Duration, Target, Buffer
        # Duration
        config_layout.addWidget(QtWidgets.QLabel("Duration:"), 0, 0)
        duration_widget = QtWidgets.QWidget()
        duration_layout = QtWidgets.QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(Spacing.SM)

        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "7s", "10s", "30s", "60s", "Custom"])
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)
        duration_layout.addWidget(self.duration_combo)

        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.custom_duration.setVisible(False)
        duration_layout.addWidget(self.custom_duration)

        config_layout.addWidget(duration_widget, 0, 1)

        # Target
        config_layout.addWidget(QtWidgets.QLabel("Target:"), 0, 2)
        target_widget = QtWidgets.QWidget()
        target_layout = QtWidgets.QHBoxLayout(target_widget)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(Spacing.SM)

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems([
            "All Apps (*)",
            "Top App (Foreground)",
            "Launcher",
            "SystemUI",
            "Settings",
            "Custom Package",
        ])
        self.target_combo.currentTextChanged.connect(self._toggle_custom_target)
        target_layout.addWidget(self.target_combo)

        self.custom_target = QtWidgets.QLineEdit()
        self.custom_target.setPlaceholderText("com.example.app")
        self.custom_target.setEnabled(False)
        self.custom_target.setVisible(False)
        self.custom_target.setMinimumWidth(140)
        target_layout.addWidget(self.custom_target)

        config_layout.addWidget(target_widget, 0, 3)

        # Buffer
        config_layout.addWidget(QtWidgets.QLabel("Buffer:"), 0, 4)
        self.buffer_spin = QtWidgets.QSpinBox()
        self.buffer_spin.setRange(1024, 1024 * 1024)
        self.buffer_spin.setValue(10240)
        self.buffer_spin.setSuffix(" KB")
        self.buffer_spin.setSingleStep(1024)
        config_layout.addWidget(self.buffer_spin, 0, 5)

        # Row 1: Output path with Open button
        config_layout.addWidget(QtWidgets.QLabel("Output:"), 1, 0)
        output_widget = QtWidgets.QWidget()
        output_layout = QtWidgets.QHBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(Spacing.SM)

        self.output_path = OutputPathWidget(
            self.default_output_dir,
            label="",
            editable=True,
            tooltip="Shared output directory. Changes sync across panels.",
        )
        output_layout.addWidget(self.output_path, 1)

        self.open_output_btn = QtWidgets.QPushButton()
        self.open_output_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.open_output_btn.setToolTip("Open output directory")
        self.open_output_btn.setMaximumWidth(36)
        self.open_output_btn.clicked.connect(self._on_open_output)
        output_layout.addWidget(self.open_output_btn)

        config_layout.addWidget(output_widget, 1, 1, 1, 3)

        # Options
        options_widget = QtWidgets.QWidget()
        options_layout = QtWidgets.QHBoxLayout(options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(Spacing.LG)

        self.enhance_cb = QtWidgets.QCheckBox("Enhanced thread names")
        self.enhance_cb.setToolTip("Show detailed thread names in trace (may impact performance)")
        options_layout.addWidget(self.enhance_cb)

        options_layout.addStretch()
        config_layout.addWidget(options_widget, 1, 4, 1, 2)

        layout.addWidget(config_group)

        # =====================================================================
        # TRACE CATEGORIES GROUP
        # =====================================================================
        categories_group = QtWidgets.QGroupBox("Trace Categories")
        categories_layout = QtWidgets.QVBoxLayout(categories_group)
        categories_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        categories_layout.setSpacing(Spacing.SM)

        self.category_selector = CategorySelector()
        self.category_selector.refresh_button.clicked.connect(self._on_load_categories)
        self.category_selector.selection_changed.connect(self._notify_readiness)
        categories_layout.addWidget(self.category_selector, 1)

        layout.addWidget(categories_group, 1)

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _toggle_custom_duration(self, text: str) -> None:
        is_custom = text == "Custom"
        self.custom_duration.setEnabled(is_custom)
        self.custom_duration.setVisible(is_custom)

    def _toggle_custom_target(self, text: str) -> None:
        is_custom = text == "Custom Package"
        self.custom_target.setEnabled(is_custom)
        self.custom_target.setVisible(is_custom)

    def _on_open_output(self) -> None:
        output_dir = self.output_path.output_dir()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(output_dir))

    def _on_load_categories(self) -> None:
        if not self.device_serial or self.presenter.is_loading_categories:
            return
        self.category_selector.clear()
        run_in_thread(self.presenter.load_categories, self.device_serial)

    # =========================================================================
    # DEVICE MANAGEMENT
    # =========================================================================

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        can_load = bool(serial)
        self.category_selector.refresh_button.setEnabled(can_load)
        self._notify_readiness()

        if not serial:
            self.category_selector.clear()
            self._auto_loaded_serial = None
            self.status_message.emit("Please select a device.")
        else:
            self.status_message.emit(f"Selected device: {serial}.")
            should_auto_load = (
                serial != self._auto_loaded_serial
                or len(self.category_selector.get_selected()) == 0
            )
            if should_auto_load:
                self._auto_loaded_serial = serial
                self._on_load_categories()

    # =========================================================================
    # VIEW UPDATE (from presenter)
    # =========================================================================

    def update_view(self) -> None:
        busy = (
            self.presenter.is_loading_categories
            or self.presenter.is_capturing
        )
        self.busy_changed.emit(busy)

        # Populate categories when loaded
        if self.presenter.categories and not self.presenter.is_loading_categories:
            if len(self.category_selector.get_selected()) == 0:
                self.category_selector.set_categories(
                    self.presenter.categories,
                    DEFAULT_ATRACE_SET,
                )

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)

        if self.presenter.last_output_path:
            self.status_message.emit(
                f"Capture saved to: {self.presenter.last_output_path}"
            )

        if self.presenter.is_loading_categories:
            self.status_message.emit("Loading categories...")
        elif not self.presenter.is_capturing:
            self.status_message.emit("Ready.")

        self.category_selector.refresh_button.setEnabled(
            bool(self.device_serial) and not busy
        )
        self._notify_readiness()

    # =========================================================================
    # READINESS
    # =========================================================================

    def _notify_readiness(self) -> None:
        busy = self.presenter.is_loading_categories or self.presenter.is_capturing
        can_run = bool(self.device_serial) and not busy
        self.readiness_changed.emit(can_run)

    def is_ready(self) -> bool:
        busy = self.presenter.is_loading_categories or self.presenter.is_capturing
        return bool(self.device_serial) and not busy

    # =========================================================================
    # CAPTURE CONTROL
    # =========================================================================

    def _get_duration(self) -> int:
        text = self.duration_combo.currentText()
        if text == "Custom":
            return int(self.custom_duration.value())
        return int(text.replace("s", ""))

    def _get_target_app(self) -> Optional[str]:
        text = self.target_combo.currentText()
        if text == "Custom Package":
            return self.custom_target.text().strip() or None
        if text == "Launcher":
            return "com.android.launcher3"
        if text == "SystemUI":
            return "com.android.systemui"
        if text == "Settings":
            return "com.android.settings"
        return None

    def start_capture(self) -> None:
        if not self.device_serial:
            self.error_message.emit("No device selected.")
            return

        selected = self.category_selector.get_selected()
        if not selected:
            # Fallback to defaults if no categories loaded
            if len(self.presenter.categories or []) == 0:
                selected = list(DEFAULT_ATRACE_CATEGORIES)
                self.status_message.emit(
                    "Using default categories (device list unavailable)."
                )
            else:
                self.error_message.emit("No categories selected.")
                return

        run_in_thread(
            self.presenter.run_request,
            SystraceRequest(
                device_serial=self.device_serial or "",
                categories=selected,
                duration_seconds=self._get_duration(),
                buffer_size_kb=self.buffer_spin.value(),
                app_name=self._get_target_app(),
                output_dir=self.output_path.output_dir(),
                auxiliary_options=self._auxiliary_options,
            ),
        )
        self.capture_started.emit(self._get_duration())

    def set_output_dir(self, output_dir: str) -> None:
        self.output_path.set_output_dir(output_dir)
