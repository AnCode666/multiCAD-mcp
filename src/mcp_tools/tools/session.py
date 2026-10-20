"""
Unified session management tool.

Replaces 7 individual tools with 1:
- manage_session: connect_cad, disconnect_cad, list_supported_cads,
                  get_connection_status, zoom_extents, undo, redo (7→1)

Covers all non-content operations: connection lifecycle, view, and history.
"""

import json
import logging
import webbrowser
from typing import Optional, Dict, Any, Callable, List, Tuple


from core import get_supported_cads, CADConnectionError, get_config
from adapters.adapter_manager import (
    get_cad_instances,
    get_adapter,
    shutdown_all,
    auto_detect_cad,
)

logger = logging.getLogger(__name__)


def _refresh_cache_safe():
    """Refresh dashboard cache, ignoring errors if dashboard not loaded."""
    try:
        from web.api import refresh_dashboard_cache

        refresh_dashboard_cache()
    except Exception as e:
        logger.debug(f"Dashboard cache refresh skipped: {e}")


# ========== Action Handlers ==========


def _connect(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Connect to a running or launchable CAD application.

    Args:
        spec: Operation spec (no required keys).

    Returns:
        Dict with keys: success (bool), detail (str).
    """
    try:
        _adapter = get_adapter(only_if_running=False)
        from adapters.adapter_manager import get_active_cad_type

        cad_type = get_active_cad_type()
        logger.info(f"Connected to {cad_type}")
        _refresh_cache_safe()
        return {"success": True, "detail": f"Connected to {cad_type}"}
    except Exception as e:
        return {"success": False, "detail": str(e)}


def _disconnect(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Disconnect from the active CAD application.

    Args:
        spec: Operation spec (no required keys).

    Returns:
        Dict with keys: success (bool), detail (str).
    """
    try:
        shutdown_all()
        _refresh_cache_safe()
        return {"success": True, "detail": "Disconnected."}
    except Exception as e:
        logger.error(f"Disconnection error: {e}")
        return {"success": False, "detail": f"Error disconnecting: {e}"}


def _status(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return the current connection status for all CAD instances.

    Args:
        spec: Operation spec (no required keys).

    Returns:
        Dict with keys: success (bool), status (dict mapping cad type to status string).
    """
    instances = get_cad_instances()
    if instances:
        return {"success": True, "status": {k: "connected" for k in instances.keys()}}
    return {"success": True, "status": {"all": "disconnected"}}


def _list_supported(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return the list of supported CAD application types.

    Args:
        spec: Operation spec (no required keys).

    Returns:
        Dict with keys: success (bool), supported (list).
    """
    supported = get_supported_cads()
    return {"success": True, "supported": list(supported)}


def _zoom_extents(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Zoom the view to show all entities in the drawing.

    Args:
        spec: Operation spec (no required keys).

    Returns:
        Dict with keys: success (bool), detail (str).
    """
    adapter = get_adapter()
    success = adapter.zoom_extents()
    return {
        "success": success,
        "detail": "Zoomed to extents" if success else "Failed to zoom",
    }


def _undo(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Undo one or more recent actions.

    Args:
        spec: Operation spec with keys: count (int, optional, default 1).

    Returns:
        Dict with keys: success (bool), detail (str).
    """
    adapter = get_adapter()
    count = spec.get("count", 1)
    success = adapter.undo(count=count)
    if success:
        detail = "Action undone" if count == 1 else f"{count} actions undone"
    else:
        detail = "Failed to undo"
    return {"success": success, "detail": detail}


def _redo(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Redo one or more previously undone actions.

    Args:
        spec: Operation spec with keys: count (int, optional, default 1).

    Returns:
        Dict with keys: success (bool), detail (str).
    """
    adapter = get_adapter()
    count = spec.get("count", 1)
    success = adapter.redo(count=count)
    if success:
        detail = "Action redone" if count == 1 else f"{count} actions redone"
    else:
        detail = "Failed to redo"
    return {"success": success, "detail": detail}


def _screenshot(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Capture window screenshot including UI chrome."""
    adapter = get_adapter()
    try:
        result = adapter.get_screenshot()
        return {
            "success": True,
            "detail": f"Screenshot saved to {result['path']}",
            "path": result["path"],
            "data": result["data"],
        }
    except Exception as e:
        return {"success": False, "detail": str(e)}


def _export_view(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Export view using internal rendering (no UI, works when obscured)."""
    adapter = get_adapter()
    try:
        result = adapter.export_view()
        return {
            "success": True,
            "detail": f"View exported to {result['path']}",
            "path": result["path"],
            "data": result["data"],
        }
    except Exception as e:
        return {"success": False, "detail": str(e)}


def _check_running(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Check if any supported CAD is running without launching it."""
    auto_detect_cad(only_if_running=True)
    instances = get_cad_instances()

    if instances:
        _refresh_cache_safe()
        return {
            "success": True,
            "any_running": True,
            "running_cad_types": list(instances.keys()),
        }

    return {"success": True, "any_running": False, "running_cad_types": []}


def _open_dashboard(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Open the web dashboard in the default browser."""
    # import webbrowser

    config = get_config()
    host = spec.get("host", config.dashboard.host)
    port = spec.get("port", config.dashboard.port)
    url = f"http://{host}:{port}"
    try:
        webbrowser.open(url)
        return {"success": True, "detail": f"Dashboard opened at {url}"}
    except Exception as e:
        return {"success": False, "detail": f"Failed to open dashboard: {e}"}


def _zoom_window(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Zoom view to window bounding box."""
    from mcp_tools.helpers import parse_coordinate

    adapter = get_adapter()
    c1 = parse_coordinate(spec.get("corner1", "0,0"))
    c2 = parse_coordinate(spec.get("corner2", "100,100"))
    success = adapter.zoom_window(c1, c2)
    return {
        "success": success,
        "detail": f"Zoomed window from {c1} to {c2}" if success else "Failed to zoom window",
    }


def _zoom_center(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Zoom view centered on coordinate."""
    from mcp_tools.helpers import parse_coordinate

    adapter = get_adapter()
    center = parse_coordinate(spec.get("center", "0,0"))
    mag = float(spec.get("magnification", 1.0))
    success = adapter.zoom_center(center, mag)
    return {
        "success": success,
        "detail": f"Zoomed center at {center} (mag: {mag})" if success else "Failed to zoom center",
    }


def _set_view_preset(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Set orthographic or isometric 3D view preset."""
    adapter = get_adapter()
    preset = str(spec.get("preset", "top"))
    success = adapter.set_view_preset(preset)
    return {
        "success": success,
        "detail": f"Set view preset to '{preset}'" if success else f"Failed to set view preset to '{preset}'",
    }


def _set_visual_style(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Set visual style (wireframe, conceptual, realistic, shaded)."""
    adapter = get_adapter()
    style = str(spec.get("style", "wireframe"))
    success = adapter.set_visual_style(style)
    return {
        "success": success,
        "detail": f"Set visual style to '{style}'" if success else f"Failed to set visual style to '{style}'",
    }


# Dispatch table: action -> (handler, required_fields)
SESSION_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "connect": (_connect, []),
    "disconnect": (_disconnect, []),
    "status": (_status, []),
    "list_supported": (_list_supported, []),
    "check_running": (_check_running, []),
    "zoom_extents": (_zoom_extents, []),
    "zoom_window": (_zoom_window, ["corner1", "corner2"]),
    "zoom_center": (_zoom_center, ["center"]),
    "set_view_preset": (_set_view_preset, ["preset"]),
    "set_visual_style": (_set_visual_style, ["style"]),
    "undo": (_undo, []),
    "redo": (_redo, []),
    "screenshot": (_screenshot, []),
    "export_view": (_export_view, []),
    "open_dashboard": (_open_dashboard, []),
}


def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], action: str
) -> Optional[str]:
    """Validate that required fields are present in spec.

    Args:
        spec: Operation spec dict to validate.
        required: List of field names that must be present.
        action: Action name used in the error message.

    Returns:
        Error message string if any fields are missing, otherwise None.
    """
    missing = [f for f in required if f not in spec]
    if missing:
        return f"'{action}' requires fields: {', '.join(missing)}"
    return None


# ========== Tool Registration ==========


def register_session_tools(mcp):
    """Register unified session management tool with FastMCP."""

    @mcp.tool()
    def manage_session(
        operations: str,
    ) -> str:
        """
        Manage CAD session: connection, view, and history operations.

        Args:
            operations: JSON array of operations. Each object must include
                        an "action" field.

                Supported actions and their fields:

                Connection:
                - connect:        (no fields) — launches and connects to auto-detected CAD
                - disconnect:     (no fields) — disconnects from CAD
                - status:         (no fields) — shows connection status
                - list_supported: (no fields) — lists available CAD applications
                - check_running:  (no fields) — checks for running CAD without launching

                View:
                - zoom_extents:   (no fields) — zoom to show all entities
                - screenshot:     (no fields) — capture window screenshot (includes UI chrome)
                - export_view:    (no fields) — export view using internal rendering (pure drawing, works when window is obscured)

                History:
                - undo:           [count] (default count: 1)
                - redo:           [count] (default count: 1)

                Dashboard:
                - open_dashboard: [host, port] — open web dashboard in browser (default from config.json)

                Example:
                [
                    {"action": "connect"},
                    {"action": "zoom_extents"},
                    {"action": "undo", "count": 3}
                ]

                Operations execute sequentially.

        Returns:
            JSON result with per-operation status
        """
        from mcp_tools.shorthand import parse_session_input

        try:
            ops_data = parse_session_input(operations)
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid session operation input: {str(e)}",
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
                        + ", ".join(SESSION_DISPATCH.keys()),
                    }
                )
                continue

            action_lower = action.lower()
            dispatch_entry = SESSION_DISPATCH.get(action_lower)

            if not dispatch_entry:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": f"Unknown action '{action}'. Supported: "
                        + ", ".join(SESSION_DISPATCH.keys()),
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
            except CADConnectionError as e:
                logger.error(f"Connection error in op {i} ({action_lower}): {e}")
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": str(e),
                    }
                )
            except Exception as e:
                logger.error(f"Error in session op {i} ({action_lower}): {e}")
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

    @mcp.tool()
    def manage_view(
        operations: str,
    ) -> str:
        """
        Manage CAD viewport, camera zoom, view presets, and visual styles.

        Shorthand:
        - ze (or zoom_extents): Zoom to fit all entities
        - zw|x1,y1|x2,y2 (or zoom_window): Zoom into bounding box
        - zc|x,y|mag (or zoom_center): Center view on coordinate
        - preset|top|bottom|front|back|left|right|sw_iso|se_iso: Set 3D or orthographic projection
        - style|2d|wireframe|conceptual|realistic|shaded: Set visual rendering style
        - screenshot / preview: Capture visual snapshot of the drawing
        - undo|count / redo|count: History navigation
        """
        return manage_session(operations)
