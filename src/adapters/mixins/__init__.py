"""
Mixins package for AutoCAD adapter.

Exports all mixin classes for use in the main AutoCADAdapter.
"""

from typing import Protocol, Any, List, runtime_checkable

from .utility_mixin import UtilityMixin, com_session, SelectionSetManager, com_safe
from .connection_mixin import ConnectionMixin
from .drawing_mixin import DrawingMixin
from .layer_mixin import LayerMixin
from .file_mixin import FileMixin
from .view_mixin import ViewMixin
from .selection_mixin import SelectionMixin
from .entity_mixin import EntityMixin
from .manipulation_mixin import ManipulationMixin
from .block_mixin import BlockMixin
from .export_mixin import ExportMixin


@runtime_checkable
class CADAdapterProtocol(Protocol):
    """
    Protocol defining the interface that mixins expect from the base adapter.

    This ensures type safety when mixins call methods from the main adapter class.
    """

    # Connection state
    application: Any
    document: Any
    is_connected: bool
    _drawing_state: dict
    cad_type: str
    config: dict

    # Connection methods
    def _validate_connection(self) -> None:
        """Validate CAD connection is active."""
        ...

    def _get_application(self, operation: str = "operation") -> Any:
        """Get the CAD application COM object."""
        ...

    def _get_document(self, operation: str = "operation") -> Any:
        """Get the current document COM object."""
        ...

    # Coordinate and conversion methods
    def _to_variant_array(self, point: Any) -> Any:
        """Convert Python tuple to COM VARIANT array."""
        ...

    def _to_radians(self, degrees: float) -> float:
        """Convert degrees to radians."""
        ...

    def _objects_to_variant_array(self, objects: List[Any]) -> Any:
        """Convert list of COM objects to VARIANT array."""
        ...

    # Selection set methods
    def _delete_selection_set(self, document: Any, name: str) -> None:
        """Delete a selection set by name."""
        ...

    # View methods
    def refresh_view(self) -> bool:
        """Refresh the CAD view."""
        ...

    def _simulate_autocad_click(self) -> bool:
        """Simulate mouse click to refresh view."""
        ...

    # Color and lineweight
    def _get_color_index(self, color_name: str) -> int:
        """Get AutoCAD Color Index from color name."""
        ...

    def validate_lineweight(self, weight: int) -> int:
        """Validate and return a valid lineweight value."""
        ...

    def _wait_for(
        self, condition: Any, timeout: float = 20.0, interval: float = 0.1
    ) -> bool:
        """Wait for a condition to be met."""
        ...


__all__ = [
    # Protocol
    "CADAdapterProtocol",
    # Mixin classes
    "UtilityMixin",
    "ConnectionMixin",
    "DrawingMixin",
    "LayerMixin",
    "FileMixin",
    "ViewMixin",
    "SelectionMixin",
    "EntityMixin",
    "ManipulationMixin",
    "BlockMixin",
    "ExportMixin",
    # Helper classes and functions
    "com_session",
    "SelectionSetManager",
    "com_safe",
]
