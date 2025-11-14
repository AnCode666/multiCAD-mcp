"""
Entity selection and manipulation tools.

Provides tools for:
- Selecting entities by color, layer, or type
- Moving, rotating, and scaling entities
- Copying and pasting entities
- Changing entity properties (color, layer)
"""

import logging
from typing import Optional

from mcp.server.fastmcp import Context

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_handles

logger = logging.getLogger(__name__)


def register_entity_tools(mcp):
    """Register entity selection and manipulation tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @cad_tool(mcp, "select_by_color")
    def select_by_color(
        ctx: Context,
        color: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Select all entities of a specific color.

        Args:
            color: Color name (red, blue, green, white, etc.)
            cad_type: CAD application to use

        Returns:
            Number of selected entities and their handles
        """
        handles = get_current_adapter().select_by_color(color)

        if handles:
            handles_str = ",".join(handles)
            return f"Selected {len(handles)} entities with color '{color}'. Handles: {handles_str}"
        else:
            return f"No entities found with color '{color}'"

    @cad_tool(mcp, "select_by_layer")
    def select_by_layer(
        ctx: Context,
        layer_name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Select all entities on a specific layer.

        Args:
            layer_name: Name of the layer
            cad_type: CAD application to use

        Returns:
            Number of selected entities and their handles
        """
        handles = get_current_adapter().select_by_layer(layer_name)

        if handles:
            handles_str = ",".join(handles)
            return f"Selected {len(handles)} entities on layer '{layer_name}'. Handles: {handles_str}"
        else:
            return f"No entities found on layer '{layer_name}'"

    @cad_tool(mcp, "select_by_type")
    def select_by_type(
        ctx: Context,
        entity_type: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Select all entities of a specific type.

        Args:
            entity_type: Entity type (line, circle, arc, polyline, etc.)
            cad_type: CAD application to use

        Returns:
            Number of selected entities and their handles
        """
        handles = get_current_adapter().select_by_type(entity_type)

        if handles:
            handles_str = ",".join(handles)
            return f"Selected {len(handles)} entities of type '{entity_type}'. Handles: {handles_str}"
        else:
            return f"No entities found of type '{entity_type}'"

    @cad_tool(mcp, "move_entities")
    def move_entities(
        ctx: Context,
        handles: str,
        offset_x: float,
        offset_y: float,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Move entities by an offset.

        Args:
            handles: Comma-separated entity handles
            offset_x: X offset distance
            offset_y: Y offset distance
            cad_type: CAD application to use

        Returns:
            Status message with count of moved entities
        """
        handle_list = parse_handles(handles)
        success = get_current_adapter().move_entities(handle_list, offset_x, offset_y)

        if success:
            return f"Moved {len(handle_list)} entities by ({offset_x}, {offset_y})"
        else:
            return "Failed to move entities"

    @cad_tool(mcp, "rotate_entities")
    def rotate_entities(
        ctx: Context,
        handles: str,
        center_x: float,
        center_y: float,
        angle: float,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Rotate entities around a point.

        Args:
            handles: Comma-separated entity handles
            center_x: X coordinate of rotation center
            center_y: Y coordinate of rotation center
            angle: Rotation angle in degrees
            cad_type: CAD application to use

        Returns:
            Status message with count of rotated entities
        """
        handle_list = parse_handles(handles)
        success = get_current_adapter().rotate_entities(
            handle_list, center_x, center_y, angle
        )

        if success:
            return f"Rotated {len(handle_list)} entities by {angle}°"
        else:
            return "Failed to rotate entities"

    @cad_tool(mcp, "scale_entities")
    def scale_entities(
        ctx: Context,
        handles: str,
        center_x: float,
        center_y: float,
        scale_factor: float,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Scale entities around a point.

        Args:
            handles: Comma-separated entity handles
            center_x: X coordinate of scale center
            center_y: Y coordinate of scale center
            scale_factor: Scale factor (1.0 = no change, 2.0 = double size)
            cad_type: CAD application to use

        Returns:
            Status message with count of scaled entities
        """
        handle_list = parse_handles(handles)
        success = get_current_adapter().scale_entities(
            handle_list, center_x, center_y, scale_factor
        )

        if success:
            return f"Scaled {len(handle_list)} entities by {scale_factor}x"
        else:
            return "Failed to scale entities"

    @cad_tool(mcp, "copy_entities")
    def copy_entities(
        ctx: Context,
        handles: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Copy entities to clipboard.

        Args:
            handles: Comma-separated entity handles
            cad_type: CAD application to use

        Returns:
            Status message with count of copied entities
        """
        handle_list = parse_handles(handles)
        success = get_current_adapter().copy_entities(handle_list)

        if success:
            return f"Copied {len(handle_list)} entities to clipboard"
        else:
            return "Failed to copy entities"

    @cad_tool(mcp, "paste_entities")
    def paste_entities(
        ctx: Context,
        base_point_x: float,
        base_point_y: float,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Paste entities from clipboard at a base point.

        Args:
            base_point_x: X coordinate of base point
            base_point_y: Y coordinate of base point
            cad_type: CAD application to use

        Returns:
            Status message
        """
        get_current_adapter().paste_entities(base_point_x, base_point_y)
        return f"Pasted entities at ({base_point_x}, {base_point_y})"

    @cad_tool(mcp, "change_entity_color")
    def change_entity_color(
        ctx: Context,
        handles: str,
        color: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Change color of entities.

        Args:
            handles: Comma-separated entity handles
            color: New color name
            cad_type: CAD application to use

        Returns:
            Status message with count of changed entities
        """
        handle_list = parse_handles(handles)
        success = get_current_adapter().change_entity_color(handle_list, color)

        if success:
            return f"Changed color of {len(handle_list)} entities to '{color}'"
        else:
            return "Failed to change entity color"

    @cad_tool(mcp, "change_entity_layer")
    def change_entity_layer(
        ctx: Context,
        handles: str,
        layer_name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Move entities to a different layer.

        Args:
            handles: Comma-separated entity handles
            layer_name: Target layer name
            cad_type: CAD application to use

        Returns:
            Status message with count of moved entities
        """
        handle_list = parse_handles(handles)
        success = get_current_adapter().change_entity_layer(handle_list, layer_name)

        if success:
            return f"Moved {len(handle_list)} entities to layer '{layer_name}'"
        else:
            return "Failed to change entity layer"
