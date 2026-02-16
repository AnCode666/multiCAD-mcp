import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from adapters.adapter_manager import AdapterRegistry
from core import get_supported_cads

logger = logging.getLogger(__name__)

# FastAPI App
api_app = FastAPI(title="multiCAD-MCP Dashboard API")

# Bridge events for manual refresh requests
# The web thread (dashboard) sets refresh_event, and the MCP thread (refresher) 
# waits for it to trigger a refresh_dashboard_cache() call.
# Once finished, it sets refresh_done_event to release the web thread.
refresh_event = threading.Event()
refresh_done_event = threading.Event()


@api_app.post("/api/cad/refresh")
async def api_cad_trigger_refresh() -> dict:
    """Trigger a manual refresh and wait for completion."""
    refresh_done_event.clear()
    refresh_event.set()
    
    # Wait for completion (max 20s for large drawings)
    # We do this in a blocking way because it's a dedicated worker thread in FastAPI
    finished = refresh_done_event.wait(timeout=20.0)
    
    if finished:
        return {"success": True, "detail": "Refresh completed"}
    else:
        return {"success": False, "detail": "Refresh timed out"}


# ---------- Thread-safe dashboard cache ----------
# COM objects cannot be accessed cross-thread on Windows (STA threading).
# The MCP thread calls refresh_dashboard_cache() after connecting or
# performing operations, and the dashboard thread just reads the cache.

class DashboardCache:
    """Thread-safe cache for dashboard data.
    
    Populated by the MCP thread (which owns the COM objects).
    Read by the dashboard web thread (which cannot touch COM).
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            "connected": False,
            "cad_type": "None",
            "drawings": [],
            "current_drawing": "None",
            "layers": [],  # Active drawing layers
            "blocks": [],  # Active drawing blocks
            "entities": [], # Active drawing entities
        }
    
    def update(self, **kwargs):
        """Update cache from MCP thread."""
        with self._lock:
            self._data.update(kwargs)
    
    def get(self, key: str, default=None):
        """Read cache from dashboard thread."""
        with self._lock:
            return self._data.get(key, default)
    
    def snapshot(self) -> Dict[str, Any]:
        """Get a full copy of the cache."""
        with self._lock:
            return dict(self._data)


_cache = DashboardCache()


def refresh_dashboard_cache():
    """Refresh the dashboard cache from the current CAD connection.
    
    MUST be called from the MCP thread (which owns COM objects).
    Called automatically after connect, or can be triggered manually.
    """
    registry = AdapterRegistry.get_instance()
    active = registry._active_cad_type
    instances = registry.get_cad_instances()
    
    adapter = None
    if active and active in instances:
        adapter = instances[active]
    elif instances:
        active = next(iter(instances))
        adapter = instances[active]
    
    # If no adapter found or not connected, try to auto-detect
    if adapter is None:
        try:
            logger.info("No active adapter found for dashboard, trying auto-detect...")
            from adapters.adapter_manager import auto_detect_cad
            auto_detect_cad()
            
            # Re-check registry after auto-detect
            active = registry._active_cad_type
            instances = registry.get_cad_instances()
            if active and active in instances:
                adapter = instances[active]
        except Exception as e:
            logger.error(f"Auto-detect failed during refresh: {e}")
    
    if adapter is None:
        _cache.update(
            connected=False,
            cad_type="None",
            drawings=[],
            current_drawing="None",
            layers=[],
            blocks=[],
            entities=[],
        )
        return
    
    try:
        connected = adapter.is_connected()
    except Exception:
        connected = False
    
    if not connected:
        _cache.update(connected=False, cad_type=active or "None")
        return
    
    try:
        # Single drawing extraction (Active Document)
        current_drawing = adapter.get_current_drawing_name()
        layers_info = adapter.get_layers_info()
        blocks_info = adapter.list_blocks()
        entities_info = adapter.extract_drawing_data(only_selected=False)
        
        _cache.update(
            connected=True,
            cad_type=active,
            drawings=[current_drawing],
            current_drawing=current_drawing,
            layers=layers_info,
            blocks=blocks_info,
            entities=entities_info,
        )
        
        logger.info(f"Dashboard cache refreshed: {active}, "
                    f"Active drawing '{current_drawing}' has {len(entities_info)} entities.")
    except Exception as e:
        logger.error(f"Failed to refresh dashboard cache: {e}")


# ---------- Static files ----------
STATIC_DIR = Path(__file__).parent / "static"


class ProjectState:
    """Project state tracking."""

    def __init__(self):
        self.last_refresh = None


state = ProjectState()


@api_app.get("/")
async def get_index() -> FileResponse:
    """Serve the main dashboard page."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)


@api_app.get("/api/health")
async def api_health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.3"}


@api_app.get("/api/debug/registry")
async def api_debug_registry() -> dict:
    """Debug: check adapter registry and cache state."""
    registry = AdapterRegistry.get_instance()
    instances = registry.get_cad_instances()
    return {
        "registry_id": id(registry),
        "active_cad_type": registry._active_cad_type,
        "instances": list(instances.keys()),
        "cache": _cache.snapshot(),
    }


@api_app.get("/api/cad/status")
async def api_cad_status() -> dict:
    """Get current CAD connection status (from cache)."""
    return {
        "success": True,
        "status": {
            "connected": _cache.get("connected", False),
            "cad_type": _cache.get("cad_type", "None"),
            "drawings": _cache.get("drawings", []),
            "current_drawing": _cache.get("current_drawing", "None"),
            "supported": get_supported_cads(),
        }
    }


@api_app.get("/api/cad/layers")
async def api_cad_layers() -> dict:
    """Get layers from the active CAD drawing (from cache)."""
    if not _cache.get("connected"):
        return {"success": False, "error": "No CAD connection"}
    return {"success": True, "layers": _cache.get("layers", [])}


@api_app.get("/api/cad/blocks")
async def api_cad_blocks() -> dict:
    """Get block definitions from the active CAD drawing (from cache)."""
    if not _cache.get("connected"):
        return {"success": False, "error": "No CAD connection"}
    return {"success": True, "blocks": _cache.get("blocks", [])}


@api_app.get("/api/cad/entities")
async def api_cad_entities() -> dict:
    """Get all entities from the active CAD drawing (from cache)."""
    if not _cache.get("connected"):
        return {"success": False, "error": "No CAD connection"}
    return {"success": True, "entities": _cache.get("entities", [])}


@api_app.get("/api/cad/drawings")
async def api_cad_drawings() -> dict:
    """Get summary of all open drawings (from cache)."""
    if not _cache.get("connected"):
        return {"success": False, "error": "No CAD connection"}

    drawing_names = _cache.get("drawings", [])
    current = _cache.get("current_drawing", "None")

    drawings_info = []
    for name in drawing_names:
        drawings_info.append({
            "name": name,
            "is_active": name == current,
        })

    return {"success": True, "drawings": drawings_info, "current": current}


# Mount static files (at the end to not shadow API routes)
if STATIC_DIR.exists():
    api_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")
