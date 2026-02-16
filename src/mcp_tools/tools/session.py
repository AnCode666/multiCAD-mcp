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



from core import get_supported_cads, CADConnectionError
from adapters import AutoCADAdapter
from adapters.adapter_manager import get_cad_instances, get_adapter, set_active_cad_type

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
    cad_type = spec.get("cad_type", "autocad").lower()
    cad_instances = get_cad_instances()

    if cad_type in cad_instances and cad_instances[cad_type].is_connected():
        set_active_cad_type(cad_type)
        _refresh_cache_safe()
        return {"success": True, "detail": f"Already connected to {cad_type}"}

    try:
        adapter = AutoCADAdapter(cad_type)
        adapter.connect()
        cad_instances[cad_type] = adapter
        set_active_cad_type(cad_type)
        logger.info(f"Connected to {cad_type}")
        _refresh_cache_safe()
        return {"success": True, "detail": f"Connected to {cad_type}"}
    except CADConnectionError:
        raise
    except Exception as e:
        raise CADConnectionError(cad_type, str(e))


def _disconnect(spec: Dict[str, Any]) -> Dict[str, Any]:
    cad_type = spec.get("cad_type", "autocad").lower()
    cad_instances = get_cad_instances()

    if cad_type not in cad_instances:
        return {"success": True, "detail": f"Not connected to {cad_type}"}

    try:
        cad_instances[cad_type].disconnect()
        del cad_instances[cad_type]
        logger.info(f"Disconnected from {cad_type}")
        return {"success": True, "detail": f"Disconnected from {cad_type}"}
    except Exception as e:
        logger.error(f"Disconnection error: {e}")
        return {"success": False, "detail": f"Error disconnecting: {e}"}


def _status(spec: Dict[str, Any]) -> Dict[str, Any]:
    cad_instances = get_cad_instances()
    status = {}
    for cad_type in get_supported_cads():
        if cad_type in cad_instances:
            is_connected = cad_instances[cad_type].is_connected()
            status[cad_type] = "connected" if is_connected else "disconnected"
        else:
            status[cad_type] = "not initialized"
    return {"success": True, "status": status}


def _list_supported(spec: Dict[str, Any]) -> Dict[str, Any]:
    supported = get_supported_cads()
    return {"success": True, "supported": list(supported)}


def _zoom_extents(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_adapter(spec.get("cad_type"))
    success = adapter.zoom_extents()
    return {
        "success": success,
        "detail": "Zoomed to extents" if success else "Failed to zoom",
    }


def _undo(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_adapter(spec.get("cad_type"))
    count = spec.get("count", 1)
    success = adapter.undo(count=count)
    if success:
        detail = "Action undone" if count == 1 else f"{count} actions undone"
    else:
        detail = "Failed to undo"
    return {"success": success, "detail": detail}


def _redo(spec: Dict[str, Any]) -> Dict[str, Any]:
    adapter = get_adapter(spec.get("cad_type"))
    count = spec.get("count", 1)
    success = adapter.redo(count=count)
    if success:
        detail = "Action redone" if count == 1 else f"{count} actions redone"
    else:
        detail = "Failed to redo"
    return {"success": success, "detail": detail}


def _screenshot(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Capture window screenshot including UI chrome."""
    adapter = get_adapter(spec.get("cad_type"))
    try:
        result = adapter.get_screenshot()
        return {
            "success": True,
            "detail": f"Screenshot saved to {result['path']}",
            "path": result["path"],
            "data": result["data"]
        }
    except Exception as e:
        return {"success": False, "detail": str(e)}


def _export_view(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Export view using internal rendering (no UI, works when obscured)."""
    adapter = get_adapter(spec.get("cad_type"))
    try:
        result = adapter.export_view()
        return {
            "success": True,
            "detail": f"View exported to {result['path']}",
            "path": result["path"],
            "data": result["data"]
        }
    except Exception as e:
        return {"success": False, "detail": str(e)}


def _open_dashboard(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Open the web dashboard in the default browser."""
    host = spec.get("host", "127.0.0.1")
    port = spec.get("port", 8000)
    url = f"http://{host}:{port}"
    try:
        webbrowser.open(url)
        return {"success": True, "detail": f"Dashboard opened at {url}"}
    except Exception as e:
        return {"success": False, "detail": f"Failed to open dashboard: {e}"}


# Dispatch table: action -> (handler, required_fields)
SESSION_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "connect": (_connect, []),
    "disconnect": (_disconnect, []),
    "status": (_status, []),
    "list_supported": (_list_supported, []),
    "zoom_extents": (_zoom_extents, []),
    "undo": (_undo, []),
    "redo": (_redo, []),
    "screenshot": (_screenshot, []),
    "export_view": (_export_view, []),
    "open_dashboard": (_open_dashboard, []),
}


def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], action: str
) -> Optional[str]:
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
                - connect:        [cad_type] (default: "autocad")
                - disconnect:     [cad_type]
                - status:         (no fields) — shows connection status for all CAD types
                - list_supported: (no fields) — lists available CAD applications

                View:
                - zoom_extents:   [cad_type] — zoom to show all entities
                - screenshot:     [cad_type] — capture window screenshot (includes UI chrome)
                - export_view:    [cad_type] — export view using internal rendering (pure drawing, works when window is obscured)

                History:
                - undo:           [count, cad_type] (default count: 1)
                - redo:           [count, cad_type] (default count: 1)

                Dashboard:
                - open_dashboard: [host, port] — open web dashboard in browser (default: 127.0.0.1:8000)

                Example:
                [
                    {"action": "connect", "cad_type": "autocad"},
                    {"action": "zoom_extents"},
                    {"action": "undo", "count": 3}
                ]

                Operations execute sequentially.

        Returns:
            JSON result with per-operation status
        """
        try:
            ops_data = (
                json.loads(operations) if isinstance(operations, str) else operations
            )
            if not isinstance(ops_data, list):
                ops_data = [ops_data]
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
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
