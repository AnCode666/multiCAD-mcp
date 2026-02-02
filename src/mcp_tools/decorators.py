"""
Decorators for MCP tools.

Provides decorators for standardizing adapter access and error handling:
- @cad_tool: Standard CAD tool decorator
- @cad_tool_with_ui: CAD tool decorator with MCP Apps UI support
"""

from functools import wraps
from typing import Callable, TypeVar, Optional, Any, Dict

from mcp.server.fastmcp import FastMCP, Context

from core import CADOperationError

T = TypeVar("T")


class AdapterContext:
    """
    Manages the current adapter context for tool execution.

    Encapsulates the global state of the current adapter, making it easier
    to test and manage adapter lifecycle.
    """

    _instance: Optional["AdapterContext"] = None

    def __init__(self):
        """Initialize with no adapter set."""
        self._current_adapter: Any = None

    @classmethod
    def get_instance(cls) -> "AdapterContext":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def get_current_adapter(self) -> Any:
        """Get the current adapter with proper type handling.

        Returns:
            Current CAD adapter instance

        Raises:
            CADOperationError: If no adapter is initialized
        """
        if self._current_adapter is None:
            raise CADOperationError("adapter", "No adapter initialized")
        return self._current_adapter

    def set_current_adapter(self, adapter: Any) -> None:
        """Set the current adapter.

        Args:
            adapter: CAD adapter instance to set as current
        """
        self._current_adapter = adapter


# Singleton instance
_context = AdapterContext.get_instance()


# Module-level convenience functions for backward compatibility
def get_current_adapter() -> Any:
    """Convenience function - delegates to singleton context."""
    return _context.get_current_adapter()


def set_current_adapter(adapter: Any) -> None:
    """Convenience function - delegates to singleton context."""
    _context.set_current_adapter(adapter)


def cad_tool(mcp: FastMCP, operation_name: str):
    """
    Decorator for standardizing adapter access and error handling.

    Automatically:
    1. Resolves the correct adapter based on cad_type parameter
    2. Sets current adapter in context for the decorated function
    3. Wraps with try/except for consistent error handling
    4. Raises CADOperationError on failure
    5. Registers with FastMCP

    Args:
        mcp: FastMCP instance
        operation_name: Name of operation for error reporting

    Usage:
        @cad_tool(mcp, "draw_line")
        def draw_line(ctx, start, end, ...):
            adapter = get_current_adapter()
            return adapter.draw_line(...)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(ctx: Context, *args, cad_type: Optional[str] = None, **kwargs) -> T:
            from adapters.adapter_manager import get_adapter

            try:
                set_current_adapter(get_adapter(cad_type))
                return func(ctx, *args, **kwargs)
            except CADOperationError:
                raise
            except Exception as e:
                raise CADOperationError(operation_name, str(e))

        return mcp.tool()(wrapper)

    return decorator


def cad_tool_with_ui(
    mcp: FastMCP,
    operation_name: str,
    ui_resource: Optional[str] = None,
):
    """
    Decorator for CAD tools with MCP Apps UI support.

    Extends the standard cad_tool decorator with UI resource metadata
    for enhanced visualization in MCP Apps-compatible hosts (Claude Desktop, VS Code).

    Automatically:
    1. Resolves the correct adapter based on cad_type parameter
    2. Sets current adapter in context for the decorated function
    3. Wraps with try/except for consistent error handling
    4. Raises CADOperationError on failure
    5. Registers with FastMCP with optional UI metadata
    6. Injects _meta.ui.resourceUri for UI-enabled responses

    Args:
        mcp: FastMCP instance
        operation_name: Name of operation for error reporting
        ui_resource: Optional UI resource name (e.g., "drawing_viewer")
                    If provided, adds ui://multicad/{ui_resource} to tool metadata

    Usage:
        @cad_tool_with_ui(mcp, "extract_drawing_data", ui_resource="drawing_viewer")
        def extract_drawing_data(ctx, ...):
            adapter = get_current_adapter()
            return adapter.extract_drawing_data(...)

    Note:
        - Hosts without MCP Apps support will ignore the UI metadata
        - The tool response remains JSON-compatible for backward compatibility
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(ctx: Context, *args, cad_type: Optional[str] = None, **kwargs) -> T:
            from adapters.adapter_manager import get_adapter

            try:
                set_current_adapter(get_adapter(cad_type))
                return func(ctx, *args, **kwargs)
            except CADOperationError:
                raise
            except Exception as e:
                raise CADOperationError(operation_name, str(e))

        # Build tool metadata with optional UI resource
        tool_kwargs: Dict[str, Any] = {}

        if ui_resource:
            # MCP Apps UI metadata
            tool_kwargs["annotations"] = {
                "ui": {
                    "resourceUri": f"ui://multicad/{ui_resource}",
                }
            }

        return mcp.tool(**tool_kwargs)(wrapper)

    return decorator
