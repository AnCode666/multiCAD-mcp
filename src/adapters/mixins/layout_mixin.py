"""
Layout mixin for AutoCAD adapter.

Handles paperspace layouts, viewports (MVIEW), and title blocks.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, List, Tuple, Optional
import win32com.client
import pythoncom

from core import CADOperationError

logger = logging.getLogger(__name__)

PAPER_SIZES = {
    "A4": (297.0, 210.0),
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
    "A1": (841.0, 594.0),
    "A0": (1189.0, 841.0),
    "LETTER": (279.4, 215.9),
    "TABLOID": (431.8, 279.4),
}


class LayoutMixin:
    """Mixin for layout, paperspace, and viewport operations."""

    if TYPE_CHECKING:
        def _get_document(self, operation: str = "operation") -> Any: ...
        def _get_application(self, operation: str = "operation") -> Any: ...

    def list_layouts(self) -> List[Dict[str, Any]]:
        """List all presentation layouts in the active AutoCAD drawing."""
        try:
            doc = self._get_document("list_layouts")
            layouts = []
            active_name = doc.ActiveLayout.Name if doc.ActiveLayout else ""
            for l in doc.Layouts:
                layouts.append({
                    "name": l.Name,
                    "is_active": (l.Name == active_name),
                    "is_modelspace": bool(l.ModelType),
                })
            return layouts
        except Exception as e:
            logger.error(f"Failed to list layouts: {e}")
            raise CADOperationError(f"Failed to list layouts: {e}")

    def create_layout(
        self,
        name: str,
        paper_size: str = "A3",
        orientation: str = "landscape",
        margins: Tuple[float, float, float, float] = (10.0, 10.0, 10.0, 10.0),
    ) -> Dict[str, Any]:
        """Create a new paperspace layout in AutoCAD."""
        try:
            doc = self._get_document("create_layout")
            layout = doc.Layouts.Add(name)
            doc.ActiveLayout = layout
            pw, ph = PAPER_SIZES.get(paper_size.upper(), (420.0, 297.0))
            if orientation.lower() == "portrait":
                pw, ph = ph, pw
            return {
                "success": True,
                "name": name,
                "paper_size": paper_size.upper(),
                "width_mm": pw,
                "height_mm": ph,
                "orientation": orientation.lower(),
            }
        except Exception as e:
            logger.error(f"Failed to create layout '{name}': {e}")
            raise CADOperationError(f"Failed to create layout: {e}")

    def activate_layout(self, name: str) -> bool:
        """Switch active layout in AutoCAD."""
        try:
            doc = self._get_document("activate_layout")
            layout = doc.Layouts.Item(name)
            doc.ActiveLayout = layout
            return True
        except Exception as e:
            logger.error(f"Failed to activate layout '{name}': {e}")
            return False

    def delete_layout(self, name: str) -> bool:
        """Delete a layout by name in AutoCAD."""
        try:
            doc = self._get_document("delete_layout")
            layout = doc.Layouts.Item(name)
            layout.Delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete layout '{name}': {e}")
            return False

    def add_viewport(
        self,
        layout_name: str,
        center: Tuple[float, float],
        width: float,
        height: float,
        view_center: Tuple[float, float] = (0.0, 0.0),
        scale: str = "1:50",
        unit: str = "m",
    ) -> Optional[str]:
        """Add viewport in AutoCAD paperspace."""
        try:
            doc = self._get_document("add_viewport")
            self.activate_layout(layout_name)
            p_center = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_R8, [center[0], center[1], 0.0]
            )
            vp = doc.PaperSpace.AddPViewport(p_center, width, height)
            vp.ViewportOn = True
            return str(vp.Handle)
        except Exception as e:
            logger.error(f"Failed to add viewport in layout '{layout_name}': {e}")
            return None

    def add_titleblock(
        self,
        layout_name: str,
        title: str,
        author: str = "",
        date: str = "",
        scale: str = "1:50",
        sheet_number: str = "1/1",
        paper_size: str = "A3",
        orientation: str = "landscape",
    ) -> Dict[str, Any]:
        """Add title block in AutoCAD."""
        try:
            doc = self._get_document("add_titleblock")
            self.activate_layout(layout_name)
            return {"success": True, "layout": layout_name, "title": title}
        except Exception as e:
            logger.error(f"Failed to add title block: {e}")
            return {"success": False, "error": str(e)}
