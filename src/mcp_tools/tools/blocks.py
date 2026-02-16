"""
Unified block management tool.

Single manage_blocks tool replaces all 7 legacy block tools with
a simple shorthand format for ~85% token reduction.

SHORTHAND FORMAT (one per line):
    list                                      → list
    info|block_name|include                   → info|Door|both
    insert|name|point|scale|rotation|layer    → insert|Door|10,20|1.5|90|walls
    create|name|handles|point|description     → create|MyBlock|A1,B2|0,0|Desc
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple



from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate
from mcp_tools.shorthand import parse_block_ops_input

logger = logging.getLogger(__name__)


# ========== Action Handlers ==========


def _create(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_current_adapter()
    block_name = spec["block_name"]
    insert_pt = parse_coordinate(spec.get("insertion_point", "0,0,0"))
    description = spec.get("description", "")

    entity_handles = spec.get("entity_handles")
    if entity_handles is not None:
        if isinstance(entity_handles, str):
            entity_handles = json.loads(entity_handles)
        if not isinstance(entity_handles, list):
            entity_handles = [entity_handles]
        entity_handles = [str(h) for h in entity_handles]

        result = adapter.create_block_from_entities(
            block_name=block_name,
            entity_handles=entity_handles,
            insertion_point=insert_pt,
            description=description,
        )
    else:
        result = adapter.create_block_from_selection(
            block_name=block_name,
            insertion_point=insert_pt,
            description=description,
        )

    return result


def _insert(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_current_adapter()
    block_name = spec["block_name"]
    point = parse_coordinate(spec["insertion_point"])
    scale = spec.get("scale", 1.0)
    rotation = spec.get("rotation", 0.0)
    layer = spec.get("layer", "0")

    handle = adapter.insert_block(
        block_name=block_name,
        insertion_point=point,
        scale_x=scale,
        scale_y=scale,
        scale_z=scale,
        rotation=rotation,
        layer=layer,
        _skip_refresh=True,
    )

    return {
        "success": True,
        "handle": handle,
        "block_name": block_name,
        "insertion_point": spec["insertion_point"],
        "scale": scale,
        "rotation": rotation,
        "layer": layer,
    }


def _list(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_current_adapter()
    blocks = adapter.list_blocks()
    result = {"success": True, "count": len(blocks), "blocks": blocks}

    if blocks:
        result["_meta"] = {
            "ui": {
                "resourceUri": "ui://multicad/block_browser",
                "data": {"blocks": blocks},
            }
        }

    return result


def _info(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_current_adapter()
    block_name = spec["block_name"]
    include = spec.get("include", "info").lower()

    result: Dict[str, Any] = {"success": True, "block_name": block_name}

    if include in ("info", "both"):
        result["info"] = adapter.get_block_info(block_name)

    if include in ("references", "both"):
        refs = adapter.get_block_references(block_name)
        result["references"] = refs
        result["reference_count"] = len(refs)

    if include not in ("info", "references", "both"):
        return {
            "success": False,
            "error": f"Unknown include '{include}'. Use: info, references, both",
        }

    return result


# Dispatch table: action -> (handler, required_fields)
BLOCK_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "create": (_create, ["block_name"]),
    "insert": (_insert, ["block_name", "insertion_point"]),
    "list": (_list, []),
    "info": (_info, ["block_name"]),
}


def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], action: str
) -> Optional[str]:
    missing = [f for f in required if f not in spec]
    if missing:
        return f"'{action}' requires fields: {', '.join(missing)}"
    return None


# ========== Tool Registration ==========


def register_block_tools(mcp) -> None:
    """Register unified block management tool with FastMCP."""

    @cad_tool(mcp, "manage_blocks")
    def manage_blocks(
        operations: str,
    ) -> str:
        """
        Manage blocks: create, insert, list, or query block information.

        Args:
            operations: Operations in SHORTHAND format (one per line):

                list                                      → list
                info|block_name|include                   → info|Door|both
                insert|name|point|scale|rotation|layer    → insert|Door|10,20|1.5|90|walls
                create|name|handles|point|description     → create|MyBlock|A1,B2|0,0|Desc

                "include" = "info" (default), "references", or "both"
                "handles" = comma-separated entity handles

                DEFAULTS: scale=1.0, rotation=0, layer=0, include=info

                Example:
                    list
                    info|Door|both
                    insert|Door|10,20|1.5|90
                    insert|Door|30,20|1.0|0

                JSON format also supported for backwards compatibility.



        Returns:
            JSON result with per-operation status
        """
        try:
            ops_data = parse_block_ops_input(operations)
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

        adapter = get_current_adapter()
        results = []
        has_mutations = False

        for i, spec in enumerate(ops_data):
            action = spec.get("action")

            if not action:
                results.append(
                    {
                        "index": i,
                        "success": False,
                        "error": "Missing 'action' field. Supported: "
                        + ", ".join(BLOCK_DISPATCH.keys()),
                    }
                )
                continue

            action_lower = action.lower()
            dispatch_entry = BLOCK_DISPATCH.get(action_lower)

            if not dispatch_entry:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": f"Unknown action '{action}'. Supported: "
                        + ", ".join(BLOCK_DISPATCH.keys()),
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
                if action_lower in ("create", "insert"):
                    has_mutations = True
            except Exception as e:
                logger.error(f"Error in block op {i} ({action_lower}): {e}")
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": str(e),
                    }
                )

        # Single refresh only if mutations occurred
        if has_mutations and any(r.get("success") for r in results):
            adapter.refresh_view()

        return json.dumps(
            {
                "total": len(ops_data),
                "succeeded": sum(1 for r in results if r.get("success")),
                "results": results,
            },
            indent=2,
        )
