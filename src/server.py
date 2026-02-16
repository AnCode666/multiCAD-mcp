"""
multiCAD-MCP Server

Fast, extensible MCP server for controlling multiple CAD applications.

Uses FastMCP framework for clean, decorator-based tool definition.
Supports AutoCAD, ZWCAD, GstarCAD, and other COM-compatible CAD software.
"""

import sys

from fastmcp import FastMCP

from __version__ import __version__, __title__
from core import get_supported_cads
from mcp_tools.helpers import setup_utf8_encoding, setup_logging
from mcp_tools.tools import (
    register_session_tools,
    register_drawing_tools,
    register_layer_tools,
    register_file_tools,
    register_entity_tools,
    register_export_tools,
    register_block_tools,
)
from web.api import api_app

# Setup at module load
setup_utf8_encoding()
logger = setup_logging()

# Initialize FastMCP server
mcp = FastMCP(name=__title__)


def register_all_tools():
    """Register all MCP tools with FastMCP.

    Organizes tools by category:
    - Session management (connection, view, history)
    - Drawing operations
    - Layer management
    - File operations
    - Entity selection and manipulation
    - Block management
    - Export and data extraction
    """
    logger.info("Registering MCP tools...")

    register_session_tools(mcp)
    logger.debug("  ✓ Session tools registered")

    register_drawing_tools(mcp)
    logger.debug("  ✓ Drawing tools registered")

    register_layer_tools(mcp)
    logger.debug("  ✓ Layer tools registered")

    register_file_tools(mcp)
    logger.debug("  ✓ File tools registered")

    register_entity_tools(mcp)
    logger.debug("  ✓ Entity tools registered")

    register_block_tools(mcp)
    logger.debug("  ✓ Block tools registered")

    register_export_tools(mcp)
    logger.debug("  ✓ Export tools registered")

    logger.info("All MCP tools registered successfully")


# Register tools at module load
register_all_tools()

# CAD connection is lazy-loaded on first tool use
logger.info(f"Starting multiCAD-MCP server v{__version__}...")
logger.info(f"Supported CAD types: {', '.join(get_supported_cads())}")
logger.info("CAD applications will be connected on first tool use (lazy loading)")


if __name__ == "__main__":
    import threading
    import uvicorn

    # Configuration
    host = "127.0.0.1"
    port = 8000

    # Autodetect transport mode:
    # - If stdin is a TTY (interactive terminal) → HTTP with dashboard
    # - If stdin is a pipe (Claude Desktop, etc.) → stdio
    use_stdio = not sys.stdin.isatty()

    def run_dashboard():
        """Helper to run uvicorn in a thread."""
        logger.info(f"Starting dashboard on http://{host}:{port}")
        uvicorn.run(api_app, host=host, port=port, log_level="warning")

    try:
        if use_stdio:
            logger.info("Starting multiCAD-MCP server in stdio mode...")

            # Start dashboard in background
            web_thread = threading.Thread(target=run_dashboard, daemon=True)
            web_thread.start()

            # Start background refresher thread
            def refresher_loop():
                """Wait for refresh events or timeout to update the dashboard cache."""
                from web.api import refresh_event, refresh_done_event, refresh_dashboard_cache
                logger.debug("Refresher thread started")
                while True:
                    # Wait for manual refresh or 30s auto-refresh
                    event_set = refresh_event.wait(timeout=30.0)
                    if event_set:
                        logger.info("Manual dashboard refresh requested via API")
                        refresh_event.clear()
                    
                    try:
                        refresh_dashboard_cache()
                    except Exception as e:
                        logger.error(f"Error in background cache refresh: {e}")
                    finally:
                        # Always signal completion if an event was waiting
                        if event_set:
                            refresh_done_event.set()

            refresher_thread = threading.Thread(target=refresher_loop, daemon=True)
            refresher_thread.start()

            # Run MCP stdio
            mcp.run(transport="stdio")
        else:
            logger.info("Starting multiCAD-MCP server in HTTP mode...")

            # Mount dashboard on the same app
            # Note: FastMCP.http_app allows mounting additional FastAPI apps
            app = mcp.http_app()
            app.mount("/", api_app)

            logger.info(f"Access dashboard at http://{host}:{port}/")
            logger.info(f"MCP endpoint at http://{host}:{port}/mcp")

            uvicorn.run(app, host=host, port=port)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
