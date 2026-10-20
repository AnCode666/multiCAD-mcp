"""
AutoCAD adapter for multiCAD-MCP.

Implements CADInterface for AutoCAD using Windows COM.
Supports AutoCAD, ZWCAD, GstarCAD, and BricsCAD via factory pattern.

Refactored to use mixin classes for better organization and maintainability.
"""

import threading
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
    LayoutMixin,
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
    LayoutMixin,
    CADInterface,
):
    """Adapter for controlling AutoCAD via COM interface.

    [... docstring truncated for brevity ...]
    """

    def __init__(self, cad_type: str = "autocad"):
        """Initialize AutoCAD adapter.

        Args:
            cad_type: Type of CAD (autocad, zwcad, gcad, bricscad)
        """
        self.cad_type = cad_type.lower()
        self.config = get_cad_config(self.cad_type)

        # Thread-local storage for COM objects to prevent cross-thread RPC errors
        self._local = threading.local()

        self._drawing_state: Dict[str, Any] = {
            "entities": [],
            "current_layer": "0",
        }

    @property
    def application(self) -> Any:
        """Get the thread-local application COM proxy."""
        return getattr(self._local, "application", None)

    @application.setter
    def application(self, value: Any):
        """Set the thread-local application COM proxy."""
        self._local.application = value

    @property
    def document(self) -> Any:
        """Get the thread-local document COM proxy."""
        return getattr(self._local, "document", None)

    @document.setter
    def document(self, value: Any):
        """Set the thread-local document COM proxy."""
        self._local.document = value
