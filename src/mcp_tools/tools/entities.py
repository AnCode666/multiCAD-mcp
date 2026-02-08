"""
Unified entity management tool.

Single manage_entities tool replaces 13 legacy entity tools with
a simple shorthand format for ~85% token reduction.

SHORTHAND FORMAT (one per line):
    select|by|value               → select|layer|walls
    move|handles|offset_x|offset_y → move|A1,B2|10|5
    rotate|handles|angle|cx|cy    → rotate|A1|45|0|0
    scale|handles|factor|cx|cy    → scale|A1|2.0|0|0
    set_color|handles|color       → set_color|A1,B2|red
    set_layer|handles|layer       → set_layer|A1|walls
    copy|handles                  → copy|A1,B2
    delete|handles                → delete|A1,B2
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple

from mcp.server.fastmcp import Context
from pydantic import ValidationError

from core.models import (
    MoveEntityRequest,
    RotateEntityRequest,
    ScaleEntityRequest,
)
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_handles
from mcp_tools.shorthand import parse_entity_ops_input

logger = logging.getLogger(__name__)


# ========== Action Handlers ==========


def _select(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_current_adapter()
    by = spec["by"].lower()

    select_map = {
        "color": ("color", lambda v: adapter.select_by_color(v)),
        "layer": ("layer_name", lambda v: adapter.select_by_layer(v)),
        "type": ("entity_type", lambda v: adapter.select_by_type(v)),
    }

    entry = select_map.get(by)
    if not entry:
        return {
            "success": False,
            "error": f"Unknown selection criteria '{by}'. Supported: color, layer, type",
        }

    _, handler = entry
    value = spec["value"]
    handles = handler(value)

    if handles:
        return {
            "success": True,
            "count": len(handles),
            "handles": handles,
            "detail": f"Selected {len(handles)} entities by {by}='{value}'",
        }
    return {
        "success": True,
        "count": 0,
        "handles": [],
        "detail": f"No entities found with {by}='{value}'",
    }


def _move(spec: Dict[str, Any]) -> Dict[str, Any]:
    handle_list = parse_handles(spec["handles"])
    validated = MoveEntityRequest(
        handles=handle_list,
        displacement=(spec["offset_x"], spec["offset_y"]),
    )
    success = get_current_adapter().move_entities(
        validated.handles, spec["offset_x"], spec["offset_y"]
    )
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Moved by ({spec['offset_x']}, {spec['offset_y']})",
    }


def _rotate(spec: Dict[str, Any]) -> Dict[str, Any]:
    handle_list = parse_handles(spec["handles"])
    validated = RotateEntityRequest(
        handles=handle_list,
        base_point=(spec["center_x"], spec["center_y"]),
        angle=spec["angle"],
    )
    success = get_current_adapter().rotate_entities(
        validated.handles, spec["center_x"], spec["center_y"], validated.angle
    )
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Rotated {spec['angle']}° around ({spec['center_x']}, {spec['center_y']})",
    }


def _scale(spec: Dict[str, Any]) -> Dict[str, Any]:
    handle_list = parse_handles(spec["handles"])
    validated = ScaleEntityRequest(
        handles=handle_list,
        base_point=(spec["center_x"], spec["center_y"]),
        scale_factor=spec["scale_factor"],
    )
    success = get_current_adapter().scale_entities(
        validated.handles,
        spec["center_x"],
        spec["center_y"],
        validated.scale_factor,
    )
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Scaled {spec['scale_factor']}x around ({spec['center_x']}, {spec['center_y']})",
    }


def _set_color(spec: Dict[str, Any]) -> Dict[str, Any]:
    handle_list = parse_handles(spec["handles"])
    color = spec["color"]
    success = get_current_adapter().change_entity_color(handle_list, color)
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Color set to '{color}'",
    }


def _set_layer(spec: Dict[str, Any]) -> Dict[str, Any]:
    handle_list = parse_handles(spec["handles"])
    layer_name = spec["layer_name"]
    success = get_current_adapter().change_entity_layer(handle_list, layer_name)
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Moved to layer '{layer_name}'",
    }


def _set_color_bylayer(spec: Dict[str, Any]) -> Dict[str, Any]:
    handles_raw = spec["handles"]
    if isinstance(handles_raw, str):
        if handles_raw.startswith("["):
            handles_list = json.loads(handles_raw)
        else:
            handles_list = parse_handles(handles_raw)
    else:
        handles_list = handles_raw

    result = get_current_adapter().set_entities_color_bylayer(handles_list)
    return {
        "success": result.get("changed", 0) > 0,
        "count": result.get("total", len(handles_list)),
        "detail": f"Set {result.get('changed', 0)} entities to ByLayer color",
    }


def _copy(spec: Dict[str, Any]) -> Dict[str, Any]:
    handle_list = parse_handles(spec["handles"])
    success = get_current_adapter().copy_entities(handle_list)
    return {
        "success": success,
        "count": len(handle_list),
        "detail": (
            f"Copied {len(handle_list)} entities to clipboard"
            if success
            else "Failed to copy entities"
        ),
    }


def _paste(spec: Dict[str, Any]) -> Dict[str, Any]:
    base_point = spec["base_point"]
    parts = str(base_point).split(",")
    if len(parts) < 2:
        return {"success": False, "error": "base_point must be 'x,y' format"}
    bx, by = float(parts[0].strip()), float(parts[1].strip())
    get_current_adapter().paste_entities(bx, by)
def _delete(spec: Dict[str, Any]) -> Dict[str, Any]:
    handle_list = parse_handles(spec["handles"])
    adapter = get_current_adapter()
    deleted_count = 0
    for handle in handle_list:
        if adapter.delete_entity(handle):
            deleted_count += 1
    return {
        "success": deleted_count > 0,
        "count": len(handle_list),
        "detail": f"Deleted {deleted_count} entities",
    }


# Dispatch table: action -> (handler, required_fields)
ENTITY_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "select": (_select, ["by", "value"]),
    "move": (_move, ["handles", "offset_x", "offset_y"]),
    "rotate": (_rotate, ["handles", "center_x", "center_y", "angle"]),
    "scale": (_scale, ["handles", "center_x", "center_y", "scale_factor"]),
    "set_color": (_set_color, ["handles", "color"]),
    "set_layer": (_set_layer, ["handles", "layer_name"]),
    "set_color_bylayer": (_set_color_bylayer, ["handles"]),
    "copy": (_copy, ["handles"]),
    "paste": (_paste, ["base_point"]),
    "delete": (_delete, ["handles"]),
}


def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], action: str
) -> Optional[str]:
    missing = [f for f in required if f not in spec]
    if missing:
        return f"'{action}' requires fields: {', '.join(missing)}"
    return None


# ========== Tool Registration ==========


def register_entity_tools(mcp):
    """Register unified entity management tool with FastMCP."""

    @cad_tool(mcp, "manage_entities")
    def manage_entities(
        ctx: Context,
        operations: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Manage entities: select, transform, restyle, copy/paste.

        Args:
            operations: Operations in SHORTHAND format (one per line):

                select|by|value               → select|layer|walls
                move|handles|offset_x|offset_y → move|A1,B2|10|5
                rotate|handles|angle|cx|cy    → rotate|A1|45|0|0
                scale|handles|factor|cx|cy    → scale|A1|2.0|0|0
                set_color|handles|color       → set_color|A1,B2|red
                set_layer|handles|layer       → set_layer|A1|walls
                set_color_bylayer|handles     → set_color_bylayer|A1,B2
                copy|handles                  → copy|A1,B2
                paste|base_point              → paste|100,200
                delete|handles                → delete|A1,B2

                "handles" = comma-separated entity handles (e.g. "A1B2,C3D4")
                "by" = "color", "layer", or "type"

                Example:
                    select|layer|walls
                    move|A1B2,C3D4|10|5
                    set_color|A1B2,C3D4|red

                JSON format also supported for backwards compatibility.

            cad_type: CAD application to use

        Returns:
            JSON result with per-operation status
        """
        try:
            ops_data = parse_entity_ops_input(operations)
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid input: {str(e)}",
                    "total": 0,
                    "succeeded": 0,
                    "results": [],
                },
                indent=2,
            )

        results = []

        for i, spec in enumerate(ops_data):
            action = spec.get("action")

            if not action:
                results.append(
                    {
                        "index": i,
                        "success": False,
                        "error": "Missing 'action' field. Supported: "
                        + ", ".join(ENTITY_DISPATCH.keys()),
                    }
                )
                continue

            action_lower = action.lower()
            dispatch_entry = ENTITY_DISPATCH.get(action_lower)

            if not dispatch_entry:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": f"Unknown action '{action}'. Supported: "
                        + ", ".join(ENTITY_DISPATCH.keys()),
                    }
                )
                continue

            handler, required_fields = dispatch_entry

            field_error = _validate_required_fields(spec, required_fields, action_lower)
            if field_error:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": field_error,
                    }
                )
                continue

            try:
                result = handler(spec)
                results.append({"index": i, "action": action_lower, **result})
            except ValidationError as e:
                error_msg = f"Validation error: {e.errors()[0]['msg']}"
                logger.error(
                    f"Validation error in entity op {i} ({action_lower}): {error_msg}"
                )
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": error_msg,
                    }
                )
            except Exception as e:
                logger.error(f"Error in entity op {i} ({action_lower}): {e}")
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": str(e),
                    }
                )

        return json.dumps(
            {
                "total": len(ops_data),
                "succeeded": sum(1 for r in results if r.get("success")),
                "results": results,
            },
            indent=2,
        )
