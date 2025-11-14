"""
Simple view and history tools.

Provides tools for:
- Zooming to extents
- Undo/redo operations
"""

import logging
from typing import Optional

from mcp.server.fastmcp import Context

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import result_message

logger = logging.getLogger(__name__)


def register_simple_tools(mcp):
    """Register simple utility tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @cad_tool(mcp, "zoom_extents")
    def zoom_extents(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Zoom to show all entities in the view.

        Args:
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().zoom_extents()
        return result_message("zoom to extents", success)

    @cad_tool(mcp, "undo")
    def undo(
        ctx: Context,
        count: int = 1,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Undo last action(s).

        Args:
            count: Number of operations to undo (default: 1)
            cad_type: CAD application to use

        Returns:
            Success/failure message
        """
        success = get_current_adapter().undo(count=count)
        if success:
            if count == 1:
                return "Action undone"
            else:
                return f"{count} actions undone"
        return "Failed to undo"

    @cad_tool(mcp, "redo")
    def redo(
        ctx: Context,
        count: int = 1,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Redo last undone action(s).

        Args:
            count: Number of operations to redo (default: 1)
            cad_type: CAD application to use

        Returns:
            Success/failure message
        """
        success = get_current_adapter().redo(count=count)
        if success:
            if count == 1:
                return "Action redone"
            else:
                return f"{count} actions redone"
        return "Failed to redo"
