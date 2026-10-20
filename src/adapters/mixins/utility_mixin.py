"""
Utility mixin for AutoCAD adapter.

Contains helper methods, decorators, context managers, and utility classes.
"""

import logging
import time
import math
from pathlib import Path
from typing import Any, Callable, TypeVar, List, Optional, Dict, TYPE_CHECKING
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
    CADConnectionError,
    InvalidParameterError,
    Point,
    ConfigManager,
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

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Cleanup SelectionSet on exit.

        Args:
            _exc_type: Exception type if raised
            _exc_val: Exception value if raised
            _exc_tb: Exception traceback if raised
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
        cad_type: str

        def is_connected(self) -> bool: ...
        def validate_lineweight(self, weight: int) -> int: ...

    def _validate_connection(self) -> None:
        """Check if connection is still alive, otherwise reconnect.

        Is thread-safe: each thread will have its own proxy via self._local.
        """
        import threading

        if self.application is None:
            from .connection_mixin import ConnectionMixin

            if isinstance(self, ConnectionMixin):
                self.connect(only_if_running=True)
            else:
                logger.warning(
                    "_validate_connection: application is None and self is not ConnectionMixin"
                )
                return

        try:
            # Simple ping to verify COM proxy is still valid for THIS thread
            _ = self.application.Visible
        except Exception as e:
            logger.debug(
                f"Connection validation failed (thread {threading.get_ident()}): {e}"
            )
            from .connection_mixin import ConnectionMixin

            if isinstance(self, ConnectionMixin):
                self.connect(only_if_running=True)

    def _get_application(self, operation: str = "operation") -> Any:
        """Helper to ensure application is available for an operation."""
        self._validate_connection()
        if self.application is None:
            from core import CADConnectionError

            raise CADConnectionError(
                self.cad_type, f"No active instance for '{operation}'"
            )
        return self.application

    def _get_document(self, operation: str = "operation") -> Any:
        """Helper to ensure document is available for an operation."""
        self._validate_connection()

        if self.document is None:
            # Try to grab ActiveDocument if it's missing in this thread
            app = self._get_application(operation)
            try:
                self.document = app.ActiveDocument
            except Exception as e:
                logger.error(f"Failed to get ActiveDocument for {operation}: {e}")
                from core import CADConnectionError

                raise CADConnectionError(
                    getattr(self, "cad_type", "unknown"),
                    f"No active document for '{operation}'",
                )

        if self.document is None:
            from core import CADConnectionError

            raise CADConnectionError(
                getattr(self, "cad_type", "unknown"),
                f"No active document for '{operation}'",
            )

        return self.document

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

    def resolve_export_path(self, filename: str, folder_type: str = "drawings") -> str:
        """Centralized path resolution for all export operations.

        Handles:
        1. Configured output directory (from config.json)
        2. Subfolder hierarchy (drawings, images, sheets)
        3. Tilde expansion and absolute path resolution
        4. Security validation (must be within output directory)
        5. Directory creation

        Args:
            filename: Name of the file with extension
            folder_type: Subfolder category ('drawings', 'images', 'sheets')

        Returns:
            str: Full absolute path to the resolved file
        """
        config = ConfigManager()
        output_dir = Path(config.ensure_output_directory()).expanduser().resolve()

        # Define subfolder
        subfolder_mapping = {
            "drawings": "drawings",
            "images": "images",
            "sheets": "sheets",
        }
        subfolder_name = subfolder_mapping.get(folder_type, folder_type)
        target_dir = output_dir / subfolder_name

        # Create subfolder if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # Resolve final path
        final_path = (target_dir / filename).resolve()

        # SECURITY: Validate path to prevent traversal attacks
        self._validate_export_path(final_path, output_dir)

        logger.debug(f"Resolved export path for {folder_type}: {final_path}")
        return str(final_path)

    def _validate_export_path(self, resolved_path: Path, output_dir: Path) -> bool:
        """Prevent path traversal by validating resolved_path is within output_dir.

        Args:
            resolved_path: The resolved absolute path to validate
            output_dir: The allowed parent directory

        Returns:
            bool: True if path is safe

        Raises:
            CADOperationError: If path traversal is detected or allowed
        """
        config = ConfigManager().config
        if getattr(config.output, "allow_arbitrary_paths", False):
            logger.debug(f"Bypassing path validation for: {resolved_path}")
            return True

        try:
            resolved_path.resolve().relative_to(output_dir.resolve())
            return True
        except ValueError:
            raise CADOperationError(
                "resolve_export_path",
                f"Path traversal detected: {resolved_path} is outside {output_dir}. "
                "Enable 'allow_arbitrary_paths' in config to bypass.",
            )

    def _handle_operation_error(
        self,
        operation_name: str,
        error: Exception,
        default_return: Any = False,
    ) -> Any:
        """Standardized error handling for all mixin operations.

        Logs errors consistently and determines whether to re-raise or return default.

        Args:
            operation_name: Name of the operation that failed
            error: The exception that was raised
            default_return: Default value to return for non-critical errors

        Returns:
            The default_return value, unless it's a critical error that should propagate

        Raises:
            If error is a critical exception (CADConnectionError, CADOperationError)
        """
        logger.error(f"{operation_name} failed: {error}")
        # Re-raise critical errors, return default for others
        if isinstance(error, (CADConnectionError, CADOperationError)):
            raise
        return default_return

    def _validate_drawing_params(
        self,
        operation: str,
        radius: Optional[float] = None,
        angle: Optional[float] = None,
        points: Optional[List] = None,
    ) -> None:
        """Validate parameters for drawing operations.

        Performs sanity checks on common drawing parameters to catch invalid inputs early.

        Args:
            operation: Name of the operation being validated
            radius: Circle/arc radius to validate (must be > 0)
            angle: Rotation/arc angle in degrees
            points: List of coordinate points

        Raises:
            InvalidParameterError: If any parameter is invalid
        """
        if radius is not None:
            if radius <= 0:
                raise InvalidParameterError(operation, "radius", "positive number")
            if radius > 1000000:
                logger.warning(f"{operation}: Very large radius {radius}")

        if angle is not None:
            if not -360 <= angle <= 360:
                logger.warning(
                    f"{operation}: Angle {angle} outside normal range [-360, 360]"
                )

        if points is not None:
            if not isinstance(points, (list, tuple)):
                raise InvalidParameterError(
                    operation, "points", "list of coordinate points"
                )
            if len(points) < 2:
                raise InvalidParameterError(
                    operation, "points", "at least 2 coordinate points"
                )

    def _iterate_entities_safe(
        self,
        operation_name: str,
        callback: Callable[[Any], bool],
    ) -> tuple[int, int]:
        """Safely iterate through entities with standardized error handling.

        Provides consistent iteration, error logging, and metrics collection.

        Args:
            operation_name: Name of the operation being performed
            callback: Function to call for each entity, returns True if successful

        Returns:
            Tuple of (successful_count, total_count)
        """
        try:
            document = self._get_document(operation_name)
        except Exception as e:
            return self._handle_operation_error(
                operation_name, e, default_return=(0, 0)
            )

        success_count = 0
        total_count = 0

        try:
            for entity in document.ModelSpace:
                total_count += 1
                try:
                    if callback(entity):
                        success_count += 1
                except Exception as e:
                    logger.debug(f"{operation_name} skipped entity: {e}")
                    continue

            logger.info(f"{operation_name}: {success_count}/{total_count} processed")
            return success_count, total_count
        except Exception as e:
            return self._handle_operation_error(
                operation_name, e, default_return=(success_count, total_count)
            )

    # ========== Human-in-the-Loop Interaction Methods ==========

    def prompt_point(
        self, prompt: str = "Select point:", base_point: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Prompt user in CAD viewport to pick a point with crosshair."""
        try:
            document = self._get_document("prompt_point")
            utility = document.Utility
            prompt_str = prompt if prompt.endswith(" ") or prompt.endswith(":") else prompt + ": "
            if base_point is not None:
                bp = self._to_variant_array(base_point)
                pt = utility.GetPoint(bp, prompt_str)
            else:
                pt = utility.GetPoint(prompt_str)
            point_tuple = (float(pt[0]), float(pt[1]), float(pt[2]))
            logger.info(f"User picked point: {point_tuple}")
            return {"success": True, "point": point_tuple, "interactive": True}
        except Exception as e:
            err_str = str(e)
            if "cancelled" in err_str.lower() or "-2145320928" in err_str:
                return {"success": False, "cancelled": True, "detail": "User cancelled point selection"}
            logger.error(f"Failed to get point from user: {e}")
            return {"success": False, "detail": str(e)}

    def prompt_entity(
        self, prompt: str = "Select entity:"
    ) -> Dict[str, Any]:
        """Prompt user in CAD viewport to pick an entity."""
        try:
            document = self._get_document("prompt_entity")
            utility = document.Utility
            prompt_str = prompt if prompt.endswith(" ") or prompt.endswith(":") else prompt + ": "
            res = utility.GetEntity(prompt_str)
            entity = res[0] if isinstance(res, (tuple, list)) else res
            pt = res[1] if isinstance(res, (tuple, list)) and len(res) > 1 else None

            handle = str(getattr(entity, "Handle", ""))
            obj_name = str(getattr(entity, "ObjectName", ""))
            layer = str(getattr(entity, "Layer", ""))
            picked_pt = tuple(float(c) for c in pt) if pt else None

            logger.info(f"User picked entity {handle} ({obj_name}) on layer {layer}")
            return {
                "success": True,
                "handle": handle,
                "type": obj_name,
                "layer": layer,
                "picked_point": picked_pt,
                "interactive": True,
            }
        except Exception as e:
            err_str = str(e)
            if "cancelled" in err_str.lower() or "-2145320928" in err_str:
                return {"success": False, "cancelled": True, "detail": "User cancelled entity selection"}
            logger.error(f"Failed to get entity from user: {e}")
            return {"success": False, "detail": str(e)}

    def prompt_distance(
        self, prompt: str = "Specify distance:", base_point: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Prompt user in CAD viewport to specify or measure a distance."""
        try:
            document = self._get_document("prompt_distance")
            utility = document.Utility
            prompt_str = prompt if prompt.endswith(" ") or prompt.endswith(":") else prompt + ": "
            if base_point is not None:
                bp = self._to_variant_array(base_point)
                dist = utility.GetDistance(bp, prompt_str)
            else:
                dist = utility.GetDistance(prompt_str)
            dist_val = float(dist)
            logger.info(f"User specified distance: {dist_val}")
            return {"success": True, "distance": dist_val, "interactive": True}
        except Exception as e:
            err_str = str(e)
            if "cancelled" in err_str.lower() or "-2145320928" in err_str:
                return {"success": False, "cancelled": True, "detail": "User cancelled distance specification"}
            logger.error(f"Failed to get distance from user: {e}")
            return {"success": False, "detail": str(e)}

    def prompt_string(
        self, prompt: str = "Enter string:", has_spaces: bool = True
    ) -> Dict[str, Any]:
        """Prompt user in CAD command line to enter text string."""
        try:
            document = self._get_document("prompt_string")
            utility = document.Utility
            prompt_str = prompt if prompt.endswith(" ") or prompt.endswith(":") else prompt + ": "
            val = utility.GetString(1 if has_spaces else 0, prompt_str)
            str_val = str(val)
            logger.info(f"User entered string: '{str_val}'")
            return {"success": True, "string": str_val, "interactive": True}
        except Exception as e:
            err_str = str(e)
            if "cancelled" in err_str.lower() or "-2145320928" in err_str:
                return {"success": False, "cancelled": True, "detail": "User cancelled string input"}
            logger.error(f"Failed to get string from user: {e}")
            return {"success": False, "detail": str(e)}
