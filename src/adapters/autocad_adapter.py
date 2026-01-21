"""
AutoCAD adapter for multiCAD-MCP.

Implements CADInterface for AutoCAD using Windows COM.
Supports AutoCAD, ZWCAD, GstarCAD, and BricsCAD via factory pattern.

Refactored to use mixin classes for better organization and maintainability.
"""

import logging
from typing import Dict, Any

from core import (
    CADInterface,
    get_cad_config,
)
from .mixins import (
    UtilityMixin,
    ConnectionMixin,
    DrawingMixin,
    LayerMixin,
    FileMixin,
    ViewMixin,
    SelectionMixin,
    EntityMixin,
    ManipulationMixin,
    BlockMixin,
    ExportMixin,
    com_session,
    SelectionSetManager,
    com_safe,
)
from mcp_tools.constants import COLOR_MAP

logger = logging.getLogger(__name__)

# Export helpers for backward compatibility
__all__ = [
    "AutoCADAdapter",
    "com_session",
    "SelectionSetManager",
    "com_safe",
    "COLOR_MAP",
]


class AutoCADAdapter(
    UtilityMixin,
    ConnectionMixin,
    DrawingMixin,
    LayerMixin,
    FileMixin,
    ViewMixin,
    SelectionMixin,
    EntityMixin,
    ManipulationMixin,
    BlockMixin,
    ExportMixin,
    CADInterface,
):
    """Adapter for controlling AutoCAD via COM interface.

    Features:
    - Multi-CAD support (AutoCAD, ZWCAD, GstarCAD, BricsCAD) via cad_type parameter
    - Full drawing operations (lines, circles, arcs, polylines, dimensions, etc.)
    - Layer management (create, rename, delete, visibility control)
    - File operations (save, open, close, switch)
    - Entity selection and manipulation (move, rotate, scale, copy, paste)
    - Undo/redo support
    - Robust error handling with specific exception types

    Refactored using mixin classes for better organization:
    - UtilityMixin: Helper methods, converters, property access
    - ConnectionMixin: Connection management
    - DrawingMixin: Drawing operations
    - LayerMixin: Layer management
    - FileMixin: File operations
    - ViewMixin: View control, undo/redo
    - SelectionMixin: Entity selection
    - EntityMixin: Entity properties
    - ManipulationMixin: Entity manipulation
    - BlockMixin: Block operations
    - ExportMixin: Data extraction and Excel export
    """

    def __init__(self, cad_type: str = "autocad"):
        """Initialize AutoCAD adapter.

        Args:
            cad_type: Type of CAD (autocad, zwcad, gcad, bricscad)
        """
        self.cad_type = cad_type.lower()
        self.config = get_cad_config(self.cad_type)
        self.application = None
        self.document = None
        self._drawing_state: Dict[str, Any] = {
            "entities": [],
            "current_layer": "0",
        }
