"""
Stylesheet Generator
====================
QSS stylesheet generation from design tokens.

Philosophy: Generate styles programmatically for consistency.
All visual constants flow from tokens.py.
"""

from easy_tracer.ui.theme.tokens import Colors, Spacing, Dimensions


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
    return f"""
        /* ===================================================================
         * BASE STYLES
         * =================================================================== */

        QWidget {{
            font-size: 13px;
        }}

        /* ===================================================================
         * GROUP BOX
         * =================================================================== */

        QGroupBox {{
            font-weight: 600;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            margin-top: 12px;
            padding-top: 8px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 {Spacing.SM}px;
            color: {Colors.NEUTRAL_700};
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

        /* ===================================================================
         * COMBO BOX
         * =================================================================== */

        QComboBox {{
            padding: {Spacing.SM}px {Spacing.MD}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
            min-height: 24px;
        }}

        QComboBox:hover {{
            border-color: {Colors.NEUTRAL_400};
        }}

        QComboBox:focus {{
            border-color: {Colors.PRIMARY};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox QAbstractItemView {{
            border: 1px solid {Colors.NEUTRAL_300};
            background-color: {Colors.SURFACE};
            selection-background-color: {Colors.PRIMARY_LIGHT};
        }}

        /* ===================================================================
         * SPIN BOX
         * =================================================================== */

        QSpinBox {{
            padding: {Spacing.SM}px;
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.SURFACE};
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
            padding: {Spacing.MD}px {Spacing.LG}px;
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
            background-color: {Colors.PRIMARY_LIGHT};
            color: {Colors.ON_PRIMARY};
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
            background-color: {Colors.PRIMARY_LIGHT};
            color: {Colors.ON_PRIMARY};
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
        }}

        /* ===================================================================
         * PROGRESS BAR
         * =================================================================== */

        QProgressBar {{
            border: 1px solid {Colors.NEUTRAL_300};
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            background-color: {Colors.NEUTRAL_100};
            text-align: center;
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
    """Generate QSS for preset selection buttons (radio-style).

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
                border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
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
            border-radius: {Dimensions.BUTTON_BORDER_RADIUS}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
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
