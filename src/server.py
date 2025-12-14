"""
multiCAD-MCP Server

Fast, extensible MCP server for controlling multiple CAD applications.

Uses FastMCP framework for clean, decorator-based tool definition.
Supports AutoCAD, ZWCAD, GstarCAD, and other COM-compatible CAD software.
"""

import sys

from mcp.server.fastmcp import FastMCP

from __version__ import __version__, __title__
from core import get_supported_cads
from mcp_tools.helpers import setup_utf8_encoding, setup_logging
from mcp_tools.adapter_manager import auto_detect_cad
from mcp_tools.tools import (
    register_connection_tools,
    register_drawing_tools,
    register_layer_tools,
    register_file_tools,
    register_entity_tools,
    register_simple_tools,
    register_nlp_tools,
    register_export_tools,
    register_debug_tools,
    register_block_tools,
)

# Setup at module load
setup_utf8_encoding()
logger = setup_logging()

# Initialize FastMCP server
mcp = FastMCP(name=__title__)


def register_all_tools():
    """Register all MCP tools with FastMCP.

    Organizes tools by category:
    - Connection management
    - Drawing operations
    - Layer management
    - File operations
    - Entity selection and manipulation
    - Block management
    - Simple view and history tools
    - Natural language command execution
    - Debug and diagnostic tools
    """
    logger.info("Registering MCP tools...")

    register_connection_tools(mcp)
    logger.debug("  ✓ Connection tools registered")

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

    register_simple_tools(mcp)
    logger.debug("  ✓ Simple tools registered")

    register_nlp_tools(mcp)
    logger.debug("  ✓ NLP tools registered")

    register_export_tools(mcp)
    logger.debug("  ✓ Export tools registered")

    register_debug_tools(mcp)
    logger.debug("  ✓ Debug tools registered")

    logger.info("All MCP tools registered successfully")


# Register tools at module load
register_all_tools()

# Auto-detect available CAD applications at startup
logger.info(f"Starting multiCAD-MCP server v{__version__}...")
logger.info(f"Supported CAD types: {', '.join(get_supported_cads())}")

try:
    logger.info("Auto-detecting CAD applications...")
    auto_detect_cad()
except Exception as e:
    logger.warning(f"Auto-detection failed (will attempt on first use): {e}")


if __name__ == "__main__":
    try:
        logger.info("Starting MCP server loop...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
