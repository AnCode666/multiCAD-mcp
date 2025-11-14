"""
Layer management tools.

Provides tools for:
- Creating, listing, and deleting layers
- Renaming layers
- Toggling layer visibility
"""

import logging
from typing import Optional

from mcp.server.fastmcp import Context

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import result_message

logger = logging.getLogger(__name__)


def register_layer_tools(mcp):
    """Register layer management tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @cad_tool(mcp, "create_layer")
    def create_layer(
        ctx: Context,
        name: str,
        color: str = "white",
        lineweight: int = 0,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Create a new layer.

        Args:
            name: Layer name
            color: Layer color
            lineweight: Layer line weight
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().create_layer(name, color, lineweight)
        return result_message("create layer", success, name)

    @cad_tool(mcp, "list_layers")
    def list_layers(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        List all layers in the current drawing.

        Args:
            cad_type: CAD application to use

        Returns:
            Comma-separated list of layer names
        """
        layers = get_current_adapter().list_layers()
        return f"Layers: {', '.join(layers)}"

    @cad_tool(mcp, "rename_layer")
    def rename_layer(
        ctx: Context,
        old_name: str,
        new_name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Rename an existing layer.

        Args:
            old_name: Current layer name
            new_name: New layer name
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().rename_layer(old_name, new_name)
        return result_message("rename layer", success, f"'{old_name}' → '{new_name}'")

    @cad_tool(mcp, "delete_layer")
    def delete_layer(
        ctx: Context,
        name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Delete a layer from the drawing.

        Args:
            name: Layer name to delete
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().delete_layer(name)
        return result_message("delete layer", success, name)

    @cad_tool(mcp, "turn_layer_on")
    def turn_layer_on(
        ctx: Context,
        name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Turn on (make visible) a layer.

        Args:
            name: Layer name
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().turn_layer_on(name)
        return result_message("turn layer on", success, name)

    @cad_tool(mcp, "turn_layer_off")
    def turn_layer_off(
        ctx: Context,
        name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Turn off (hide) a layer.

        Args:
            name: Layer name
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().turn_layer_off(name)
        return result_message("turn layer off", success, name)

    @cad_tool(mcp, "is_layer_on")
    def is_layer_on(
        ctx: Context,
        name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Check if a layer is visible (turned on).

        Args:
            name: Layer name
            cad_type: CAD application to use

        Returns:
            Layer visibility status
        """
        is_on = get_current_adapter().is_layer_on(name)
        status = "on (visible)" if is_on else "off (hidden)"
        return f"Layer '{name}' is {status}"
