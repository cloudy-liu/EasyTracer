"""
Stylesheet Generator
====================
QSS stylesheet generation from design tokens.

Philosophy: Generate styles programmatically for consistency.
All visual constants flow from tokens.py.
"""

from easy_tracer.assets import icon_path
from easy_tracer.ui.theme.tokens import Colors, Spacing, Dimensions, Typography


# =============================================================================
# RECORD BUTTON STYLES
# Extracted from main_window.py for centralized control
# =============================================================================

def record_button_qss(is_recording: bool) -> str:
    """Generate QSS for the global record/stop button.

    Args:
        is_recording: True for stop state (red), False for record state (green)

    Returns:
        Complete QPushButton stylesheet string
    """
    if is_recording:
        return f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: {Colors.ON_DANGER};
                font-weight: {600};
                padding: {Dimensions.BUTTON_PADDING_V}px {Dimensions.BUTTON_PADDING_H}px;
                border: 1px solid {Colors.DANGER_DARK};
                border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.DANGER_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {Colors.DANGER_DARK};
            }}
            QPushButton:disabled {{
                background-color: {Colors.DISABLED_BG};
                color: {Colors.DISABLED_TEXT};
                border: 1px solid {Colors.DISABLED_BORDER};
            }}
        """

    return f"""
        QPushButton {{
            background-color: {Colors.SUCCESS};
            color: {Colors.ON_SUCCESS};
            font-weight: {600};
            padding: {Dimensions.BUTTON_PADDING_V}px {Dimensions.BUTTON_PADDING_H}px;
            border: 1px solid {Colors.SUCCESS_DARK};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.SUCCESS_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {Colors.SUCCESS_DARK};
        }}
        QPushButton:disabled {{
            background-color: {Colors.DISABLED_BG};
            color: {Colors.DISABLED_TEXT};
            border: 1px solid {Colors.DISABLED_BORDER};
        }}
    """


# =============================================================================
# GLOBAL APPLICATION STYLESHEET
# Applied to QApplication for consistent base styling
# =============================================================================

def generate_app_stylesheet() -> str:
    """Generate the global application stylesheet.

    Returns:
        Complete QSS string to apply to QApplication
    """
    combo_arrow = icon_path("chevron-down")
    check_icon = icon_path("check-white")
    combo_arrow_url = str(combo_arrow).replace("\\", "/") if combo_arrow else ""
    check_icon_url = str(check_icon).replace("\\", "/") if check_icon else ""

    return f"""
        /* ===================================================================
         * BASE STYLES
         * =================================================================== */

        QWidget {{
            font-family: {Typography.FONT_UI};
            font-size: {Typography.SIZE_BODY}px;
            color: {Colors.NEUTRAL_900};
        }}

        /* ===================================================================
         * GROUP BOX
         * =================================================================== */

        QGroupBox {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            font-weight: 600;
            margin-top: 14px;
            padding: {Spacing.LG}px {Spacing.XL}px {Spacing.XL}px {Spacing.XL}px;
            padding-top: {Spacing.XL}px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: {Spacing.LG}px;
            padding: 0 {Spacing.SM}px;
            color: {Colors.NEUTRAL_700};
            background-color: {Colors.SURFACE};
        }}

        /* ===================================================================
         * BUTTONS - Default Style
         * =================================================================== */

        QPushButton {{
            padding: {Spacing.SM}px {Spacing.MD}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            min-height: 24px;
            font-weight: 500;
        }}

        QPushButton:hover {{
            background-color: {Colors.NEUTRAL_100};
            border-color: {Colors.NEUTRAL_400};
        }}

        QPushButton:pressed {{
            background-color: {Colors.NEUTRAL_200};
        }}

        QPushButton:disabled {{
            background-color: {Colors.NEUTRAL_100};
            color: {Colors.NEUTRAL_400};
            border-color: {Colors.NEUTRAL_200};
        }}

        QPushButton:focus {{
            border-color: {Colors.PRIMARY};
            outline: none;
        }}

        QToolButton {{
            padding: {Spacing.SM}px {Spacing.MD}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
        }}

        QToolButton:hover {{
            background-color: {Colors.NEUTRAL_100};
            border-color: {Colors.NEUTRAL_400};
        }}

        /* ===================================================================
         * LINE EDIT / INPUT FIELDS
         * =================================================================== */

        QLineEdit {{
            padding: {Spacing.SM}px {Spacing.MD}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            selection-background-color: {Colors.PRIMARY_LIGHT};
        }}

        QLineEdit:hover {{
            border-color: {Colors.NEUTRAL_400};
        }}

        QLineEdit:focus {{
            border-color: {Colors.PRIMARY};
            outline: none;
        }}

        QLineEdit:disabled {{
            background-color: {Colors.NEUTRAL_100};
            color: {Colors.NEUTRAL_500};
        }}

        QLineEdit:read-only {{
            background-color: {Colors.NEUTRAL_100};
            color: {Colors.NEUTRAL_600};
            border: 1px dashed {Colors.NEUTRAL_300};
        }}

        QLineEdit:read-only:hover {{
            border-color: {Colors.NEUTRAL_400};
        }}

        /* ===================================================================
         * COMBO BOX
         * =================================================================== */

        QComboBox {{
            padding: {Spacing.SM}px 28px {Spacing.SM}px {Spacing.MD}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            min-height: 28px;
        }}

        QComboBox:hover {{
            border-color: {Colors.NEUTRAL_400};
        }}

        QComboBox:focus {{
            border-color: {Colors.PRIMARY};
        }}

        QComboBox::drop-down {{
            subcontrol-position: right center;
            subcontrol-origin: padding;
            width: 24px;
            border: none;
            padding-right: {Spacing.MD}px;
        }}

        QComboBox::down-arrow {{
            image: url({combo_arrow_url});
            width: 10px;
            height: 6px;
        }}

        QComboBox QAbstractItemView {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            selection-background-color: {Colors.PRIMARY_LIGHT};
            padding: {Spacing.SM}px;
            outline: none;
        }}

        QComboBox QAbstractItemView::item {{
            padding: {Spacing.SM}px {Spacing.MD}px;
            min-height: 24px;
        }}

        QComboBox QAbstractItemView::item:hover {{
            background-color: {Colors.NEUTRAL_100};
        }}

        QComboBox QAbstractItemView::item:selected {{
            background-color: {Colors.PRIMARY_LIGHT};
            color: {Colors.NEUTRAL_900};
        }}

        /* ===================================================================
         * SPIN BOX
         * =================================================================== */

        QSpinBox {{
            padding: {Spacing.SM}px {Spacing.MD}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            min-height: 28px;
        }}

        QSpinBox:hover {{
            border-color: {Colors.NEUTRAL_400};
        }}

        QSpinBox:focus {{
            border-color: {Colors.PRIMARY};
        }}

        /* ===================================================================
         * CHECK BOX
         * =================================================================== */

        QCheckBox {{
            spacing: {Spacing.SM}px;
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {Colors.NEUTRAL_400};
            border-radius: 4px;
            background-color: {Colors.SURFACE};
        }}

        QCheckBox::indicator:hover {{
            border-color: {Colors.PRIMARY};
            background-color: #e3f2fd;
        }}

        QCheckBox::indicator:checked {{
            background-color: {Colors.PRIMARY};
            border-color: {Colors.PRIMARY};
            image: url({check_icon_url});
        }}

        QCheckBox::indicator:disabled {{
            background-color: {Colors.NEUTRAL_100};
            border-color: {Colors.NEUTRAL_300};
        }}

        /* ===================================================================
         * RADIO BUTTON
         * =================================================================== */

        QRadioButton {{
            spacing: {Spacing.SM}px;
        }}

        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {Colors.NEUTRAL_400};
            border-radius: 8px;
            background-color: {Colors.SURFACE};
        }}

        QRadioButton::indicator:hover {{
            border-color: {Colors.PRIMARY};
        }}

        QRadioButton::indicator:checked {{
            background-color: {Colors.PRIMARY};
            border-color: {Colors.PRIMARY};
        }}

        /* ===================================================================
         * TAB WIDGET
         * =================================================================== */

        QTabWidget::pane {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
        }}

        QTabBar::tab {{
            padding: {Spacing.MD}px {Spacing.XL}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-bottom: none;
            border-top-left-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            border-top-right-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.NEUTRAL_100};
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {Colors.SURFACE};
            border-bottom: 1px solid {Colors.SURFACE};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {Colors.NEUTRAL_200};
        }}

        /* ===================================================================
         * LIST WIDGET
         * =================================================================== */

        QListWidget {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            outline: none;
        }}

        QListWidget::item {{
            padding: {Spacing.SM}px;
        }}

        QListWidget::item:hover {{
            background-color: {Colors.NEUTRAL_100};
        }}

        QListWidget::item:selected {{
            background-color: #e3f2fd;
            color: {Colors.NEUTRAL_900};
            border: 1px solid {Colors.PRIMARY};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
        }}

        /* ===================================================================
         * TREE WIDGET
         * =================================================================== */

        QTreeWidget {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            outline: none;
        }}

        QTreeWidget::item {{
            padding: {Spacing.XS}px;
        }}

        QTreeWidget::item:hover {{
            background-color: {Colors.NEUTRAL_100};
        }}

        QTreeWidget::item:selected {{
            background-color: #e3f2fd;
            color: {Colors.NEUTRAL_900};
            border: 1px solid {Colors.PRIMARY};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
        }}

        /* ===================================================================
         * TEXT EDIT (Log Panel)
         * =================================================================== */

        QTextEdit {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            selection-background-color: {Colors.PRIMARY_LIGHT};
        }}

        QTableWidget {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            gridline-color: {Colors.NEUTRAL_300};
            selection-background-color: #e3f2fd;
            selection-color: {Colors.NEUTRAL_900};
        }}

        QHeaderView::section {{
            background-color: {Colors.NEUTRAL_100};
            color: {Colors.NEUTRAL_700};
            padding: {Spacing.MD}px;
            border: none;
            border-bottom: 1px solid {Colors.NEUTRAL_300};
            font-weight: 600;
        }}

        /* ===================================================================
         * SCROLL BAR
         * =================================================================== */

        QScrollBar:vertical {{
            border: none;
            background-color: {Colors.NEUTRAL_100};
            width: 10px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {Colors.NEUTRAL_400};
            min-height: 30px;
            border-radius: 5px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {Colors.NEUTRAL_500};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            border: none;
            background-color: {Colors.NEUTRAL_100};
            height: 10px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {Colors.NEUTRAL_400};
            min-width: 30px;
            border-radius: 5px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {Colors.NEUTRAL_500};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        /* ===================================================================
         * SPLITTER
         * =================================================================== */

        QSplitter::handle {{
            background-color: {Colors.NEUTRAL_200};
        }}

        QSplitter::handle:hover {{
            background-color: {Colors.NEUTRAL_400};
        }}

        /* ===================================================================
         * STATUS BAR
         * =================================================================== */

        QStatusBar {{
            background-color: {Colors.NEUTRAL_100};
            border-top: 1px solid {Colors.NEUTRAL_300};
            padding: 2px {Spacing.MD}px;
        }}

        QStatusBar::item {{
            border: none;
        }}

        /* ===================================================================
         * PROGRESS BAR
         * =================================================================== */

        QProgressBar {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.NEUTRAL_100};
            text-align: center;
            min-height: 16px;
        }}

        QProgressBar::chunk {{
            background-color: {Colors.PRIMARY};
            border-radius: 3px;
        }}

        /* ===================================================================
         * TOOL TIP
         * =================================================================== */

        QToolTip {{
            background-color: {Colors.NEUTRAL_800};
            color: {Colors.NEUTRAL_50};
            border: none;
            padding: {Spacing.SM}px {Spacing.MD}px;
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
        }}
    """


# =============================================================================
# COMPONENT-SPECIFIC STYLES
# =============================================================================

def preset_button_qss(selected: bool) -> str:
    """Generate QSS for preset pill buttons.

    Args:
        selected: Whether this preset is currently active

    Returns:
        QPushButton stylesheet string
    """
    if selected:
        return f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: {Colors.ON_PRIMARY};
                border: 1px solid {Colors.PRIMARY_DARK};
                border-radius: {Dimensions.PRESET_BORDER_RADIUS}px;
                padding: {Spacing.SM}px {Spacing.LG}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """

    return f"""
        QPushButton {{
            background-color: {Colors.SURFACE};
            color: {Colors.NEUTRAL_700};
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.PRESET_BORDER_RADIUS}px;
            padding: {Spacing.SM}px {Spacing.LG}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.NEUTRAL_100};
            border-color: {Colors.PRIMARY};
        }}
    """


