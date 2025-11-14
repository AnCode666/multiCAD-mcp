"""
Data export tools for extracting and saving drawing information.

Provides tools for:
- Extracting drawing data (entities with properties)
- Exporting data to Excel format
"""

import logging
import json
from typing import Optional

from mcp.server.fastmcp import Context

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import result_message

logger = logging.getLogger(__name__)


def register_export_tools(mcp):
    """Register export tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @cad_tool(mcp, "export_drawing_to_excel")
    def export_drawing_to_excel(
        ctx: Context,
        filename: str = "drawing_data.xlsx",
        cad_type: Optional[str] = None,
    ) -> str:
        """Export drawing data to Excel file.

        Extracts all entities from the drawing and creates an Excel spreadsheet with:
        - Handle: Entity identifier
        - ObjectType: Entity type (LINE, CIRCLE, LWPOLYLINE, etc.)
        - Layer: Layer name
        - Color: Color index or name
        - Length: Length (for linear objects)
        - Area: Area (for closed objects)
        - Name: Name (for blocks, etc.)

        Files are saved to the output directory configured in config.json for security.
        If subdirectories are specified in the filename, they must be within the
        configured output directory.

        Args:
            filename: Excel filename or path (default: "drawing_data.xlsx")
                     Examples:
                     - "data.xlsx" → saved to output directory
                     - "exports/data.xlsx" → saved to output/exports/
            cad_type: CAD application to use (autocad, zwcad, gcad, bricscad)

        Returns:
            JSON result with export status
        """
        try:
            adapter = get_current_adapter()
            success = adapter.export_to_excel(filename)
            return result_message(
                "export drawing to excel",
                success,
                f"Saved to {filename}" if success else "Check logs for details",
            )
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return result_message("export drawing to excel", False, str(e))

    @cad_tool(mcp, "extract_drawing_data")
    def extract_drawing_data(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> str:
        """Extract all drawing data without saving to file.

        Returns entity data as JSON with columns:
        - Handle: Entity identifier
        - ObjectType: Entity type (LINE, CIRCLE, LWPOLYLINE, etc.)
        - Layer: Layer name
        - Color: Color index or name
        - Length: Length (for linear objects)
        - Area: Area (for closed objects)
        - Name: Name (for blocks, etc.)

        Args:
            cad_type: CAD application to use (autocad, zwcad, gcad, bricscad)

        Returns:
            JSON result with extracted data
        """
        try:
            adapter = get_current_adapter()
            data = adapter.extract_drawing_data()

            if data:
                result = {
                    "success": True,
                    "count": len(data),
                    "message": f"Extracted data from {len(data)} entities",
                    "entities": data,
                }
            else:
                result = {
                    "success": False,
                    "count": 0,
                    "message": "No entities found in drawing",
                    "entities": [],
                }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            result = {
                "success": False,
                "count": 0,
                "message": f"Extraction error: {str(e)}",
                "entities": [],
            }
            return json.dumps(result, indent=2)
