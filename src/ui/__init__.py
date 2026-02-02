"""
MCP UI Resources module for multiCAD-MCP.

Provides UI resources for enhanced visualization in MCP Apps-compatible hosts.
"""

from ui.resources import (
    create_cad_ui_resource,
    register_all_ui_resources,
    get_drawing_viewer_html,
    get_layer_panel_html,
    get_block_browser_html,
)

__all__ = [
    "create_cad_ui_resource",
    "register_all_ui_resources",
    "get_drawing_viewer_html",
    "get_layer_panel_html",
    "get_block_browser_html",
]
