"""
Block tools for inserting and managing block references with attributes.

Provides tools for:
- Listing available block definitions
- Inserting blocks with attributes
- Getting/setting block attributes
- Batch block insertion and attribute updates
"""

import json
import logging
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import Context

from core import InvalidParameterError
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate

logger = logging.getLogger(__name__)


# ============================================================
#  Helper: Insert a single block
# ============================================================

def insert_block(
    adapter,
    block_name: str,
    insertion_point: str,
    scale: float = 1.0,
    rotation: float = 0.0,
    layer: str = "0",
    color: str = "white",
    attributes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Insert a block into the CAD drawing.

    Args:
        adapter: Active CAD adapter
        block_name: Name of the block to insert
        insertion_point: Coordinates as "x,y" or "x,y,z"
        scale: Uniform scale factor
        rotation: Rotation in degrees
        layer: Target layer
        color: Color for the block reference
        attributes: Dictionary of attribute tag -> value pairs

    Returns:
        Dictionary with operation result
    """
    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        point = parse_coordinate(insertion_point)

        handle = adapter.insert_block(
            block_name=block_name,
            insertion_point=point,
            scale_x=scale,
            scale_y=scale,
            scale_z=scale,
            rotation=rotation,
            layer=layer,
            color=color,
            attributes=attributes,
        )

        return {
            "success": True,
            "message": f"Block '{block_name}' inserted.",
            "block_name": block_name,
            "handle": handle,
            "insertion_point": insertion_point,
            "scale": scale,
            "rotation": rotation,
            "layer": layer,
        }

    except Exception as e:
        logger.error(f"insert_block error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
#  Helper: Insert multiple blocks (batch)
# ============================================================

def insert_blocks_batch(
    adapter, blocks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Insert multiple blocks in a single operation.

    Args:
        adapter: Active CAD adapter
        blocks: List of block specs with:
                - block_name (required)
                - insertion_point or position (required)
                - scale (optional, uniform) or scale_x/y/z (optional, individual)
                - rotation (optional)
                - layer (optional)
                - color (optional)
                - attributes (optional, dict of tag -> value)

    Returns:
        Aggregated operation result
    """
    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    results = []
    success_count = 0
    fail_count = 0

    for i, b in enumerate(blocks):
        try:
            # Support both "insertion_point" and "position" keys
            pos_str = b.get("insertion_point") or b.get("position")
            if not pos_str:
                raise InvalidParameterError(
                    "position", "missing",
                    "insertion_point or position field required"
                )
            point = parse_coordinate(pos_str)

            # Scale handling: uniform or individual
            if "scale" in b:
                scale = float(b["scale"])
                scale_x = scale_y = scale_z = scale
            else:
                scale_x = float(b.get("scale_x", 1.0))
                scale_y = float(b.get("scale_y", 1.0))
                scale_z = float(b.get("scale_z", 1.0))

            handle = adapter.insert_block(
                block_name=b["block_name"],
                insertion_point=point,
                scale_x=scale_x,
                scale_y=scale_y,
                scale_z=scale_z,
                rotation=b.get("rotation", 0.0),
                layer=b.get("layer", "0"),
                color=b.get("color", "white"),
                attributes=b.get("attributes"),
                _skip_refresh=True,
            )

            results.append({
                "index": i,
                "success": True,
                "handle": handle,
                "block_name": b["block_name"],
            })
            success_count += 1

        except Exception as e:
            fail_count += 1
            results.append({
                "index": i,
                "success": False,
                "block_name": b.get("block_name"),
                "error": str(e),
            })

    # Single view refresh after all blocks inserted
    adapter.refresh_view()

    return {
        "success": fail_count == 0,
        "inserted": success_count,
        "failed": fail_count,
        "results": results,
    }


# ============================================================
#  Helper: List available blocks
# ============================================================

def list_blocks(adapter) -> Dict[str, Any]:
    """
    List all non-system block definitions in the CAD drawing.

    Returns:
        Dictionary with block list (Name, IsXRef, IsLayout, Origin)
    """
    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        blocks = adapter.list_blocks()
        return {
            "success": True,
            "count": len(blocks),
            "blocks": blocks,
        }
    except Exception as e:
        logger.error(f"list_blocks error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
#  Helper: Get block definition info
# ============================================================

def get_block_info(adapter, block_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a block definition.

    Returns:
        Dictionary with Name, Origin, ObjectCount, IsXRef, Comments
    """
    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        info = adapter.get_block_info(block_name)
        return {"success": True, "info": info}
    except Exception as e:
        logger.error(f"get_block_info error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
#  Helper: Get block references (instances)
# ============================================================

def get_block_references(adapter, block_name: str) -> Dict[str, Any]:
    """
    List all references of a block in the drawing.

    Returns:
        List with Handle, InsertionPoint, ScaleFactors, Rotation, Layer
    """
    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        refs = adapter.get_block_references(block_name)
        return {
            "success": True,
            "count": len(refs),
            "references": refs,
        }
    except Exception as e:
        logger.error(f"get_block_references error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
#  Tool Registration
# ============================================================

def register_block_tools(mcp) -> None:
    """Register block-related MCP tools."""

    # ---------- Insert single block ----------

    @cad_tool(mcp, "insert_block")
    def insert_block_tool(
        ctx: Context,
        block_name: str,
        insertion_point: str,
        scale: float = 1.0,
        rotation: float = 0.0,
        layer: str = "0",
        color: str = "white",
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return insert_block(
                adapter, block_name, insertion_point,
                scale, rotation, layer, color,
            )
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"insert_block failed: {e}")
            raise

    # ---------- Insert multiple blocks (batch) ----------

    @cad_tool(mcp, "insert_blocks_batch")
    def insert_blocks_batch_tool(
        ctx: Context,
        blocks: List[Dict[str, Any]],
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return insert_blocks_batch(adapter, blocks)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"insert_blocks_batch failed: {e}")
            raise

    # ---------- List blocks ----------

    @cad_tool(mcp, "list_blocks")
    def list_blocks_tool(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return list_blocks(adapter)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"list_blocks failed: {e}")
            raise

    # ---------- Get block info ----------

    @cad_tool(mcp, "get_block_info")
    def get_block_info_tool(
        ctx: Context,
        block_name: str,
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return get_block_info(adapter, block_name)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"get_block_info failed: {e}")
            raise

    # ---------- Get block references ----------

    @cad_tool(mcp, "get_block_references")
    def get_block_references_tool(
        ctx: Context,
        block_name: str,
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return get_block_references(adapter, block_name)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"get_block_references failed: {e}")
            raise

    # ---------- Get block attributes ----------

    @cad_tool(mcp, "get_block_attributes")
    def get_block_attributes_tool(
        ctx: Context,
        handle: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Get all attributes from a block reference.

        Args:
            handle: Handle of the block reference entity
            cad_type: CAD application to use

        Returns:
            JSON object with attribute tag -> value pairs
        """
        adapter = get_current_adapter()
        attributes = adapter.get_block_attributes(handle)

        return json.dumps({
            "success": True,
            "handle": handle,
            "attribute_count": len(attributes),
            "attributes": attributes,
        }, indent=2)

    # ---------- Set block attributes ----------

    @cad_tool(mcp, "set_block_attributes")
    def set_block_attributes_tool(
        ctx: Context,
        handle: str,
        attributes: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Set attributes on a block reference.

        Args:
            handle: Handle of the block reference entity
            attributes: JSON object with attribute tag -> value pairs.
                       Example: {"INTENSIDAD": "25A", "POLOS": "4P", "PODER_CORTE": "10kA"}
            cad_type: CAD application to use

        Returns:
            JSON result with operation status
        """
        try:
            attrs_data = (
                json.loads(attributes) if isinstance(attributes, str)
                else attributes
            )

            adapter = get_current_adapter()
            success = adapter.set_block_attributes(handle, attrs_data)

            return json.dumps({
                "success": success,
                "handle": handle,
                "attributes_set": list(attrs_data.keys()) if success else [],
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON for attributes: {str(e)}",
            }, indent=2)

    # ---------- Update multiple block attributes (batch) ----------

    @cad_tool(mcp, "update_multiple_block_attributes")
    def update_multiple_block_attributes_tool(
        ctx: Context,
        updates: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Update attributes on multiple block references in a single operation.

        Args:
            updates: JSON array of update specifications.
                    Example: [{"handle": "ABC123", "attributes": {"INTENSIDAD": "16A"}},
                             {"handle": "DEF456", "attributes": {"INTENSIDAD": "25A"}}]
            cad_type: CAD application to use

        Returns:
            JSON result with operation status for each block
        """
        try:
            updates_data = (
                json.loads(updates) if isinstance(updates, str)
                else updates
            )
            if not isinstance(updates_data, list):
                updates_data = [updates_data]

            adapter = get_current_adapter()
            results = []

            for i, update in enumerate(updates_data):
                try:
                    handle = update["handle"]
                    attrs = update["attributes"]

                    success = adapter.set_block_attributes(handle, attrs)

                    results.append({
                        "index": i,
                        "handle": handle,
                        "success": success,
                        "attributes_set": (
                            list(attrs.keys()) if success else []
                        ),
                    })

                except KeyError as e:
                    results.append({
                        "index": i,
                        "success": False,
                        "error": f"Missing required field: {e}",
                    })
                except Exception as e:
                    results.append({
                        "index": i,
                        "success": False,
                        "error": str(e),
                    })

            return json.dumps({
                "total": len(updates_data),
                "updated": sum(1 for r in results if r["success"]),
                "results": results,
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON input: {str(e)}",
                "total": 0,
                "updated": 0,
                "results": [],
            }, indent=2)
