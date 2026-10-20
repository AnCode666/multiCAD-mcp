import collections
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from __version__ import __version__
from adapters.adapter_manager import AdapterRegistry, get_active_cad_type
from core import get_supported_cads

logger = logging.getLogger(__name__)


# ---------- In-memory log buffer for dashboard console ----------


class _LogBuffer:
    """Thread-safe circular buffer for log records."""

    def __init__(self, maxlen: int = 500):
        self._lock = threading.Lock()
        self._entries: collections.deque = collections.deque(maxlen=maxlen)
        self._seq = 0

    def append(self, level: str, name: str, msg: str, time_str: str) -> None:
        with self._lock:
            self._seq += 1
            self._entries.append(
                {
                    "seq": self._seq,
                    "time": time_str,
                    "level": level,
                    "name": name,
                    "msg": msg,
                }
            )

    def since(self, seq: int) -> list:
        with self._lock:
            return [e for e in self._entries if e["seq"] > seq]


class _MemoryLogHandler(logging.Handler):
    """Logging handler that stores records in _LogBuffer."""

    def __init__(self, buffer: _LogBuffer):
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from datetime import datetime

            time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            self._buffer.append(
                level=record.levelname,
                name=record.name,
                msg=record.getMessage(),
                time_str=time_str,
            )
        except Exception:
            self.handleError(record)


log_buffer = _LogBuffer(maxlen=500)
log_handler = _MemoryLogHandler(log_buffer)
log_handler.setLevel(logging.INFO)

# FastAPI App
api_app = FastAPI(title="multiCAD-MCP Dashboard API")


@api_app.post("/api/cad/export")
async def api_cad_export() -> dict:
    """Trigger an Excel export."""
    if not _cache.get("connected"):
        return {"success": False, "detail": "No CAD connection"}

    try:
        from adapters.adapter_manager import get_adapter

        adapter = get_adapter(only_if_running=True)
        if adapter:
            success = adapter.export_to_excel()
            return {
                "success": success,
                "detail": "Exportado con éxito" if success else "Error al exportar",
            }
        else:
            return {
                "success": False,
                "detail": "No se encontró un adaptador CAD activo",
            }
    except Exception as e:
        logger.error(f"Error in export: {e}")
        return {"success": False, "detail": f"Error: {str(e)}"}


