"""
Unified file management tool.

Replaces 5 individual tools with 1 using a simple shorthand format
for ~85% token reduction.

SHORTHAND FORMAT (one per line):
    save|path_or_filename|format  → save|/path/to/file.dwg
    save|filename                 → save|backup.dwg
    new                           → new
    close|save_changes            → close|true
    list                          → list
    switch|drawing_name           → switch|floor_plan.dwg
"""

import json
import logging
import os
from typing import Optional, Dict, Any, Callable, List, Tuple

from mcp.server.fastmcp import Context

from core import get_config
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.shorthand import parse_file_ops_input

logger = logging.getLogger(__name__)


# ========== Action Handlers ==========


def _save(spec: Dict[str, Any]) -> Dict[str, Any]:
    filepath = spec.get("filepath", "")
    filename = spec.get("filename", "")
    fmt = spec.get("format", "dwg")

    success = get_current_adapter().save_drawing(
        filepath=filepath, filename=filename, format=fmt
    )

    if success:
        if filepath:
            saved_path = filepath
        elif filename:
            config = get_config()
            output_dir = os.path.abspath(os.path.expanduser(config.output.directory))
            saved_path = os.path.join(output_dir, filename)
        else:
            saved_path = None

        result = {"success": True, "detail": "Drawing saved"}
        if saved_path:
            result["path"] = saved_path
        return result

    return {"success": False, "detail": "Failed to save drawing"}


def _new(spec: Dict[str, Any]) -> Dict[str, Any]:
    success = get_current_adapter().new_drawing()
    return {
        "success": success,
        "detail": "New drawing created" if success else "Failed to create drawing",
    }


def _close(spec: Dict[str, Any]) -> Dict[str, Any]:
    save_changes = spec.get("save_changes", False)
    adapter = get_current_adapter()
    success = adapter.close_drawing(save_changes=save_changes)

    if success:
        action = "saved and closed" if save_changes else "closed without saving"
        open_drawings = adapter.get_open_drawings()
        detail = f"Drawing {action}"
        if open_drawings:
            detail += f". Switched to: {open_drawings[0]}"
        else:
            detail += ". No other drawings open"
        return {"success": True, "detail": detail}

    return {"success": False, "detail": "Failed to close drawing"}


def _list(spec: Dict[str, Any]) -> Dict[str, Any]:
    drawings = get_current_adapter().get_open_drawings()
    if not drawings:
        return {
            "success": True,
            "count": 0,
            "drawings": [],
            "detail": "No drawings open",
        }
    return {"success": True, "count": len(drawings), "drawings": drawings}


def _switch(spec: Dict[str, Any]) -> Dict[str, Any]:
    drawing_name = spec["drawing_name"]
    adapter = get_current_adapter()
    success = adapter.switch_drawing(drawing_name)

    if success:
        return {"success": True, "detail": f"Switched to: {drawing_name}"}

    available = adapter.get_open_drawings()
    return {
        "success": False,
        "detail": f"Drawing '{drawing_name}' not found",
        "available": available if available else [],
    }


# Dispatch table: action -> (handler, required_fields)
FILE_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "save": (_save, []),
    "new": (_new, []),
    "close": (_close, []),
    "list": (_list, []),
    "switch": (_switch, ["drawing_name"]),
}


def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], action: str
) -> Optional[str]:
    missing = [f for f in required if f not in spec]
    if missing:
        return f"'{action}' requires fields: {', '.join(missing)}"
    return None


# ========== Tool Registration ==========


def register_file_tools(mcp):
    """Register unified file management tool with FastMCP."""

    @cad_tool(mcp, "manage_files")
    def manage_files(
        ctx: Context,
        operations: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Manage drawing files with one or more operations in a single call.

        Args:
            operations: Operations in SHORTHAND format (one per line):

                save|path_or_filename|format  → save|/path/to/file.dwg
                save|filename                 → save|backup.dwg
                new                           → new
                close|save_changes            → close|true
                list                          → list
                switch|drawing_name           → switch|floor_plan.dwg

                "format" = "dwg" (default), "dxf", "pdf"
                "save_changes" = true/false (default: false)

                Example:
                    save|backup.dwg
                    new
                    switch|floor_plan.dwg

                JSON format also supported for backwards compatibility.

            cad_type: CAD application to use

        Returns:
            JSON result with per-operation status
        """
        try:
            ops_data = parse_file_ops_input(operations)
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
                        + ", ".join(FILE_DISPATCH.keys()),
                    }
                )
                continue

            action_lower = action.lower()
            dispatch_entry = FILE_DISPATCH.get(action_lower)

            if not dispatch_entry:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": f"Unknown action '{action}'. Supported: "
                        + ", ".join(FILE_DISPATCH.keys()),
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
            except Exception as e:
                logger.error(f"Error in file op {i} ({action_lower}): {e}")
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
