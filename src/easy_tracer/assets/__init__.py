"""
Assets Package
==============
Static resources: icons, images, etc.

Icons designed for 24x24 display in navigation list.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtWidgets import QStyle, QApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QSize, Qt

ASSETS_DIR = Path(__file__).parent
ICONS_DIR = ASSETS_DIR / "icons"

# Fallback mapping to Qt standard icons
_FALLBACK_ICONS = {
    "device": QStyle.StandardPixmap.SP_ComputerIcon,
    "systrace": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    "perfetto": QStyle.StandardPixmap.SP_DialogApplyButton,
    "simpleperf": QStyle.StandardPixmap.SP_ArrowUp,
    "traceview": QStyle.StandardPixmap.SP_FileDialogInfoView,
    "combo": QStyle.StandardPixmap.SP_BrowserReload,
    "settings": QStyle.StandardPixmap.SP_FileDialogContentsView,
    "about": QStyle.StandardPixmap.SP_MessageBoxInformation,
}


def icon_path(name: str) -> Optional[Path]:
    """Get absolute path to an icon file (SVG or PNG).

    Args:
        name: Icon name without extension (e.g., 'perfetto')

    Returns:
        Path to the icon file, or None if not found
    """
    for ext in ("svg", "png"):
        p = ICONS_DIR / f"{name}.{ext}"
        if p.exists():
            return p
    return None


def load_icon(name: str, size: int = 24) -> QIcon:
    """Load an icon with SVG/PNG support, fallback to system icon.

    Args:
        name: Icon name without extension
        size: Icon size in pixels

    Returns:
        QIcon instance (custom or system fallback)
    """
    path = icon_path(name)

    if path is not None:
        if path.suffix == ".svg":
            renderer = QSvgRenderer(str(path))
            if renderer.isValid():
                pixmap = QPixmap(QSize(size, size))
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                return QIcon(pixmap)
        else:
            # PNG or other raster format
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    QSize(size, size),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                return QIcon(scaled)

    # Fallback to system icon
    fallback = _FALLBACK_ICONS.get(name)
    if fallback is not None:
        app = QApplication.instance()
        if app:
            return app.style().standardIcon(fallback)

    return QIcon()

