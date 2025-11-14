"""
Connection management tools for CAD applications.

Provides tools for:
- Connecting to CAD applications
- Disconnecting from CAD applications
- Listing supported CAD types
- Checking connection status
"""

import logging

from mcp.server.fastmcp import Context

from core import get_supported_cads, CADConnectionError
from adapters import create_adapter
from mcp_tools.adapter_manager import get_cad_instances

logger = logging.getLogger(__name__)


def register_connection_tools(mcp):
    """Register connection management tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @mcp.tool()
    def connect_cad(ctx: Context, cad_type: str = "autocad") -> str:
        """
        Connect to a CAD application.

        Args:
            cad_type: Type of CAD to connect to (autocad, zwcad, gcad, bricscad)

        Returns:
            Status message confirming connection
        """
        cad_type = cad_type.lower()
        cad_instances = get_cad_instances()

        if cad_type in cad_instances:
            if cad_instances[cad_type].is_connected():
                return f"Already connected to {cad_type}"

        try:
            adapter = create_adapter(cad_type)
            adapter.connect()
            cad_instances[cad_type] = adapter
            logger.info(f"Connected to {cad_type}")
            return f"Successfully connected to {cad_type}"
        except CADConnectionError as e:
            logger.error(f"Connection failed: {e}")
            raise
        except Exception as e:
            raise CADConnectionError(cad_type, str(e))

    @mcp.tool()
    def disconnect_cad(ctx: Context, cad_type: str = "autocad") -> str:
        """
        Disconnect from a CAD application.

        Args:
            cad_type: Type of CAD to disconnect from

        Returns:
            Status message confirming disconnection
        """
        cad_type = cad_type.lower()
        cad_instances = get_cad_instances()

        if cad_type not in cad_instances:
            return f"Not connected to {cad_type}"

        try:
            adapter = cad_instances[cad_type]
            adapter.disconnect()
            del cad_instances[cad_type]
            logger.info(f"Disconnected from {cad_type}")
            return f"Successfully disconnected from {cad_type}"
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            return f"Error disconnecting from {cad_type}: {e}"

    @mcp.tool()
    def list_supported_cads(ctx: Context) -> str:
        """
        List all supported CAD applications.

        Returns:
            List of supported CAD types
        """
        supported = get_supported_cads()
        return f"Supported CAD types: {', '.join(supported)}"

    @mcp.tool()
    def get_connection_status(ctx: Context) -> str:
        """
        Get connection status for all CAD types.

        Returns:
            Dictionary with connection status for each CAD type
        """
        cad_instances = get_cad_instances()
        status = {}
        for cad_type in get_supported_cads():
            if cad_type in cad_instances:
                is_connected = cad_instances[cad_type].is_connected()
                status[cad_type] = "connected" if is_connected else "disconnected"
            else:
                status[cad_type] = "not initialized"

        return str(status)
