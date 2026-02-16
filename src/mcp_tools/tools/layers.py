"""
Unified layer management tool.

Single manage_layers tool replaces all 9 legacy layer tools with
a simple shorthand format for ~85% token reduction.

SHORTHAND FORMAT (one per line):
    create|name|color|lineweight  → create|walls|red|50
    delete|name                   → delete|temp
    rename|old|new                → rename|Layer1|furniture
    on|names(,sep)                → on|walls,doors
    off|names(,sep)               → off|Defpoints
    set_color|name|color          → set_color|0|white
    list                          → list
    info                          → info
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple


from pydantic import ValidationError

from core.models import CreateLayerRequest
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.shorthand import parse_layer_ops_input

logger = logging.getLogger(__name__)


# ========== Action Handlers ==========


def _parse_layer_names(raw: Any) -> List[str]:
    """Parse layer names from string array or object array formats."""
    if not isinstance(raw, list):
        raw = [raw]
    names = []
    for item in raw:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            name = item.get("name")
            if name is not None:
                names.append(str(name))
        else:
            names.append(str(item))
    return names


def _create(spec: Dict[str, Any]) -> Dict[str, Any]:
    validated = CreateLayerRequest(
        name=spec["name"],
        color=spec.get("color", "white"),
        lineweight=spec.get("lineweight", 25),
    )
    success = get_current_adapter().create_layer(
        validated.name, validated.color, validated.lineweight
    )
    return {"name": spec["name"], "success": success}


def _rename(spec: Dict[str, Any]) -> Dict[str, Any]:
    old_name = spec["old_name"]
    new_name = spec["new_name"]
    success = get_current_adapter().rename_layer(old_name, new_name)
    return {"old_name": old_name, "new_name": new_name, "success": success}


def _delete(spec: Dict[str, Any]) -> Dict[str, Any]:
    name = spec["name"]
    success = get_current_adapter().delete_layer(name)
    return {"name": name, "success": success}


def _turn_on(spec: Dict[str, Any]) -> Dict[str, Any]:
    names = _parse_layer_names(spec["names"])
    results = []
    for name in names:
        success = get_current_adapter().turn_layer_on(name)
        results.append({"name": name, "success": success})
    ok = sum(1 for r in results if r["success"])
    return {"success": ok == len(names), "count": ok, "layers": results}


def _turn_off(spec: Dict[str, Any]) -> Dict[str, Any]:
    names = _parse_layer_names(spec["names"])
    results = []
    for name in names:
        success = get_current_adapter().turn_layer_off(name)
        results.append({"name": name, "success": success})
    ok = sum(1 for r in results if r["success"])
    return {"success": ok == len(names), "count": ok, "layers": results}


def _set_color(spec: Dict[str, Any]) -> Dict[str, Any]:
    name = spec["name"]
    color = spec["color"]
    success = get_current_adapter().set_layer_color(name, color)
    return {"name": name, "color": color, "success": success}


def _list(spec: Dict[str, Any]) -> Dict[str, Any]:
    layers = get_current_adapter().list_layers()
    return {"success": True, "count": len(layers), "layers": layers}


def _is_on(spec: Dict[str, Any]) -> Dict[str, Any]:
    name = spec["name"]
    is_on = get_current_adapter().is_layer_on(name)
    return {
        "success": True,
        "name": name,
        "on": is_on,
        "detail": f"Layer '{name}' is {'on (visible)' if is_on else 'off (hidden)'}",
    }


def _info(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_current_adapter()
    layer_names = adapter.list_layers()

    layers = []
    for name in layer_names:
        try:
            layer_info = {
                "name": name,
                "on": adapter.is_layer_on(name),
            }
            try:
                doc = adapter.get_document()
                layer = doc.Layers.Item(name)
                layer_info["color"] = layer.color
                layer_info["locked"] = layer.Lock
                layer_info["frozen"] = layer.Freeze
                layer_info["current"] = doc.ActiveLayer.Name == name
            except Exception:
                pass
            layers.append(layer_info)
        except Exception as e:
            logger.debug(f"Error getting info for layer {name}: {e}")
            layers.append({"name": name, "on": True})

    return {
        "success": True,
        "count": len(layers),
        "layers": layers,
        "_meta": {
            "ui": {
                "resourceUri": "ui://multicad/layer_panel",
                "data": {"layers": layers},
            }
        },
    }


# Dispatch table: action -> (handler, required_fields)
LAYER_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "create": (_create, ["name"]),
    "rename": (_rename, ["old_name", "new_name"]),
    "delete": (_delete, ["name"]),
    "turn_on": (_turn_on, ["names"]),
    "turn_off": (_turn_off, ["names"]),
    "set_color": (_set_color, ["name", "color"]),
    "list": (_list, []),
    "is_on": (_is_on, ["name"]),
    "info": (_info, []),
}


def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], action: str
) -> Optional[str]:
    missing = [f for f in required if f not in spec]
    if missing:
        return f"'{action}' requires fields: {', '.join(missing)}"
    return None


# ========== Tool Registration ==========


def register_layer_tools(mcp):
    """Register unified layer management tool with FastMCP."""

    @cad_tool(mcp, "manage_layers")
    def manage_layers(
        operations: str,
    ) -> str:
        """
        Manage layers: create, modify, query, or change visibility.

        Args:
            operations: Operations in SHORTHAND format (one per line):

                create|name|color|lineweight  → create|walls|red|50
                delete|name                   → delete|temp
                rename|old|new                → rename|Layer1|furniture
                on|names(,sep)                → on|walls,doors
                off|names(,sep)               → off|Defpoints
                set_color|name|color          → set_color|0|white
                is_on|name                    → is_on|walls
                list                          → list
                info                          → info

                DEFAULTS: color=white, lineweight=25

                Example:
                    create|walls|red
                    create|doors|blue
                    off|Defpoints,notes
                    set_color|0|white

                JSON format also supported for backwards compatibility.



        Returns:
            JSON result with per-operation status
        """
        try:
            ops_data = parse_layer_ops_input(operations)
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
                        + ", ".join(LAYER_DISPATCH.keys()),
                    }
                )
                continue

            action_lower = action.lower()
            dispatch_entry = LAYER_DISPATCH.get(action_lower)

            if not dispatch_entry:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": f"Unknown action '{action}'. Supported: "
                        + ", ".join(LAYER_DISPATCH.keys()),
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
                    f"Validation error in layer op {i} ({action_lower}): {error_msg}"
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
                logger.error(f"Error in layer op {i} ({action_lower}): {e}")
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
