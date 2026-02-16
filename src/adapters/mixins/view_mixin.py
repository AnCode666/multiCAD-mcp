"""
View mixin for AutoCAD adapter.

Handles view operations (zoom, refresh, undo, redo).
"""

import logging
import base64
import tempfile
import os
import time
import win32gui
import win32con
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional
from core.config import ConfigManager
from PIL import ImageGrab

logger = logging.getLogger(__name__)


class ViewMixin:
    """Mixin for view operations."""

    if TYPE_CHECKING:
        # Tell type checker this mixin is used with CADAdapterProtocol
        from typing import Any
        
        # Attributes from AutoCADAdapter
        cad_type: str

        def _get_application(self, operation: str = "operation") -> Any: ...
        def _get_document(self, operation: str = "operation") -> Any: ...
        def _simulate_autocad_click(self) -> bool: ...
        def _validate_connection(self) -> None: ...

    def get_screenshot(self) -> Dict[str, str]:
        """
        Capture a screenshot of the CAD application window.
        
        Returns:
            dict: Dictionary with 'path' and 'data' (base64)
            
        Raises:
            Exception: If screenshot fails
        """
        try:
            self._validate_connection()
            
            # Find the CAD window
            # Strategy: Search for main window based on CAD type
            search_term = ""
            if self.cad_type == "autocad":
                search_term = "Autodesk AutoCAD"
            elif self.cad_type == "zwcad":
                search_term = "ZWCAD"
            elif self.cad_type == "gcad":
                search_term = "GstarCAD"
            elif self.cad_type == "bricscad":
                search_term = "BricsCAD"
            
            hwnd = 0
            
            def enum_windows_callback(h, result):
                nonlocal hwnd
                if hwnd: return # Already found
                
                if win32gui.IsWindowVisible(h):
                    title = win32gui.GetWindowText(h)
                    # Simple case-insensitive containment check
                    if search_term.lower() in title.lower():
                        # Avoid "Application" windows (like VBA) if possible, 
                        # usually the main window has the drawing name or strict branding
                        hwnd = h

            win32gui.EnumWindows(enum_windows_callback, None)
            
            if not hwnd:
                # Fallback: Try to get HWND from the COM application object if available
                # AutoCAD Application object has 'HWND' property (sometimes hidden or different name)
                # But typically EnumWindows is more reliable if we know the title pattern.
                raise Exception(f"Could not find window for {self.cad_type}")

            # Bring to front (optional, but good for clean screenshot)
            # Handle minimized state
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception as e:
                logger.warning(f"Could not bring window to front: {e}")
            
            # Get window bounds
            rect = win32gui.GetWindowRect(hwnd)
            x, y, w, h = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
            logger.debug(f"Capturing screenshot for HWND {hwnd} at {x},{y} {w}x{h}")
            
            # Capture
            image = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
            
            # Prepare filename and resolve path using centralized utility
            filename = f"cad_screenshot_{os.getpid()}.png"
            filepath = self.resolve_export_path(filename, "images")
            
            image.save(filepath, "PNG")
            
            # Convert to base64
            with open(filepath, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            logger.info(f"Screenshot saved to {filepath}")
            
            return {
                "path": filepath,
                "data": encoded_string
            }
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            raise Exception(f"Failed to capture screenshot: {e}")

    def export_view(self) -> Dict[str, str]:
        """Export current view using internal PNGOUT command.
        
        This method uses ZWCAD's built-in PNGOUT command to export the drawing
        view to a PNG file. Unlike get_screenshot(), this method:
        - Works even if the window is minimized or obscured
        - Captures only the drawing content (no UI chrome)
        - Uses the CAD application's internal rendering
        
        Returns:
            Dictionary with 'path' and 'data' (base64 encoded image)
            
        Raises:
            Exception: If export fails
        """
        try:
            self._validate_connection()
            document = self._get_document("export_view")
            
            # Prepare filename and resolve path using centralized utility
            filename = f"cad_export_{os.getpid()}.png"
            filepath = self.resolve_export_path(filename, "images")
            
            # Ensure path uses backslashes for CAD command and is absolute
            filepath_cad = filepath.replace("/", "\\")
            
            logger.debug(f"Exporting view to {filepath_cad}")

            # Find the CAD window for focusing
            search_term = ""
            if self.cad_type == "autocad":
                search_term = "Autodesk AutoCAD"
            elif self.cad_type == "zwcad":
                search_term = "ZWCAD"
            elif self.cad_type == "gcad":
                search_term = "GstarCAD"
            elif self.cad_type == "bricscad":
                search_term = "BricsCAD"
            
            hwnd = 0
            def enum_windows_callback(h, result):
                nonlocal hwnd
                if hwnd: return
                if win32gui.IsWindowVisible(h):
                    title = win32gui.GetWindowText(h)
                    if search_term.lower() in title.lower():
                        hwnd = h

            win32gui.EnumWindows(enum_windows_callback, None)
            
            if hwnd:
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Could not focus window for export: {e}")

            # Use ESC ESC to clear any pending commands
            document.SendCommand("\x1b\x1b")
            time.sleep(0.1)
            
            # Disable file dialog
            document.SendCommand("FILEDIA 0\n")
            time.sleep(0.1)
            
            # Execute PNGOUT command with file path
            # Sequence: command, path, selection (all), finish selection
            document.SendCommand(f"_PNGOUT\n{filepath_cad}\n_ALL\n\n")
            
            # Wait briefly for file to be written
            time.sleep(1.5) # Increased wait for render
            
            # Re-enable file dialog
            document.SendCommand("FILEDIA 1\n")
            
            # Verify file was created
            if not os.path.exists(filepath):
                # Try fallback: maybe it didn't like _ALL, try just \n\n
                logger.debug("PNGOUT with _ALL failed, trying with default selection...")
                document.SendCommand(f"_PNGOUT\n{filepath_cad}\n\n")
                time.sleep(1.5)
                
            if not os.path.exists(filepath):
                raise Exception(f"Export file was not created at {filepath}")
            
            # Convert to base64
            with open(filepath, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            logger.info(f"View exported to {filepath}")
            
            return {
                "path": filepath,
                "data": encoded_string
            }
            
        except Exception as e:
            logger.error(f"Export view failed: {e}")
            raise Exception(f"Failed to export view: {e}")


    def zoom_extents(self) -> bool:
        """Zoom to show all entities."""
        try:
            application = self._get_application("zoom_extents")
            application.ZoomExtents()
            logger.debug("Zoomed to extents")
            return True
        except Exception as e:
            logger.error(f"Failed to zoom extents: {e}")
            return False

    def refresh_view(self) -> bool:
        """Refresh the view using multiple techniques for maximum compatibility.

        Uses a combination of techniques in fallback order:
        1. Application.Refresh() (COM API - no undo/redo impact)
        2. SendCommand with REDRAW (most reliable visual update)
        3. Window click simulation (forces UI update)

        Note: REDRAW command is not wrapped in UNDO to avoid complicating
        the undo/redo stack. If refresh_view is called during user operations,
        the REDRAW will be undone by the user's undo command anyway.

        Returns:
            True if refresh was attempted (best effort approach)
        """
        try:
            application = self._get_application("refresh_view")
            document = self._get_document("refresh_view")

            # Technique 1: COM API Refresh (doesn't affect undo/redo)
            try:
                application.Refresh()
                logger.debug("Refresh: COM Refresh executed")
            except Exception as e:
                logger.debug(f"COM Refresh failed: {e}")

            # Technique 2: Send REDRAW command (most reliable visual update)
            try:
                document.SendCommand("_redraw\n")
                logger.debug("Refresh: REDRAW command sent")
            except Exception as e:
                logger.debug(f"REDRAW command failed: {e}")

            # Technique 3: Simulate click on CAD window (forces UI update)
            self._simulate_autocad_click()

            return True
        except Exception as e:
            logger.debug(f"refresh_view error: {e}")
            return False

    def undo(self, count: int = 1) -> bool:
        """Undo last action(s).

        Args:
            count: Number of operations to undo (default: 1)

        Returns:
            True if successful, False otherwise
        """
        try:
            self._validate_connection()
            if count < 1:
                logger.warning(f"Invalid undo count: {count}. Must be >= 1")
                return False

            app = self._get_application("undo")
            app.ActiveDocument.SendCommand(f"_undo {count}\n")
            logger.info(f"Undo executed ({count} operation(s))")
            return True
        except Exception as e:
            logger.error(f"Failed to undo: {e}")
            return False

    def redo(self, count: int = 1) -> bool:
        """Redo last undone action(s).

        Args:
            count: Number of operations to redo (default: 1)

        Returns:
            True if successful, False otherwise
        """
        try:
            self._validate_connection()
            if count < 1:
                logger.warning(f"Invalid redo count: {count}. Must be >= 1")
                return False

            app = self._get_application("redo")
            app.ActiveDocument.SendCommand(f"_redo {count}\n")
            logger.info(f"Redo executed ({count} operation(s))")
            return True
        except Exception as e:
            logger.error(f"Failed to redo: {e}")
            return False
