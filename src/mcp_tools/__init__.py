"""
MCP server module.

Contains the FastMCP server infrastructure and all tool definitions.

Modules:
- constants: Configuration constants and color maps
- helpers: Utility functions for parsing and setup
- decorators: Decorator for unified tool error handling
- adapter_manager: CAD adapter lifecycle management
- tools: All MCP tool definitions
"""

from .constants import COLOR_MAP
from .helpers import parse_coordinate, parse_handles, result_message
from .decorators import cad_tool, get_current_adapter, set_current_adapter
from .adapter_manager import (
    get_adapter,
    get_active_cad_type,
    set_active_cad_type,
    auto_detect_cad,
)

__all__ = [
    "COLOR_MAP",
    "parse_coordinate",
    "parse_handles",
    "result_message",
    "cad_tool",
    "get_current_adapter",
    "set_current_adapter",
    "get_adapter",
    "get_active_cad_type",
    "set_active_cad_type",
    "auto_detect_cad",
]