def category_group_header_qss(expanded: bool) -> str:
    """Generate QSS for category group header buttons.

    Args:
        expanded: Whether the group is currently expanded

    Returns:
        QPushButton stylesheet string
    """
    return f"""
        QPushButton {{
            background-color: {Colors.NEUTRAL_100 if expanded else Colors.SURFACE};
            color: {Colors.NEUTRAL_800};
            border: none;
            border-bottom: 1px solid {Colors.NEUTRAL_200};
            padding: {Spacing.MD}px;
            text-align: left;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.NEUTRAL_200};
        }}
    """


def selection_counter_qss() -> str:
    """Generate QSS for the category selection counter badge."""
    return f"""
        QLabel {{
            background-color: {Colors.PRIMARY};
            color: {Colors.ON_PRIMARY};
            border-radius: 10px;
            padding: 2px 8px;
            font-weight: 600;
            font-size: 11px;
        }}
    """


# =============================================================================
# BANNER / CARD STYLES
# Reusable helpers for notice banners and result cards
# =============================================================================

def deprecation_banner_qss() -> str:
    """Generate QSS for deprecation warning banners."""
    return f"""
        QFrame {{
            background-color: #fff7ed;
            border: 1px solid #fed7aa;
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
        }}
        QFrame QLabel {{
            background: transparent;
            border: none;
            color: {Colors.WARNING_DARK};
        }}
    """


def info_card_qss() -> str:
    """Generate QSS for informational cards in sparse panels."""
    return f"""
        QFrame {{
            background-color: {Colors.NEUTRAL_50};
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
        }}
        QFrame QLabel {{
            background: transparent;
            border: none;
            color: {Colors.NEUTRAL_600};
        }}
    """


def result_card_qss() -> str:
    """Generate QSS for capture result summary cards."""
    return f"""
        QFrame {{
            background-color: #eef7ef;
            border: 1px solid #cfe6d2;
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
        }}
        QFrame QLabel {{
            background: transparent;
            border: none;
            color: {Colors.NEUTRAL_700};
        }}
    """
