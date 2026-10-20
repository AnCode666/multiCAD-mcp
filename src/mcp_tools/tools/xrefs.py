"""
Unified External References (XREF) and Raster Images management tool.

Enables coordinating multi-file architectural projects:
- attach: Attach DWG background reference (structure, topography, MEP)
- raster: Attach scanned orthophoto or image plan
- list: List all active external references
- reload: Refresh updated XREF files
- detach: Unlink references
"""

import json
import logging
from typing import Dict, Any, Union, List, Optional
from pathlib import Path

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate

logger = logging.getLogger(__name__)


def _attach_xref(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Attach external DWG reference."""
    path = spec.get("path") or spec.get("filepath", "")
    if not path:
        return {"success": False, "error": "Missing 'path' for XREF"}

    ins_pt = parse_coordinate(spec.get("insertion_point", "0,0"))
    scale = float(spec.get("scale", 1.0))
    rotation = float(spec.get("rotation", 0.0))
    name = spec.get("name") or Path(path).stem

    if hasattr(adapter, "attach_xref"):
        res = adapter.attach_xref(
            filepath=path,
            block_name=name,
            insertion_point=ins_pt,
            scale=scale,
            rotation=rotation,
        )
        return {"success": True, "detail": f"Attached XREF '{name}' from {path}", **res}
    return {"success": False, "error": "Adapter does not support XREF attachment"}


def _attach_raster(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Attach raster image or orthophoto."""
    path = spec.get("path") or spec.get("filepath", "")
    if not path:
        return {"success": False, "error": "Missing 'path' for raster image"}

    ins_pt = parse_coordinate(spec.get("insertion_point", "0,0"))
    scale = float(spec.get("scale", 1.0))
    rotation = float(spec.get("rotation", 0.0))

    if hasattr(adapter, "attach_raster"):
        res = adapter.attach_raster(
            filepath=path,
            insertion_point=ins_pt,
            scale=scale,
            rotation=rotation,
        )
        return {"success": True, "detail": f"Attached raster image from {path}", **res}
    return {"success": False, "error": "Adapter does not support raster image attachment"}


def _list_xrefs(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """List active external references."""
    if hasattr(adapter, "list_xrefs"):
        xrefs = adapter.list_xrefs()
        return {"success": True, "count": len(xrefs), "xrefs": xrefs}
    return {"success": False, "error": "Adapter does not support listing XREFs"}


def _reload_xref(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Reload an external reference by name."""
    name = spec.get("name", "")
    if not name:
        return {"success": False, "error": "Missing XREF 'name'"}

    if hasattr(adapter, "reload_xref"):
        ok = adapter.reload_xref(name)
        return {
            "success": ok,
            "name": name,
            "detail": f"Reloaded XREF '{name}'" if ok else f"Failed to reload XREF '{name}'",
        }
    return {"success": False, "error": "Adapter does not support reloading XREFs"}


def _detach_xref(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Detach an external reference by name."""
    name = spec.get("name", "")
    if not name:
        return {"success": False, "error": "Missing XREF 'name'"}

    if hasattr(adapter, "detach_xref"):
        ok = adapter.detach_xref(name)
        return {
            "success": ok,
            "name": name,
            "detail": f"Detached XREF '{name}'" if ok else f"Failed to detach XREF '{name}'",
        }
    return {"success": False, "error": "Adapter does not support detaching XREFs"}


XREF_DISPATCH = {
    "attach": _attach_xref,
    "attach_dwg": _attach_xref,
    "raster": _attach_raster,
    "attach_raster": _attach_raster,
    "list": _list_xrefs,
    "reload": _reload_xref,
    "detach": _detach_xref,
}


def register_xref_tools(mcp):
    """Register unified XREF management tool with FastMCP."""

    @cad_tool(mcp, "manage_xrefs")
    def manage_xrefs(
        input: Union[str, List[Any], Dict[str, Any]],
    ) -> str:
        """
        Manage external references (XREF DWGs) and raster images/orthophotos.

        Shorthand:
        - attach|path|[x,y]|[scale]|[rotation]: Attach DWG reference
        - raster|path|[x,y]|[scale]: Attach raster image (PNG, JPG, TIFF)
        - list: List all attached XREFs and images
        - reload|name: Reload updated reference
        - detach|name: Unlink reference from drawing
        """
        adapter = get_current_adapter()

        # Parse input
        if isinstance(input, dict):
            spec = input
        elif isinstance(input, list) and len(input) > 0 and isinstance(input[0], dict):
            spec = input[0]
        else:
            line = str(input).strip()
            parts = [p.strip() for p in line.split("|")]
            action_raw = parts[0].lower() if parts else "list"

            if action_raw in ("attach", "attach_dwg"):
                spec = {
                    "action": "attach",
                    "path": parts[1] if len(parts) > 1 else "",
                    "insertion_point": parts[2] if len(parts) > 2 else "0,0",
                    "scale": float(parts[3]) if len(parts) > 3 else 1.0,
                    "rotation": float(parts[4]) if len(parts) > 4 else 0.0,
                }
            elif action_raw in ("raster", "attach_raster"):
                spec = {
                    "action": "raster",
                    "path": parts[1] if len(parts) > 1 else "",
                    "insertion_point": parts[2] if len(parts) > 2 else "0,0",
                    "scale": float(parts[3]) if len(parts) > 3 else 1.0,
                }
            elif action_raw in ("reload", "detach"):
                spec = {"action": action_raw, "name": parts[1] if len(parts) > 1 else ""}
            else:
                spec = {"action": "list"}

        action = spec.get("action", "list").lower()
        handler = XREF_DISPATCH.get(action)
        if not handler:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Unknown XREF action '{action}'. Supported: "
                    + ", ".join(XREF_DISPATCH.keys()),
                },
                indent=2,
            )

        res = handler(adapter, spec)
        return json.dumps(res, indent=2)
