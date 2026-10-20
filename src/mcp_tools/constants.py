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
    "bylayer": 256,  # Special value for entities to inherit layer color
}

# Special color constants
AC_BY_BLOCK = 0  # Color ByBlock
AC_BY_LAYER = 256  # Color ByLayer (for entities only)

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
COMMAND_EXECUTE_DELAY = 100
EXPORT_WRITE_DELAY = 1500
COM_INIT_TIMEOUT = 20000

# ========== CAD Window Search Terms ==========

CAD_WINDOW_SEARCH_TERMS = {
    "autocad": "Autodesk AutoCAD",
    "zwcad": "ZWCAD",
    "gcad": "GstarCAD",
    "bricscad": "BricsCAD",
}

# ========== Standard Layer Templates (AECO, AIA, MEP) ==========

LAYER_TEMPLATES = {
    "aeco": [
        {"name": "A-MURO-ESTR", "color": "red", "lineweight": 50, "description": "Muros portantes y elementos estructurales"},
        {"name": "A-TABI-PART", "color": "yellow", "lineweight": 30, "description": "Tabiquería y particiones interiores"},
        {"name": "A-CARP-EXTE", "color": "cyan", "lineweight": 18, "description": "Carpintería exterior y cerramientos vidriados"},
        {"name": "A-CARP-INTE", "color": "green", "lineweight": 18, "description": "Carpintería interior y abatimientos de puertas"},
        {"name": "A-MOBI-SANI", "color": "gray", "lineweight": 13, "description": "Mobiliario fijo y aparatos sanitarios"},
        {"name": "A-COTA-ALIN", "color": "white", "lineweight": 18, "description": "Líneas de cota, niveles y ejes de referencia"},
        {"name": "A-TEXT-ESTA", "color": "white", "lineweight": 25, "description": "Textos generales y nombres de estancias"},
        {"name": "A-PAVI-TRAM", "color": "light_gray", "lineweight": 9, "description": "Tramas de pavimento y sombreados"},
        {"name": "E-INST-ELEC", "color": "magenta", "lineweight": 25, "description": "Instalaciones eléctricas e iluminación"},
        {"name": "E-INST-FONT", "color": "blue", "lineweight": 25, "description": "Fontanería, saneamiento y climatización"},
    ],
    "aia": [
        {"name": "A-WALL-FULL", "color": "red", "lineweight": 50, "description": "Full height structural walls"},
        {"name": "A-WALL-PRTN", "color": "yellow", "lineweight": 30, "description": "Interior non-structural partitions"},
        {"name": "A-DOOR", "color": "green", "lineweight": 18, "description": "Doors and door swings"},
        {"name": "A-GLAZ", "color": "cyan", "lineweight": 18, "description": "Windows, storefronts and curtain walls"},
        {"name": "A-FLOR-FIXT", "color": "gray", "lineweight": 13, "description": "Plumbing fixtures and millwork"},
        {"name": "A-ANNO-DIMS", "color": "white", "lineweight": 18, "description": "Dimensions and stringers"},
        {"name": "A-ANNO-TEXT", "color": "white", "lineweight": 25, "description": "Room labels, notes and callouts"},
    ],
    "mep": [
        {"name": "M-HVAC-DUCT", "color": "cyan", "lineweight": 35, "description": "HVAC ductwork and dampers"},
        {"name": "P-PLUM-PIPE", "color": "blue", "lineweight": 35, "description": "Plumbing and drainage pipes"},
        {"name": "E-POWR-CBLT", "color": "magenta", "lineweight": 35, "description": "Power circuits and cable trays"},
        {"name": "F-PROT-EQPM", "color": "red", "lineweight": 35, "description": "Fire protection sprinklers and alarms"},
    ]
}

# Aliases for templates
LAYER_TEMPLATE_ALIASES = {
    "cte": "aeco",
    "arquitectura": "aeco",
    "edificacion": "aeco",
    "standard": "aeco",
    "us": "aia",
    "instalaciones": "mep",
}

