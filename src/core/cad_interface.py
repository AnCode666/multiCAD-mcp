"""
Abstract base class for CAD application adapters.
Defines the common interface that all CAD adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum


class LineWeight(Enum):
    """Standard CAD line weights."""

    THIN = 0
    THIN_1 = 5
    THIN_2 = 9
    THIN_3 = 13
    THIN_4 = 15
    THIN_5 = 18
    THIN_6 = 20
    MEDIUM_1 = 25
    MEDIUM_2 = 30
    MEDIUM_3 = 35
    MEDIUM_4 = 40
    MEDIUM_5 = 50
    THICK_1 = 53
    THICK_2 = 60
    THICK_3 = 70
    THICK_4 = 80
    THICK_5 = 90
    THICK_6 = 100
    THICK_7 = 106
    THICK_8 = 120
    THICK_9 = 140
    THICK_10 = 158
    THICK_11 = 200
    THICK_12 = 211

    @staticmethod
    def is_valid(weight: int) -> bool:
        """Check if weight is valid."""
        return weight in [w.value for w in LineWeight]


class Color(Enum):
    """Standard CAD colors."""

    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    CYAN = (0, 255, 255)
    WHITE = (255, 255, 255)
    GRAY = (128, 128, 128)
    LIGHT_GRAY = (192, 192, 192)
    DARK_GRAY = (64, 64, 64)
    ORANGE = (255, 165, 0)


Coordinate = Tuple[float, float] | Tuple[float, float, float]
Point = Tuple[float, float, float]  # Always 3D internally


class CADInterface(ABC):
    """Abstract interface for CAD application adapters."""

    # ========== Connection Management ==========

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to a CAD application.
        Try to get existing instance first, then start new if needed.

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from CAD application.

        Returns:
            bool: True if disconnection successful
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to CAD.

        Returns:
            bool: True if connected
        """
        pass

    # ========== Drawing Operations ==========

    @abstractmethod
    def draw_line(
        self,
        start: Coordinate,
        end: Coordinate,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """
        Draw a line from start to end point.

        Args:
            start: Start point (x, y) or (x, y, z)
            end: End point (x, y) or (x, y, z)
            layer: Layer name
            color: Color name or index
            lineweight: Line weight value
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            str: Entity handle/ID
        """
        pass

    @abstractmethod
    def draw_circle(
        self,
        center: Coordinate,
        radius: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """
        Draw a circle.

        Args:
            center: Center point (x, y) or (x, y, z)
            radius: Circle radius
            layer: Layer name
            color: Color name or index
            lineweight: Line weight value
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            str: Entity handle/ID
        """
        pass

    @abstractmethod
    def draw_arc(
        self,
        center: Coordinate,
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """
        Draw an arc.

        Args:
            center: Center point
            radius: Arc radius
            start_angle: Start angle in degrees
            end_angle: End angle in degrees
            layer: Layer name
            color: Color name or index
            lineweight: Line weight value
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            str: Entity handle/ID
        """
        pass

    @abstractmethod
    def draw_rectangle(
        self,
        corner1: Coordinate,
        corner2: Coordinate,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """
        Draw a rectangle from two opposite corners.

        Args:
            corner1: First corner (x, y)
            corner2: Opposite corner (x, y)
            layer: Layer name
            color: Color name or index
            lineweight: Line weight value
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            str: Entity handle/ID (may be multiple for rectangle polyline)
        """
        pass

    @abstractmethod
    def draw_polyline(
        self,
        points: List[Coordinate],
        closed: bool = False,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """
        Draw a polyline through multiple points.

        Args:
            points: List of points
            closed: Whether to close the polyline
            layer: Layer name
            color: Color name or index
            lineweight: Line weight value
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            str: Entity handle/ID
        """
        pass

    @abstractmethod
    def draw_ellipse(
        self,
        center: Coordinate,
        major_axis_end: Coordinate,
        minor_axis_ratio: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
    ) -> str:
        """
        Draw an ellipse.

        Args:
            center: Center point
            major_axis_end: End of major axis vector
            minor_axis_ratio: Ratio of minor to major axis (0-1)
            layer: Layer name
            color: Color name or index
            lineweight: Line weight value

        Returns:
            str: Entity handle/ID
        """
        pass

    @abstractmethod
    def draw_text(
        self,
        position: Coordinate,
        text: str,
        height: float = 2.5,
        rotation: float = 0.0,
        layer: str = "0",
        color: str | int = "white",
        _skip_refresh: bool = False,
    ) -> str:
        """
        Add text to the drawing.

        Args:
            position: Text position
            text: Text content
            height: Text height
            rotation: Rotation angle in degrees
            layer: Layer name
            color: Color name or index
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            str: Entity handle/ID
        """
        pass

    @abstractmethod
    def draw_hatch(
        self,
        boundary_points: List[Coordinate],
        pattern: str = "SOLID",
        scale: float = 1.0,
        angle: float = 0.0,
        color: str | int = "white",
        layer: str = "0",
    ) -> str:
        """
        Create a hatch (filled area) with pattern.

        Args:
            boundary_points: Points defining the boundary
            pattern: Hatch pattern name (SOLID, ANGLE, CROSS, etc.)
            scale: Pattern scale
            angle: Pattern angle in degrees
            color: Fill color
            layer: Layer name

        Returns:
            str: Entity handle/ID
        """
        pass

    @abstractmethod
    def add_dimension(
        self,
        start: Coordinate,
        end: Coordinate,
        text_position: Optional[Coordinate] = None,
        text: Optional[str] = None,
        layer: str = "0",
        color: str | int = "white",
        offset: float = 10.0,
    ) -> str:
        """
        Add a dimension annotation.

        Args:
            start: Start point
            end: End point
            text_position: Optional position for dimension text
            text: Optional custom text
            layer: Layer name
            color: Color name or index
            offset: Distance to offset the dimension line from the edge (default: 10.0)

        Returns:
            str: Entity handle/ID
        """
        pass

    # ========== Layer Management ==========

    @abstractmethod
    def create_layer(
        self,
        name: str,
        color: str | int = "white",
        lineweight: int = 0,
    ) -> bool:
        """
        Create a new layer.

        Args:
            name: Layer name
            color: Layer color
            lineweight: Layer lineweight

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def set_current_layer(self, name: str) -> bool:
        """
        Set the active/current layer.

        Args:
            name: Layer name

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def get_current_layer(self) -> str:
        """
        Get the name of the current active layer.

        Returns:
            str: Layer name
        """
        pass

    @abstractmethod
    def list_layers(self) -> List[str]:
        """
        Get list of all layers in the drawing.

        Returns:
            List[str]: Layer names
        """
        pass

    @abstractmethod
    def rename_layer(self, old_name: str, new_name: str) -> bool:
        """
        Rename an existing layer.

        Args:
            old_name: Current layer name
            new_name: New layer name

        Returns:
            bool: True if successful

        Raises:
            LayerError: If layer not found or cannot be renamed
        """
        pass

    @abstractmethod
    def delete_layer(self, name: str) -> bool:
        """
        Delete a layer from the drawing.
        Cannot delete layer 0 (standard layer).

        Args:
            name: Layer name to delete

        Returns:
            bool: True if successful

        Raises:
            LayerError: If layer not found, is in use, or cannot be deleted
        """
        pass

    @abstractmethod
    def turn_layer_on(self, name: str) -> bool:
        """
        Turn on (make visible) a layer.

        Args:
            name: Layer name

        Returns:
            bool: True if successful

        Raises:
            LayerError: If layer not found
        """
        pass

    @abstractmethod
    def turn_layer_off(self, name: str) -> bool:
        """
        Turn off (hide) a layer.

        Args:
            name: Layer name

        Returns:
            bool: True if successful

        Raises:
            LayerError: If layer not found
        """
        pass

    @abstractmethod
    def is_layer_on(self, name: str) -> bool:
        """
        Check if a layer is visible (turned on).

        Args:
            name: Layer name

        Returns:
            bool: True if layer is on, False if off

        Raises:
            LayerError: If layer not found
        """
        pass

    # ========== File Operations ==========

    @abstractmethod
    def save_drawing(
        self, filepath: str = "", filename: str = "", format: str = "dwg"
    ) -> bool:
        """
        Save the current drawing to a file.

        Args:
            filepath: Full path where to save (e.g., 'C:/drawings/myfile.dwg')
            filename: Just the filename (e.g., 'myfile.dwg'). Uses configured output directory
            format: File format (dwg, dxf, etc.). Default: dwg

        Returns:
            bool: True if successful

        Note:
            - If both filepath and filename provided, filepath takes precedence
            - If only filename provided, saved to config output directory
            - If neither provided, uses current document name or generates timestamp-based name
        """
        pass

    @abstractmethod
    def open_drawing(self, filepath: str) -> bool:
        """
        Open an existing drawing file.

        Args:
            filepath: Path to the drawing file

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def new_drawing(self) -> bool:
        """
        Create a new blank drawing.

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def close_drawing(self, save_changes: bool = False) -> bool:
        """
        Close the current drawing.

        Args:
            save_changes: Whether to save changes before closing (default: False)

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def get_open_drawings(self) -> list:
        """
        Get list of all open drawing filenames.

        Returns:
            list: Drawing names (e.g., ["drawing1.dwg", "drawing2.dwg"])
        """
        pass

    @abstractmethod
    def switch_drawing(self, drawing_name: str) -> bool:
        """
        Switch to a different open drawing.

        Args:
            drawing_name: Name of the drawing to switch to

        Returns:
            bool: True if successful
        """
        pass

    # ========== View Management ==========

    @abstractmethod
    def zoom_extents(self) -> bool:
        """
        Zoom to show all entities in view.

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def refresh_view(self) -> bool:
        """
        Refresh/redraw the current view.

        Returns:
            bool: True if successful
        """
        pass

    # ========== Entity Management ==========

    @abstractmethod
    def delete_entity(self, handle: str) -> bool:
        """
        Delete an entity by its handle.

        Args:
            handle: Entity handle/ID

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def get_entity_properties(self, handle: str) -> Dict[str, Any]:
        """
        Get properties of an entity.

        Args:
            handle: Entity handle/ID

        Returns:
            Dict: Entity properties
        """
        pass

    @abstractmethod
    def set_entity_properties(self, handle: str, properties: Dict[str, Any]) -> bool:
        """
        Modify entity properties.

        Args:
            handle: Entity handle/ID
            properties: Properties to set

        Returns:
            bool: True if successful
        """
        pass

    # ========== Entity Selection ==========

    @abstractmethod
    def select_by_color(self, color: str | int) -> List[str]:
        """
        Select all entities of a specific color.

        Args:
            color: Color name or index

        Returns:
            List[str]: List of entity handles
        """
        pass

    @abstractmethod
    def select_by_layer(self, layer_name: str) -> List[str]:
        """
        Select all entities on a specific layer.

        Args:
            layer_name: Layer name

        Returns:
            List[str]: List of entity handles
        """
        pass

    @abstractmethod
    def select_by_type(self, entity_type: str) -> List[str]:
        """
        Select all entities of a specific type.

        Args:
            entity_type: Entity type (line, circle, etc.)

        Returns:
            List[str]: List of entity handles
        """
        pass

    @abstractmethod
    def get_selected_entities(self) -> List[str]:
        """
        Get list of currently selected entities.

        Returns:
            List[str]: List of entity handles
        """
        pass

    @abstractmethod
    def clear_selection(self) -> bool:
        """
        Clear current selection.

        Returns:
            bool: True if successful
        """
        pass

    # ========== Entity Manipulation ==========

    @abstractmethod
    def move_entities(
        self, handles: List[str], offset_x: float, offset_y: float
    ) -> bool:
        """
        Move entities by an offset.

        Args:
            handles: List of entity handles
            offset_x: X offset
            offset_y: Y offset

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def rotate_entities(
        self, handles: List[str], center_x: float, center_y: float, angle: float
    ) -> bool:
        """
        Rotate entities around a point.

        Args:
            handles: List of entity handles
            center_x: Rotation center X
            center_y: Rotation center Y
            angle: Rotation angle in degrees

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def scale_entities(
        self, handles: List[str], center_x: float, center_y: float, scale_factor: float
    ) -> bool:
        """
        Scale entities around a point.

        Args:
            handles: List of entity handles
            center_x: Scale center X
            center_y: Scale center Y
            scale_factor: Scale factor

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def copy_entities(self, handles: List[str]) -> bool:
        """
        Copy entities to clipboard.

        Args:
            handles: List of entity handles

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def paste_entities(self, base_point_x: float, base_point_y: float) -> List[str]:
        """
        Paste entities from clipboard.

        Args:
            base_point_x: Base point X for pasting
            base_point_y: Base point Y for pasting

        Returns:
            List[str]: Handles of pasted entities
        """
        pass

    @abstractmethod
    def change_entity_color(self, handles: List[str], color: str | int) -> bool:
        """
        Change color of entities.

        Args:
            handles: List of entity handles
            color: Color name or index

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def change_entity_layer(self, handles: List[str], layer_name: str) -> bool:
        """
        Move entities to a different layer.

        Args:
            handles: List of entity handles
            layer_name: Target layer name

        Returns:
            bool: True if successful
        """
        pass

    # ========== Undo/Redo ==========

    @abstractmethod
    def undo(self, count: int = 1) -> bool:
        """
        Undo last action(s).

        Args:
            count: Number of operations to undo (default: 1)

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def redo(self, count: int = 1) -> bool:
        """
        Redo last undone action(s).

        Args:
            count: Number of operations to redo (default: 1)

        Returns:
            bool: True if successful
        """
        pass

    # ========== Utility Methods ==========

    @staticmethod
    def normalize_coordinate(coord: Coordinate) -> Point:
        """
        Normalize a coordinate to 3D point (x, y, z).

        Args:
            coord: 2D or 3D coordinate

        Returns:
            Point: 3D point with z=0 if not provided
        """
        if len(coord) == 2:
            return (float(coord[0]), float(coord[1]), 0.0)
        elif len(coord) == 3:
            return (float(coord[0]), float(coord[1]), float(coord[2]))
        else:
            raise ValueError(f"Invalid coordinate: {coord}")

    @staticmethod
    def validate_lineweight(weight: int) -> int:
        """
        Validate and return a proper lineweight value.

        Args:
            weight: Proposed lineweight

        Returns:
            int: Valid lineweight (or default if invalid)
        """
        if LineWeight.is_valid(weight):
            return weight
        # Return default thin line if invalid
        return LineWeight.THIN.value
