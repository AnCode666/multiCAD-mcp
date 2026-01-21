"""
Utility mixin for AutoCAD adapter.

Contains helper methods, decorators, context managers, and utility classes.
"""

import logging
import time
import math
from typing import Any, Callable, TypeVar, List, Optional, TYPE_CHECKING
from functools import wraps
from contextlib import contextmanager
import sys

if sys.platform == "win32":
    import win32com.client
    import pythoncom
    import win32gui
    import win32api
    import win32con
    import pywintypes
else:
    raise ImportError("AutoCAD adapter requires Windows OS with COM support")

from core import (
    CADOperationError,
    Point,
)
from mcp_tools.constants import (
    COLOR_MAP,
    AUTOCAD_WINDOW_CLASSES,
    CLICK_DELAY,
    CLICK_HOLD_DELAY,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ========== COM Context Manager ==========


@contextmanager
def com_session():
    """Context manager for safe COM initialization and cleanup.

    Ensures CoInitialize/CoUninitialize are always paired, even on exceptions.
    Use this for all COM operations to prevent thread state leaks.

    Example:
        with com_session():
            app = win32com.client.Dispatch("AutoCAD.Application")
            # ... use app ...
    """
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception as e:
            logger.debug(f"CoUninitialize failed (non-critical): {e}")


class SelectionSetManager:
    """Context manager for safe SelectionSet handling.

    Ensures SelectionSet cleanup even on exceptions, preventing orphaned
    selection sets that can cause issues in AutoCAD.

    Example:
        with SelectionSetManager(document, "TEMP_SS") as ss:
            ss.Select(...)
            # ... use ss ...
        # Auto-deleted on exit
    """

    def __init__(self, document: Any, name: str):
        """Initialize SelectionSet manager.

        Args:
            document: AutoCAD document object
            name: Name for the selection set
        """
        self.document = document
        self.name = name
        self.selection_set: Optional[Any] = None

    def __enter__(self) -> Any:
        """Create SelectionSet, deleting existing one if present.

        Returns:
            Created SelectionSet object
        """
        # Delete if exists
        try:
            self.document.SelectionSets.Item(self.name).Delete()
            logger.debug(f"Deleted existing SelectionSet: {self.name}")
        except Exception:
            pass

        # Create new
        self.selection_set = self.document.SelectionSets.Add(self.name)
        logger.debug(f"Created SelectionSet: {self.name}")
        return self.selection_set

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Cleanup SelectionSet on exit.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        try:
            if self.selection_set:
                self.selection_set.Delete()
                logger.debug(f"Cleaned up SelectionSet: {self.name}")
        except Exception as e:
            logger.debug(f"Failed to delete SelectionSet {self.name}: {e}")


# ========== Decorators ==========


def com_safe(return_type: type = bool, operation_name: str = "operation"):
    """Decorator for COM operation error handling.

    Wraps method with:
    - Exception catching (pywintypes.com_error)
    - Operation logging
    - Automatic error conversion to CADOperationError

    Args:
        return_type: Expected return type (for type hints)
        operation_name: Name of operation (for logging)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except pywintypes.com_error as e:
                # COM error attributes: args[0] = hresult, args[2] = strerror
                error_msg = f"COM error: {str(e)}"
                logger.error(f"Failed in {func.__name__}: {error_msg}")
                if return_type == bool:
                    return False  # type: ignore
                raise CADOperationError(operation_name, error_msg)
            except Exception as e:
                logger.error(f"Failed in {func.__name__}: {e}")
                if return_type == bool:
                    return False  # type: ignore
                raise CADOperationError(operation_name, str(e))

        return wrapper

    return decorator


# ========== Utility Mixin ==========


class UtilityMixin:
    """Mixin for utility methods, helpers, and converters."""

    if TYPE_CHECKING:
        # Tell type checker this mixin is used with CADAdapterProtocol
        document: Any
        application: Any
        _drawing_state: dict

        def is_connected(self) -> bool: ...
        def validate_lineweight(self, weight: int) -> int: ...

    def _validate_connection(self) -> None:
        """Raise error if not connected."""
        if not self.is_connected():
            raise CADOperationError("connection", "Not connected to CAD application")
        if self.document is None:
            raise CADOperationError("connection", "Document is not available")

    def _get_document(self, operation: str = "operation") -> Any:
        """Get document with validation. Raises if not available."""
        self._validate_connection()
        if self.document is None:
            raise CADOperationError(operation, "Document not available")
        return self.document

    def _get_application(self, operation: str = "operation") -> Any:
        """Get application with validation. Raises if not available."""
        if self.application is None:
            raise CADOperationError(operation, "Application not available")
        return self.application

    def _wait_for(
        self,
        condition: Callable[[], bool],
        timeout: float = 20.0,
        interval: float = 0.1,
    ) -> bool:
        """Wait for a condition with timeout (replaces brittle time.sleep).

        Args:
            condition: Callable that returns True when condition is met
            timeout: Maximum seconds to wait (default: 20.0)
            interval: Check interval in seconds (default: 0.1)

        Returns:
            True if condition met before timeout, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if condition():
                    return True
            except Exception:
                pass
            time.sleep(interval)
        return False

    def _delete_selection_set(self, document: Any, name: str) -> None:
        """Delete selection set if it exists (helper to reduce repetition)."""
        try:
            document.SelectionSets.Item(name).Delete()
        except Exception:
            pass

    def _to_variant_array(self, point: Point):
        """Convert 3D point to COM variant array."""
        return win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            [float(point[0]), float(point[1]), float(point[2])],
        )

    def _points_to_variant_array(self, points: List[Point]):
        """Convert list of 3D points to COM variant array (flattened)."""
        flat_array = []
        for point in points:
            flat_array.extend([float(point[0]), float(point[1]), float(point[2])])

        return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_array)

    def _objects_to_variant_array(self, objects: List[Any]) -> Any:
        """Convert list of COM objects to variant array for CopyObjects.

        Args:
            objects: List of COM entity objects

        Returns:
            VARIANT array of COM objects for CopyObjects method
        """
        return win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, objects
        )

    def _int_array_to_variant(self, values: tuple | list) -> Any:
        """Convert list of integers to COM variant array (for DXF filter codes)."""
        return win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_I2, [int(v) for v in values]
        )

    def _mixed_array_to_variant(self, values: tuple | list) -> Any:
        """Convert list of mixed types to COM variant array (for DXF filter data)."""
        variant_list: List[Any] = []
        for val in values:
            if isinstance(val, str):
                variant_list.append(val)
            elif isinstance(val, (int, float)):
                variant_list.append(val)
            else:
                variant_list.append(str(val))

        return win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, variant_list
        )

    def _to_radians(self, degrees: float) -> float:
        """Convert degrees to radians."""
        return degrees * math.pi / 180.0

    def _get_color_index(self, color_name: str) -> int:
        """Get CAD color index from color name."""
        color_name = color_name.lower().replace(" ", "_")
        return COLOR_MAP.get(color_name, 7)  # Default white

    def _apply_properties(
        self,
        entity: Any,
        layer: str,
        color: str | int,
        lineweight: int = 0,
    ) -> None:
        """Apply common properties to an entity."""
        try:
            entity.Layer = layer
            if isinstance(color, str):
                color = self._get_color_index(color)
            entity.Color = color
            if lineweight > 0:
                entity.LineWeight = self.validate_lineweight(lineweight)
        except Exception as e:
            logger.warning(f"Failed to apply properties: {e}")

    def _track_entity(self, entity: Any, entity_type: str) -> None:
        """Track entity in drawing state."""
        try:
            self._drawing_state["entities"].append(
                {
                    "handle": str(entity.Handle),
                    "type": entity_type,
                    "object_name": entity.ObjectName,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track entity: {e}")

    def _safe_get_property(
        self, obj: Any, property_name: str, default: Any = None
    ) -> Any:
        """Safely get a COM object property with fallback value.

        Args:
            obj: COM object
            property_name: Name of property to get
            default: Default value if property access fails

        Returns:
            Property value or default
        """
        try:
            return getattr(obj, property_name)
        except Exception as e:
            logger.debug(f"Failed to get property {property_name}: {e}")
            return default

    def _fast_get_property(
        self, obj: Any, property_name: str, default: Any = None
    ) -> Any:
        """Fast version of _safe_get_property without logging for bulk operations.

        Use this in tight loops where logging overhead is significant.

        Args:
            obj: COM object
            property_name: Name of property to get
            default: Default value if property access fails

        Returns:
            Property value or default
        """
        try:
            return getattr(obj, property_name)
        except Exception:
            return default

    def _simulate_autocad_click(self) -> bool:
        """Simulate a click in the CAD window to force viewport update.

        This is a workaround to ensure the viewport updates after operations.
        Finds the CAD main window and simulates a subtle click.

        Returns:
            True if click simulation succeeded, False otherwise
        """
        try:
            self._validate_connection()

            hwnd = None
            for class_name in AUTOCAD_WINDOW_CLASSES:
                hwnd = win32gui.FindWindow(class_name, None)
                if hwnd:
                    logger.debug(f"Found CAD window: {class_name}")
                    break

            if not hwnd:
                logger.debug("CAD window not found for click simulation")
                return False

            # Get window center position for subtle click
            try:
                rect = win32gui.GetWindowRect(hwnd)
                x = (rect[0] + rect[2]) // 2  # Center X
                y = (rect[1] + rect[3]) // 2  # Center Y

                # Simulate left mouse click at window center
                win32api.SetCursorPos((x, y))
                time.sleep(CLICK_DELAY / 1000.0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                time.sleep(CLICK_HOLD_DELAY / 1000.0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

                logger.debug("CAD window click simulated")
                return True
            except Exception as e:
                logger.debug(f"Click simulation failed: {e}")
                return False

        except Exception as e:
            logger.debug(f"_simulate_autocad_click error: {e}")
            return False
