"""
Design Tokens
=============
Single source of truth for all visual constants.

Philosophy: Constraints liberate. A limited palette forces consistency.
"""


# =============================================================================
# COLORS
# Material Design inspired palette with semantic naming
# =============================================================================

class Colors:
    """Semantic color palette.

    Usage:
        from easy_tracer.ui.theme import Colors
        widget.setStyleSheet(f"background-color: {Colors.PRIMARY};")
    """

    # Brand / Primary — Bright blue (CC Switch style)
    PRIMARY = "#2196f3"
    PRIMARY_DARK = "#1976d2"
    PRIMARY_LIGHT = "#bbdefb"

    # Accent — Orange action highlight
    ACCENT = "#ff9800"
    ACCENT_DARK = "#f57c00"

    # Semantic Actions
    SUCCESS = "#2e7d32"         # Record button idle state
    SUCCESS_DARK = "#1b5e20"    # Record button border
    SUCCESS_LIGHT = "#43a047"   # Hover state

    DANGER = "#d32f2f"          # Stop button / errors
    DANGER_DARK = "#b71c1c"     # Stop button border
    DANGER_LIGHT = "#e57373"    # Hover state

    WARNING = "#f57c00"
    WARNING_DARK = "#e65100"

    INFO = "#0288d1"
    INFO_DARK = "#01579b"

    # Neutral Scale (grey)
    NEUTRAL_50 = "#fafafa"
    NEUTRAL_100 = "#f8f9fa"     # Light background (cool tone)
    NEUTRAL_200 = "#f0f2f5"
    NEUTRAL_300 = "#e4e7eb"     # Borders, dividers (softer)
    NEUTRAL_400 = "#bdbdbd"     # Disabled text
    NEUTRAL_500 = "#9e9e9e"     # Placeholder text
    NEUTRAL_600 = "#757575"     # Secondary text
    NEUTRAL_700 = "#616161"
    NEUTRAL_800 = "#424242"
    NEUTRAL_900 = "#212121"     # Primary text

    # Disabled State
    DISABLED_BG = "#b0bec5"     # Blue Grey 300
    DISABLED_TEXT = "#eceff1"   # Blue Grey 50
    DISABLED_BORDER = "#90a4ae" # Blue Grey 400

    # Surface Colors
    SURFACE = "#ffffff"
    SURFACE_VARIANT = "#f8f9fa"

    # Text on colored backgrounds
    ON_PRIMARY = "#ffffff"
    ON_SUCCESS = "#ffffff"
    ON_DANGER = "#ffffff"


# =============================================================================
# SPACING
# 4px base unit grid system
# =============================================================================

class Spacing:
    """Spacing constants based on 4px grid.

    Usage:
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)
    """

    NONE = 0
    XS = 2      # Tight: icon-text gap
    SM = 4      # Default element gap
    MD = 8      # Standard padding
    LG = 12     # Section padding
    XL = 16     # Panel padding
    XXL = 24    # Major section gaps


# =============================================================================
# TYPOGRAPHY
# Font sizes and weights
# =============================================================================

class Typography:
    """Typography constants.

    Note: We rely on system fonts for cross-platform consistency.
    Only specify sizes and weights.
    """

    # Sizes (pixels)
    SIZE_CAPTION = 11
    SIZE_BODY = 13
    SIZE_SUBTITLE = 14
    SIZE_TITLE = 16
    SIZE_HEADLINE = 20

    # Weights
    WEIGHT_NORMAL = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


# =============================================================================
# DIMENSIONS
# Component-specific size constants
# =============================================================================

class Dimensions:
    """Fixed dimensions for specific components."""

    # Buttons
    BUTTON_MIN_WIDTH = 80
    BUTTON_RECORD_WIDTH = 96
    BUTTON_PADDING_H = 12
    BUTTON_PADDING_V = 4
    BUTTON_BORDER_RADIUS = 8
    PRESET_BORDER_RADIUS = 16     # Pill shape for preset buttons

    # Inputs
    INPUT_MIN_HEIGHT = 28

    # Panels
    NAV_LIST_WIDTH = 150
    LOG_PANEL_MIN_HEIGHT = 240

    # Category Grid
    CATEGORY_ITEM_WIDTH = 140
    CATEGORY_ITEM_HEIGHT = 28
    CATEGORY_GRID_SPACING = 4

    # Window
    WINDOW_DEFAULT_WIDTH = 1100
    WINDOW_DEFAULT_HEIGHT = 780
