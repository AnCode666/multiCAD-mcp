"""
File operation tools for managing drawings.

Provides tools for:
- Saving and creating drawings
- Closing drawings
- Listing and switching between open drawings
"""

import logging
import os
from typing import Optional

from mcp.server.fastmcp import Context

from core import get_config
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import result_message

logger = logging.getLogger(__name__)


def register_file_tools(mcp):
    """Register file operation tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @cad_tool(mcp, "save_drawing")
    def save_drawing(
        ctx: Context,
        filepath: str = "",
        filename: str = "",
        format: str = "dwg",
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Save the current drawing to a file.

        Args:
            filepath: Full file path (overrides filename and directory)
            filename: Just the filename (saved to output directory)
            format: File format (dwg, dxf, pdf, etc.)
            cad_type: CAD application to use

        Returns:
            Status message with file path
        """
        success = get_current_adapter().save_drawing(
            filepath=filepath, filename=filename, format=format
        )

        if success:
            if filepath:
                return result_message("save drawing", True, filepath)
            elif filename:
                config = get_config()
                output_dir = os.path.abspath(
                    os.path.expanduser(config.output.directory)
                )
                saved_path = os.path.join(output_dir, filename)
                return result_message("save drawing", True, saved_path)
            else:
                return result_message("save drawing", True)

        return result_message("save drawing", False)

    @cad_tool(mcp, "new_drawing")
    def new_drawing(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Create a new blank drawing.

        Args:
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().new_drawing()
        return result_message("create new drawing", success)

    @cad_tool(mcp, "close_drawing")
    def close_drawing(
        ctx: Context,
        save_changes: bool = False,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Close the current drawing.

        Args:
            save_changes: Whether to save changes before closing
            cad_type: CAD application to use

        Returns:
            Status message
        """
        success = get_current_adapter().close_drawing(save_changes=save_changes)

        if success:
            action = "saved" if save_changes else "closed without saving"
            open_drawings = get_current_adapter().get_open_drawings()
            if open_drawings:
                return f"Drawing {action}. Switched to: {open_drawings[0]}"
            else:
                return f"Drawing {action}. No other drawings open."

        return result_message("close drawing", False)

    @cad_tool(mcp, "get_open_drawings")
    def get_open_drawings(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Get list of all open drawings.

        Args:
            cad_type: CAD application to use

        Returns:
            Comma-separated list of open drawing names
        """
        drawings = get_current_adapter().get_open_drawings()

        logger.debug(f"get_open_drawings() raw result: {drawings}")
        logger.debug(f"  Type: {type(drawings)}")
        logger.debug(f"  Count: {len(drawings) if drawings else 0}")

        for i, drawing in enumerate(drawings):
            logger.debug(
                f"  [{i}] {repr(drawing)} - "
                f"Unicode: {[f'{c}(U+{ord(c):04X})' for c in drawing[:20]]}"
            )

        if not drawings:
            logger.info("No drawings open")
            return "No drawings open"

        result = ", ".join(drawings)
        logger.info(f"Open drawings: {result}")
        logger.debug(f"  Formatted result: {repr(result)}")

        return result

    @cad_tool(mcp, "switch_drawing")
    def switch_drawing(
        ctx: Context,
        drawing_name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Switch to a different open drawing.

        Args:
            drawing_name: Name of the drawing to switch to
            cad_type: CAD application to use

        Returns:
            Status message or list of available drawings
        """
        success = get_current_adapter().switch_drawing(drawing_name)

        if success:
            return f"Switched to: {drawing_name}"
        else:
            available = get_current_adapter().get_open_drawings()
            return f"Drawing '{drawing_name}' not found. Available: {', '.join(available) if available else 'none'}"
