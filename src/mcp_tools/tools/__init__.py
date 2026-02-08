"""
MCP tools package - unified tools.

Contains all tool definitions organized by category:
- session: Connection lifecycle, view, and history (manage_session)
- drawing: Unified drawing operations (draw_entities)
- layers: Unified layer management (manage_layers + queries)
- files: Unified file management (manage_files)
- entities: Unified entity operations (modify_entities, select_entities, copy_paste_entities)
- blocks: Unified block management (manage_blocks, list_blocks, query_block)
- export: Unified export (export_data)

Legacy tools are preserved in ./legacy/ for reference.
"""

from .session import register_session_tools
from .drawing import register_drawing_tools
from .layers import register_layer_tools
from .files import register_file_tools
from .entities import register_entity_tools
from .export import register_export_tools
from .blocks import register_block_tools

__all__ = [
    "register_session_tools",
    "register_drawing_tools",
    "register_layer_tools",
    "register_file_tools",
    "register_entity_tools",
    "register_export_tools",
    "register_block_tools",
]