@api_app.post("/api/cad/refresh")
async def api_cad_trigger_refresh() -> dict:
    """Trigger a manual refresh directly."""
    try:
        refresh_dashboard_cache()
        return {"success": True, "detail": "Refresh completed"}
    except Exception as e:
        logger.error(f"Error refreshing dashboard: {e}")
        return {"success": False, "detail": str(e)}


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
            "entities": [],  # Active drawing entities
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
    try:
        from adapters.adapter_manager import get_adapter, get_active_cad_type
        from core import CADConnectionError

        try:
            adapter = get_adapter(only_if_running=True)
            active = get_active_cad_type()
        except CADConnectionError:
            adapter = None
            active = "None"

    except Exception as e:
        logger.error(f"Error getting adapter for dashboard refresh: {e}")
        adapter = None
        active = "None"

    if adapter is None:
        # If we had a connection before, don't immediately clear it on a refresh failure
        # as it might just be a temporary COM/threading issue in the refresher thread.
        # Only clear if we are SURE it's not running (already handled by auto_detect_cad)
        if not _cache.get("connected"):
            _cache.update(
                connected=False,
                cad_type="None",
                drawings=[],
                current_drawing="None",
                layers=[],
                blocks=[],
                entities=[],
            )
        else:
            logger.debug(
                "Keep existing cache state despite refresh failure (threading/COM context issue?)"
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
        # Ask adapter to verify if active document has changed behind the scenes
        if hasattr(adapter, "check_document_change"):
            adapter.check_document_change()

        # Single drawing extraction (Active Document)
        try:
            current_drawing = adapter.document.Name if adapter.document else "None"
        except Exception:
            current_drawing = "None"

        # Get all open drawings
        try:
            open_drawings = adapter.get_open_drawings()
        except Exception:
            open_drawings = [current_drawing] if current_drawing != "None" else []

        # 1. Get exact overall entity counts VERY fast (DXF SelectionSets)
        try:
            entity_counts = adapter.get_entity_counts()
            total_entities = sum(entity_counts.values())
        except Exception as e:
            logger.warning(f"Could not get fast entity counts: {e}")
            entity_counts = {}
            total_entities = 0

        # 2. Extract detailed entities only for a sample (max 1000) to prevent UI/COM freeze
        # We no longer extract a sample here. We fetch dynamically via /api/cad/entities.
        entities_info: list[dict] = []

        # 3. Get Layers info
        try:
            layers_info = adapter.get_layers_info(entity_data=None)
        except Exception as e:
            logger.error(f"Failed to get layers info: {e}")
            layers_info = _cache.get("layers", [])

        # 4. Get exact block insertion counts VERY fast
        try:
            insert_counts = adapter.get_block_counts()
        except Exception:
            insert_counts = {}

        # Build rich block dicts: list_blocks() returns List[str], we need List[dict]
        try:
            block_names: list = adapter.list_blocks()
        except Exception as e:
            logger.error(f"Failed to list blocks: {e}")
            block_names = []
        blocks_info: list = []
        for name in block_names:
            try:
                info = adapter.get_block_info(name)
                # Apply fast counts
                count = insert_counts.get(name, 0)
                if info:
                    info["Count"] = count
                    blocks_info.append(info)
                else:
                    blocks_info.append({"Name": name, "ObjectCount": 0, "Count": count})
            except Exception:
                blocks_info.append(
                    {
                        "Name": name,
                        "ObjectCount": 0,
                        "Count": insert_counts.get(name, 0),
                    }
                )

        _cache.update(
            connected=True,
            cad_type=active,
            drawings=open_drawings,
            current_drawing=current_drawing,
            layers=layers_info,
            blocks=blocks_info,
            entities=entities_info,  # Note: This is now a sample of max 1000
            entity_counts=entity_counts,  # New: Fast overview data
            total_entities=total_entities,  # New: Accurate total number
        )

        logger.info(
            f"Dashboard cache refreshed: {active}, drawing '{current_drawing}' — "
            f"Total Entities: {total_entities}, {len(layers_info)} layers, {len(blocks_info)} blocks."
        )
    except Exception as e:
        logger.error(f"Failed to refresh dashboard cache: {e}")


# ---------- Static files ----------
STATIC_DIR = Path(__file__).parent / "static"


class ProjectState:
    """Project state tracking."""

    def __init__(self):
        self.last_refresh = None


state = ProjectState()


class SwitchDrawingRequest(BaseModel):
    drawing_name: str


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
    return {"status": "ok", "version": __version__}


@api_app.get("/api/debug/registry")
async def api_debug_registry() -> dict:
    """Debug: check adapter registry and cache state."""
    registry = AdapterRegistry.get_instance()
    instances = registry.get_cad_instances()
    return {
        "registry_id": id(registry),
        "active_cad_type": get_active_cad_type(),
        "instances": list(instances.keys()),
        "cache": _cache.snapshot(),
    }


@api_app.post("/api/cad/switch_drawing")
async def api_cad_switch_drawing(request: SwitchDrawingRequest) -> dict:
    """Switch the active CAD drawing and trigger a cache refresh."""
    if not _cache.get("connected"):
        return {"success": False, "error": "No CAD connection"}

    from adapters.adapter_manager import get_adapter

    try:
        adapter = get_adapter(only_if_running=True)
    except Exception:
        return {"success": False, "error": "No active CAD adapter found"}

    try:
        adapter.switch_drawing(request.drawing_name)
        logger.info(f"Switched drawing to: {request.drawing_name}")

        # Trigger cache refresh synchronously
        refresh_dashboard_cache()

        return {"success": True, "message": f"Switching to {request.drawing_name}"}
    except Exception as e:
        logger.error(f"Failed to switch drawing: {e}")
        return {"success": False, "error": str(e)}


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
            "total_entities": _cache.get("total_entities", 0),
            "entity_counts": _cache.get("entity_counts", {}),
        },
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
async def api_cad_entities(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=500, ge=1, le=2000),
    type: Optional[str] = Query(default=None),
) -> dict:
    """Get entities from the active CAD drawing dynamically (paginated, by type)."""
    if not _cache.get("connected"):
        return {"success": False, "error": "No CAD connection"}

    try:
        from adapters.adapter_manager import get_adapter

        adapter = get_adapter(only_if_running=True)
        if hasattr(adapter, "check_document_change"):
            adapter.check_document_change()

        # Map friendly name or internal count key to DXF name
        # Values are lists of DXF types to try in order.
        mapping = {
            # Friendly (Spanish)
            "Línea": ["LINE"],
            "Polilínea": ["LWPOLYLINE", "POLYLINE"],
            "Círculo": ["CIRCLE"],
            "Arco": ["ARC"],
            "Bloque": ["INSERT"],
            "Texto": ["TEXT", "MTEXT"],
            "Cota": ["DIMENSION"],
            "Spline": ["SPLINE"],
            "Punto": ["POINT"],
            "Sombreado": ["HATCH"],
            # Internal (English - from get_entity_counts)
            "Line": ["LINE"],
            "Polyline": ["LWPOLYLINE", "POLYLINE"],
            "Polyline2D": ["POLYLINE", "LWPOLYLINE"],
            "Circle": ["CIRCLE"],
            "Arc": ["ARC"],
            "Block": ["INSERT"],
            "Text": ["TEXT", "MTEXT"],
            "MText": ["MTEXT", "TEXT"],
            "Dimension": ["DIMENSION"],
            "Point": ["POINT"],
            "Hatch": ["HATCH"],
        }

        requested_types = mapping.get(type) if type else None
        if type and not requested_types:
            requested_types = [type]

        offset = (page - 1) * limit
        entities = []
        dxf_type = None

        if requested_types:
            # Try types in order until we find some entities or run out of types
            for t_variant in requested_types:
                res_entities = adapter.extract_drawing_data(
                    only_selected=False,
                    limit=limit,
                    offset=offset,
                    entity_type=t_variant,
                )
                if res_entities:
                    entities = res_entities
                    dxf_type = t_variant
                    break

            # If still nothing after all variants, ensure we tried at least the first one for consistency
            if not entities and requested_types:
                dxf_type = requested_types[0]
        else:
            # Global extraction
            entities = adapter.extract_drawing_data(
                only_selected=False, limit=limit, offset=offset
            )

        # Get total for this specific type or global
        entity_counts = _cache.get("entity_counts", {})
        total_items = (
            entity_counts.get(type, 0) if type else _cache.get("total_entities", 0)
        )

        return {
            "success": True,
            "entities": entities,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_items,
                "total_pages": (total_items + limit - 1) // limit
                if total_items > 0
                else 1,
                "type": type,
                "dxf_type": dxf_type,
            },
        }
    except Exception as e:
        logger.error(f"Failed to extract entities: {e}")
        return {"success": False, "error": str(e)}


@api_app.get("/api/cad/drawings")
async def api_cad_drawings() -> dict:
    """Get summary of all open drawings (from cache)."""
    if not _cache.get("connected"):
        return {"success": False, "error": "No CAD connection"}

    drawing_names = _cache.get("drawings", [])
    current = _cache.get("current_drawing", "None")

    drawings_info = []
    for name in drawing_names:
        drawings_info.append(
            {
                "name": name,
                "is_active": name == current,
            }
        )

    return {"success": True, "drawings": drawings_info, "current": current}


@api_app.get("/api/logs")
async def api_logs(since: int = Query(default=0, ge=0)) -> dict:
    """Get server log entries newer than the given sequence number."""
    return {"success": True, "entries": log_buffer.since(since)}


# Mount static files (at the end to not shadow API routes)
if STATIC_DIR.exists():
    api_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")
