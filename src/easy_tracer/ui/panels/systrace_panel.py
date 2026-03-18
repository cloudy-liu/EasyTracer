"""
Systrace Panel
==============
Configuration and control panel for Android systrace capture.

Architecture:
- CategoryDialog: modal category picker (replaces inline selector)
- CategorySummaryWidget: compact inline status display
- Inline configuration: Duration/Target/Buffer directly in panel
- Presenter: handles all capture logic
"""

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets
from easy_tracer.models.category_registry import (
    CATEGORY_DESCRIPTIONS,
    DEFAULT_ATRACE_CATEGORIES,
    detect_preset_name,
)
from easy_tracer.models.requests import SystraceRequest
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.components.cards import DeprecationBanner
from easy_tracer.ui.dialogs.category_dialog import CategoryDialog, CategorySummaryWidget
from easy_tracer.ui.panels.app_targets import (
    APP_TARGET_OPTIONS,
    CUSTOM_PACKAGE_TARGET,
    resolve_target_package,
)
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.theme import Spacing


# =============================================================================
# CONSTANTS
# =============================================================================

BUFFER_PRESET_VALUES_KB = [4096, 8192, 10240, 16384, 32768, 65536]


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
    +-- CAPTURE CONFIGURATION ------------------------------------------+
    | Duration: [5s v]  Target: [Top App v]  Buffer: [10240 KB]         |
    | Package: [com.example.app____________________]                    |
    | Buffer KB: [65536____________________________]                    |
    | Output: [...output...]  [dir]   [ ] Enhanced thread names         |
    | Atrace   [Standard | 11/45] [Edit]                                |
    | [am] [binder_driver] [binder_lock] [dalvik] [freq] [gfx]          |
    +-------------------------------------------------------------------+
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
        self._auxiliary_options: dict[str, bool] = {}
        self._all_categories: list[str] = []
        self._selected_categories: list[str] = list(DEFAULT_ATRACE_CATEGORIES)

        # Presenter update bridge
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self._setup_ui()
        self._update_category_summary()
        self.update_device(self.device_serial)

    def set_auxiliary_options(self, options: dict[str, bool]) -> None:
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
        config_layout = QtWidgets.QVBoxLayout(config_group)
        config_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        config_layout.setSpacing(Spacing.MD)

        # Row 0: Duration, Target, Buffer
        self._controls_row = QtWidgets.QHBoxLayout()
        self._controls_row.setSpacing(Spacing.LG)

        self._controls_row.addWidget(QtWidgets.QLabel("Duration:"))
        duration_widget = QtWidgets.QWidget()
        duration_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        duration_layout = QtWidgets.QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(Spacing.SM)

        self.duration_combo = QtWidgets.QComboBox()
        self._configure_compact_combo(self.duration_combo, 6)
        self.duration_combo.addItems(["5s", "7s", "10s", "30s", "60s", "Custom"])
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)
        duration_layout.addWidget(self.duration_combo)

        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.custom_duration.setVisible(False)
        self.custom_duration.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        duration_layout.addWidget(self.custom_duration)

        self._controls_row.addWidget(duration_widget)

        # Target
        self._controls_row.addWidget(QtWidgets.QLabel("Target:"))
        self.target_widget = QtWidgets.QWidget()
        self.target_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        target_layout = QtWidgets.QHBoxLayout(self.target_widget)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(Spacing.SM)

        self.target_combo = QtWidgets.QComboBox()
        self._configure_compact_combo(self.target_combo, 12)
        self.target_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.target_combo.addItems(APP_TARGET_OPTIONS)
        self.target_combo.currentTextChanged.connect(self._toggle_custom_target)
        target_layout.addWidget(self.target_combo)

        self._controls_row.addWidget(self.target_widget)

        # Buffer
        self._controls_row.addWidget(QtWidgets.QLabel("Buffer:"))
        buffer_widget = QtWidgets.QWidget()
        buffer_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        buffer_layout = QtWidgets.QHBoxLayout(buffer_widget)
        buffer_layout.setContentsMargins(0, 0, 0, 0)
        buffer_layout.setSpacing(Spacing.SM)

        self.buffer_combo = QtWidgets.QComboBox()
        self._configure_compact_combo(self.buffer_combo, 10)
        self.buffer_combo.addItems(
            [self._format_buffer_label(size_kb) for size_kb in BUFFER_PRESET_VALUES_KB] + ["Custom"]
        )
        self.buffer_combo.setCurrentText(self._format_buffer_label(10240))
        self.buffer_combo.currentTextChanged.connect(self._toggle_custom_buffer)
        buffer_layout.addWidget(self.buffer_combo)

        self._controls_row.addWidget(buffer_widget)
        self._controls_row.addStretch(1)
        config_layout.addLayout(self._controls_row)

        self.custom_target = QtWidgets.QLineEdit()
        self.custom_target.setPlaceholderText("com.example.app")
        self.custom_target.setEnabled(False)
        self.custom_target.setVisible(False)
        self.custom_target.setMinimumWidth(240)
        self.custom_target.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        self.custom_buffer = QtWidgets.QSpinBox()
        self.custom_buffer.setRange(1024, 1024 * 1024)
        self.custom_buffer.setValue(10240)
        self.custom_buffer.setSuffix(" KB")
        self.custom_buffer.setSingleStep(1024)
        self.custom_buffer.setEnabled(False)
        self.custom_buffer.setVisible(False)
        self.custom_buffer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        self._detail_rows = QtWidgets.QWidget()
        detail_rows_layout = QtWidgets.QVBoxLayout(self._detail_rows)
        detail_rows_layout.setContentsMargins(0, 0, 0, 0)
        detail_rows_layout.setSpacing(Spacing.SM)

        self.target_detail_row = self._build_detail_row("Package:", self.custom_target)
        self.buffer_detail_row = self._build_detail_row("Buffer KB:", self.custom_buffer)
        self.target_detail_row.setVisible(False)
        self.buffer_detail_row.setVisible(False)
        detail_rows_layout.addWidget(self.target_detail_row)
        detail_rows_layout.addWidget(self.buffer_detail_row)
        self._detail_rows.setVisible(False)
        config_layout.addWidget(self._detail_rows)

        # Row 1: Output path with Open button
        output_row = QtWidgets.QHBoxLayout()
        output_row.setSpacing(Spacing.LG)
        output_row.addWidget(QtWidgets.QLabel("Output:"))

        output_widget = QtWidgets.QWidget()
        output_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
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

        output_row.addWidget(output_widget, 1)

        # Options
        self.enhance_cb = QtWidgets.QCheckBox("Enhanced thread names")
        self.enhance_cb.setToolTip("Show detailed thread names in trace (may impact performance)")
        self.enhance_cb.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        output_row.addWidget(self.enhance_cb)
        config_layout.addLayout(output_row)

        # Row 2: Category summary + Select dialog trigger
        self._category_summary = CategorySummaryWidget()
        self._category_summary.select_requested.connect(self._on_select_categories)
        config_layout.addWidget(self._category_summary)

        layout.addWidget(config_group)
        layout.addStretch(1)
        self._sync_detail_rows()

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _configure_compact_combo(
        self,
        combo: QtWidgets.QComboBox,
        minimum_contents_length: int,
    ) -> None:
        combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(minimum_contents_length)

    def _format_buffer_label(self, size_kb: int) -> str:
        return f"{size_kb} KB"

    def _set_detail_row_state(
        self,
        row: QtWidgets.QWidget,
        field: QtWidgets.QWidget,
        is_visible: bool,
    ) -> None:
        field.setEnabled(is_visible)
        field.setVisible(is_visible)
        row.setVisible(is_visible)
        self._sync_detail_rows()

    def _toggle_custom_duration(self, text: str) -> None:
        is_custom = text == "Custom"
        self.custom_duration.setEnabled(is_custom)
        self.custom_duration.setVisible(is_custom)

    def _toggle_custom_target(self, text: str) -> None:
        is_custom = text == CUSTOM_PACKAGE_TARGET
        self._set_detail_row_state(self.target_detail_row, self.custom_target, is_custom)

    def _toggle_custom_buffer(self, text: str) -> None:
        is_custom = text == "Custom"
        self._set_detail_row_state(self.buffer_detail_row, self.custom_buffer, is_custom)

    def _sync_detail_rows(self) -> None:
        self._detail_rows.setVisible(
            not self.target_detail_row.isHidden() or not self.buffer_detail_row.isHidden()
        )
        self.updateGeometry()

    def _on_open_output(self) -> None:
        output_dir = self.output_path.output_dir()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(output_dir))

    # =========================================================================
    # CATEGORY SELECTION
    # =========================================================================

    def _on_select_categories(self) -> None:
        """Open the category dialog and apply user selection."""
        all_cats = self._all_categories or sorted(CATEGORY_DESCRIPTIONS.keys())
        selected, accepted = CategoryDialog.select_categories(
            self, all_cats, set(self._selected_categories),
        )
        if accepted:
            self._selected_categories = selected
            self._update_category_summary()

    def _update_category_summary(self) -> None:
        total = len(self._all_categories) or len(CATEGORY_DESCRIPTIONS)
        preset_name = detect_preset_name(set(self._selected_categories))
        self._category_summary.update_summary(
            self._selected_categories, total, preset_name,
        )

    def _on_load_categories(self) -> None:
        if not self.device_serial or self.presenter.is_loading_categories:
            return
        run_in_thread(self.presenter.load_categories, self.device_serial)

    # =========================================================================
    # DEVICE MANAGEMENT
    # =========================================================================

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        self._notify_readiness()

        if not serial:
            self._all_categories = []
            self._auto_loaded_serial = None
            self.status_message.emit("Please select a device.")
        else:
            self.status_message.emit(f"Selected device: {serial}.")
            should_auto_load = (
                serial != self._auto_loaded_serial
                or not self._selected_categories
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

        # Store device categories when loaded
        if self.presenter.categories and not self.presenter.is_loading_categories:
            self._all_categories = self.presenter.categories
            if not self._selected_categories:
                self._selected_categories = list(DEFAULT_ATRACE_CATEGORIES)
            self._update_category_summary()

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

    def _get_buffer_size_kb(self) -> int:
        text = self.buffer_combo.currentText()
        if text == "Custom":
            return int(self.custom_buffer.value())
        return int(text.replace(" KB", ""))

    def _get_target_app(self) -> Optional[str]:
        return resolve_target_package(
            self.target_combo.currentText(),
            self.custom_target.text(),
        )

    def start_capture(self) -> None:
        if not self.device_serial:
            self.error_message.emit("No device selected.")
            return

        selected = self._selected_categories
        if not selected:
            selected = list(DEFAULT_ATRACE_CATEGORIES)
            self.status_message.emit(
                "Using default categories (none selected)."
            )

        run_in_thread(
            self.presenter.run_request,
            SystraceRequest(
                device_serial=self.device_serial or "",
                categories=selected,
                duration_seconds=self._get_duration(),
                buffer_size_kb=self._get_buffer_size_kb(),
                app_name=self._get_target_app(),
                output_dir=self.output_path.output_dir(),
                auxiliary_options=self._auxiliary_options,
            ),
        )
        self.capture_started.emit(self._get_duration())

    def set_output_dir(self, output_dir: str) -> None:
        self.output_path.set_output_dir(output_dir)
