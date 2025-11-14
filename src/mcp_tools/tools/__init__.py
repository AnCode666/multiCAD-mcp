"""
MCP tools package.

Contains all tool definitions organized by category:
- connection: CAD connection management
- drawing: Geometric drawing operations
- layers: Layer management
- files: File operations
- entities: Entity selection and manipulation
- simple: View and history tools
- nlp: Natural language command execution
- export: Data extraction and export
- debug: Debug and diagnostic tools
"""

from .connection import register_connection_tools
from .drawing import register_drawing_tools
from .layers import register_layer_tools
from .files import register_file_tools
from .entities import register_entity_tools
from .simple import register_simple_tools
from .nlp import register_nlp_tools
from .export import register_export_tools
from .debug import register_debug_tools

__all__ = [
    "register_connection_tools",
    "register_drawing_tools",
    "register_layer_tools",
    "register_file_tools",
    "register_entity_tools",
    "register_simple_tools",
    "register_nlp_tools",
    "register_export_tools",
    "register_debug_tools",
]
