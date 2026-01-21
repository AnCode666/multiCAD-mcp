"""
Layer management tools.

Provides tools for:
- Creating, listing, and deleting layers
- Renaming, toggling visibility of multiple layers
- Batch operations for efficient layer management
"""

import json
import logging
from typing import Optional

from mcp.server.fastmcp import Context
from pydantic import ValidationError

from core.models import CreateLayerRequest
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import result_message

logger = logging.getLogger(__name__)


def register_layer_tools(mcp):
    """Register layer management tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    # ========== SINGLE LAYER OPERATIONS ==========

    @cad_tool(mcp, "create_layer")
    def create_layer(
        ctx: Context,
        name: str,
        color: str = "white",
        lineweight: int = 25,
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
        try:
            # Use Pydantic validation
            validated = CreateLayerRequest(
                name=name, color=color, lineweight=lineweight
            )
            success = get_current_adapter().create_layer(
                validated.name, validated.color, validated.lineweight
            )
            return result_message("create layer", success, name)
        except ValidationError as e:
            error_msg = f"Validation error: {e.errors()[0]['msg']}"
            logger.error(f"Validation error creating layer: {error_msg}")
            return result_message("create layer", False, f"{name}: {error_msg}")

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

    # ========== BATCH OPERATIONS (Multiple Layers) ==========

    @cad_tool(mcp, "rename_layers")
    def rename_layers(
        ctx: Context,
        renames: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Rename multiple layers in a single operation.

        Args:
            renames: JSON array of rename specifications.
                     Example: [{"old_name": "Layer1", "new_name": "NewName1"}, {"old_name": "Layer2", "new_name": "NewName2"}]
                     Fields: old_name (required), new_name (required)
            cad_type: CAD application to use

        Returns:
            JSON result with rename operation status
        """
        try:
            renames_data = json.loads(renames) if isinstance(renames, str) else renames
            if not isinstance(renames_data, list):
                renames_data = [renames_data]

            results = []
            for i, rename_spec in enumerate(renames_data):
                try:
                    old_name = rename_spec["old_name"]
                    new_name = rename_spec["new_name"]
                    success = get_current_adapter().rename_layer(old_name, new_name)
                    results.append(
                        {
                            "index": i,
                            "old_name": old_name,
                            "new_name": new_name,
                            "success": success,
                        }
                    )
                except Exception as e:
                    logger.error(f"Error renaming layer {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(renames_data),
                    "renamed": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "renamed": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "delete_layers")
    def delete_layers(
        ctx: Context,
        layer_names: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Delete multiple layers in a single operation.

        Args:
            layer_names: JSON array of layer names to delete.
                         Example: ["Layer1", "Layer2", "Layer3"]
                         Or JSON array of objects: [{"name": "Layer1"}, {"name": "Layer2"}]
            cad_type: CAD application to use

        Returns:
            JSON result with delete operation status
        """
        try:
            data = (
                json.loads(layer_names) if isinstance(layer_names, str) else layer_names
            )
            if not isinstance(data, list):
                data = [data]

            # Handle both string array and object array formats
            names: list[str] = []
            for item in data:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict):
                    name = item.get("name")
                    if name is not None:
                        names.append(str(name))
                else:
                    names.append(str(item))

            results = []
            for i, name in enumerate(names):
                try:
                    success = get_current_adapter().delete_layer(name)
                    results.append({"index": i, "name": name, "success": success})
                except Exception as e:
                    logger.error(f"Error deleting layer {i} ({name}): {e}")
                    results.append(
                        {"index": i, "name": name, "success": False, "error": str(e)}
                    )

            return json.dumps(
                {
                    "total": len(names),
                    "deleted": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "deleted": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "turn_layers_on")
    def turn_layers_on(
        ctx: Context,
        layer_names: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Turn on (make visible) multiple layers in a single operation.

        Args:
            layer_names: JSON array of layer names to turn on.
                         Example: ["Layer1", "Layer2", "Layer3"]
                         Or JSON array of objects: [{"name": "Layer1"}, {"name": "Layer2"}]
            cad_type: CAD application to use

        Returns:
            JSON result with operation status
        """
        try:
            data = (
                json.loads(layer_names) if isinstance(layer_names, str) else layer_names
            )
            if not isinstance(data, list):
                data = [data]

            # Handle both string array and object array formats
            names: list[str] = []
            for item in data:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict):
                    name = item.get("name")
                    if name is not None:
                        names.append(str(name))
                else:
                    names.append(str(item))

            results = []
            for i, name in enumerate(names):
                try:
                    success = get_current_adapter().turn_layer_on(name)
                    results.append({"index": i, "name": name, "success": success})
                except Exception as e:
                    logger.error(f"Error turning on layer {i} ({name}): {e}")
                    results.append(
                        {"index": i, "name": name, "success": False, "error": str(e)}
                    )

            return json.dumps(
                {
                    "total": len(names),
                    "turned_on": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "turned_on": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "turn_layers_off")
    def turn_layers_off(
        ctx: Context,
        layer_names: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Turn off (hide) multiple layers in a single operation.

        Args:
            layer_names: JSON array of layer names to turn off.
                         Example: ["Layer1", "Layer2", "Layer3"]
                         Or JSON array of objects: [{"name": "Layer1"}, {"name": "Layer2"}]
            cad_type: CAD application to use

        Returns:
            JSON result with operation status
        """
        try:
            data = (
                json.loads(layer_names) if isinstance(layer_names, str) else layer_names
            )
            if not isinstance(data, list):
                data = [data]

            # Handle both string array and object array formats
            names: list[str] = []
            for item in data:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict):
                    name = item.get("name")
                    if name is not None:
                        names.append(str(name))
                else:
                    names.append(str(item))

            results = []
            for i, name in enumerate(names):
                try:
                    success = get_current_adapter().turn_layer_off(name)
                    results.append({"index": i, "name": name, "success": success})
                except Exception as e:
                    logger.error(f"Error turning off layer {i} ({name}): {e}")
                    results.append(
                        {"index": i, "name": name, "success": False, "error": str(e)}
                    )

            return json.dumps(
                {
                    "total": len(names),
                    "turned_off": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "turned_off": 0,
                    "results": [],
                },
                indent=2,
            )

    # ========== LAYER COLOR OPERATIONS ==========

    @cad_tool(mcp, "set_layer_color")
    def set_layer_color(
        ctx: Context,
        layer_name: str,
        color: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Set the color of a layer.

        Args:
            layer_name: Name of the layer to modify
            color: Color name (red, blue, green, etc.) or ACI index (1-255)
            cad_type: CAD application to use

        Returns:
            Status message

        Example:
            set_layer_color(layer_name="Walls", color="red")
            set_layer_color(layer_name="Doors", color="blue")

        Note:
            - Uses modern TrueColor property (recommended by Autodesk)
            - Available colors: red, blue, green, yellow, cyan, magenta, white, gray, etc.
            - Color 'bylayer' (256) is not valid for layers
        """
        adapter = get_current_adapter()

        try:
            success = adapter.set_layer_color(layer_name, color)
            if success:
                return result_message(
                    f"Set layer '{layer_name}' color to '{color}'", True
                )
            else:
                return result_message(
                    f"Failed to set layer '{layer_name}' color", False
                )
        except Exception as e:
            return result_message(f"Error setting layer color: {str(e)}", False)
