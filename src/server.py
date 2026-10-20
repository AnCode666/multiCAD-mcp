"""
multiCAD-MCP Server

Fast, extensible MCP server for controlling multiple CAD applications.

Uses FastMCP framework for clean, decorator-based tool definition.
Supports AutoCAD, ZWCAD, GstarCAD, and other COM-compatible CAD software.
"""

import sys
import logging

from fastmcp import FastMCP

from __version__ import __version__, __title__
from core import get_supported_cads, get_config
from mcp_tools.helpers import setup_utf8_encoding, setup_logging
from mcp_tools.tools import (
    register_session_tools,
    register_drawing_tools,
    register_layer_tools,
    register_file_tools,
    register_entity_tools,
    register_export_tools,
    register_block_tools,
    register_interaction_tools,
    register_xref_tools,
    register_ce3x_bridge_tools,
    register_inspection_tools,
    register_annotation_tools,
    register_layout_tools,
)
from web.api import api_app, log_handler

# Setup at module load
setup_utf8_encoding()
logger = setup_logging()
logging.getLogger().addHandler(log_handler)

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
    - Human-in-the-Loop interaction
    - Drawing inspection and interactive HTML5 viewer
    - Smart architectural annotations
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

    register_interaction_tools(mcp)
    logger.debug("  ✓ Interaction tools registered")

    register_xref_tools(mcp)
    logger.debug("  ✓ XREF tools registered")

    register_ce3x_bridge_tools(mcp)
    logger.debug("  ✓ CE3X ConTech Bridge tools registered")

    register_inspection_tools(mcp)
    logger.debug("  ✓ Drawing inspection & viewer tools registered")

    register_annotation_tools(mcp)
    logger.debug("  ✓ Smart annotation tools registered")

    register_layout_tools(mcp)
    logger.debug("  ✓ Layout and sheet presentation tools registered")


    logger.info("All MCP tools registered successfully")


# Register tools at module load
register_all_tools()

# CAD connection is lazy-loaded on first tool use
logger.info(f"Starting multiCAD-MCP server v{__version__}...")
logger.info(f"Supported CAD types: {', '.join(get_supported_cads())}")
logger.info("CAD applications will be connected on first tool use (lazy loading)")


def main():
    """Main entrypoint for multiCAD-MCP server."""
    import argparse
    import threading
    import uvicorn

    parser = argparse.ArgumentParser(
        description=f"multiCAD-MCP Server v{__version__} - MCP Server for CAD control"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=None,
        help="Transport mode (stdio or http). Autodetected if not specified.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host for HTTP dashboard (default from config.json)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for HTTP dashboard (default from config.json)",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Disable background web dashboard in stdio mode",
    )
    args = parser.parse_args()

    # Configuration from config.json
    config = get_config()
    host = args.host or config.dashboard.host
    port = args.port or config.dashboard.port

    # Autodetect transport mode:
    # - If explicit --transport is given, use it
    # - If stdin is a TTY (interactive terminal) → HTTP with dashboard
    # - If stdin is a pipe (Claude Desktop, etc.) → stdio
    if args.transport:
        use_stdio = args.transport == "stdio"
    else:
        use_stdio = not sys.stdin.isatty()

    def run_dashboard():
        """Helper to run uvicorn in a thread."""
        logger.info(f"Starting dashboard on http://{host}:{port}")
        uvicorn.run(api_app, host=host, port=port, log_level="warning")

    try:
        if use_stdio:
            logger.info("Starting multiCAD-MCP server in stdio mode...")

            # Start dashboard in background unless disabled
            if not args.no_dashboard:
                web_thread = threading.Thread(target=run_dashboard, daemon=True)
                web_thread.start()

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


if __name__ == "__main__":
    main()

