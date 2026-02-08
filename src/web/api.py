import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from adapters.adapter_manager import get_adapter
from core import get_supported_cads

logger = logging.getLogger(__name__)

# FastAPI App
api_app = FastAPI(title="multiCAD-MCP Dashboard API")

# Static files path
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


@api_app.get("/api/cad/status")
async def api_cad_status() -> dict:
    """Get current CAD connection status."""
    try:
        adapter = None
        try:
            adapter = get_adapter()
        except Exception:
            pass

        connected = adapter is not None and adapter.is_connected()
        cad_type = adapter.cad_type if adapter else "None"

        drawings = []
        current_drawing = "None"

        if connected and adapter is not None:
            drawings = adapter.get_open_drawings()
            current_drawing = adapter.get_current_drawing_name()

        return {
            "connected": connected,
            "cad_type": cad_type,
            "drawings": drawings,
            "current_drawing": current_drawing,
            "supported": get_supported_cads(),
        }
    except Exception as e:
        logger.error(f"Error in api_cad_status: {e}")
        return {"connected": False, "error": str(e)}


@api_app.get("/api/cad/layers")
async def api_cad_layers() -> dict:
    """Get layers from the active CAD drawing."""
    try:
        adapter = get_adapter()

        if not adapter or not adapter.is_connected():
            return {"success": False, "error": "No CAD connection"}

        layers = adapter.get_layers_info()
        return {"success": True, "layers": layers}
    except Exception as e:
        logger.error(f"Error in api_cad_layers: {e}")
        return {"success": False, "error": str(e)}


@api_app.get("/api/cad/blocks")
async def api_cad_blocks() -> dict:
    """Get block definitions from the active CAD drawing."""
    try:
        adapter = get_adapter()

        if not adapter or not adapter.is_connected():
            return {"success": False, "error": "No CAD connection"}

        blocks = adapter.list_blocks()
        return {"success": True, "blocks": blocks}
    except Exception as e:
        logger.error(f"Error in api_cad_blocks: {e}")
        return {"success": False, "error": str(e)}


# Mount static files (at the end to not shadow API routes)
if STATIC_DIR.exists():
    api_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")
