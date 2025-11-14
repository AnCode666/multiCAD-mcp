"""
Constants and configuration for multiCAD-MCP server.

Centralized storage for colors, selection set names, timing, and other constants.
"""

# ========== AutoCAD Color Index (ACI) ==========

COLOR_MAP = {
    "black": 0,
    "red": 1,
    "yellow": 2,
    "green": 3,
    "cyan": 4,
    "blue": 5,
    "magenta": 6,
    "white": 7,
    "gray": 8,
    "light_gray": 252,
    "dark_gray": 251,
    "orange": 30,
}

# ========== Selection Set Names ==========

SS_COLOR_SELECT = "_color_select_ss"
SS_LAYER_SELECT = "_layer_select_ss"
SS_TYPE_SELECT = "_type_select_ss"
SS_COPY = "_copy_ss"
SS_SELECTION_GET = "_selection_get"

# ========== AutoCAD Window Classes ==========

AUTOCAD_WINDOW_CLASSES = [
    "AutoCAD Main Window",
    "ACAD:Main",
    "AutoCADMainFrame",
]

# ========== Selection Set Modes ==========

SELECTION_SET_IMPLIED = 3  # acSelectionSetImplied

# ========== DXF Filter Codes ==========

DXF_LAYER = 8
DXF_COLOR = 62

# ========== Timing Constants (milliseconds) ==========

CLIPBOARD_DELAY = 300
CLIPBOARD_STABILITY_DELAY = 500
CLICK_DELAY = 50
CLICK_HOLD_DELAY = 20
