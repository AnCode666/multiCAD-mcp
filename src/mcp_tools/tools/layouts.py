"""
Layout and paperspace presentation management tool.

Enables automated creation of sheets, viewports (MVIEW), and title blocks.
"""

import json
import logging
from typing import Optional, Dict, Any, List

from mcp_tools import get_current_adapter
from mcp_tools.decorators import cad_tool

logger = logging.getLogger(__name__)


def register_layout_tools(mcp):
    """Register layout and presentation management tools."""

    @cad_tool(mcp, "manage_layouts")
    def manage_layouts(
        action: str = "create",
        name: Optional[str] = None,
        paper_size: str = "A3",
        orientation: str = "landscape",
        scale: str = "1:50",
        model_center: Optional[str] = None,
        viewport_rect: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        date: Optional[str] = None,
        sheet_number: str = "1/1",
        unit: str = "m",
    ) -> str:
        """
        Manage AutoCAD paperspace layouts, sheets, viewports, and title blocks.

        Actions:
        - "create": Create a new layout sheet (e.g. A3 landscape) with frame, viewport and title block.
        - "list": List all layouts in the drawing.
        - "activate": Set layout as active sheet.
        - "delete": Remove a layout.
        - "add_viewport": Add a custom viewport to an existing layout.
        - "add_titleblock": Add a standardized AECO title block to a layout.

        Args:
            action: Action to perform ("create", "list", "activate", "delete", "add_viewport", "add_titleblock")
            name: Layout name (e.g. "Plano_01_Distribucion")
            paper_size: Standard paper format ("A4", "A3", "A2", "A1", "A0", "LETTER", "TABLOID")
            orientation: Sheet orientation ("landscape" or "portrait")
            scale: Architectural scale ("1:50", "1:100", "1:20", "1:200", "1:500", "1:10", "1:1")
            model_center: Modelspace center coordinates to focus ("x,y", e.g. "15.0, 10.0")
            viewport_rect: Custom viewport center and size "cx,cy,w,h" (in paper mm)
            title: Project or sheet title for title block
            author: Author or collegiate engineer name
            date: Drawing date
            sheet_number: Sheet code or numbering (e.g. "PL-01", "1/4")
            unit: Model units ("m" for meters, "mm" for millimeters)
        """
        adapter = get_current_adapter()
        action_lower = action.lower().strip()

        if action_lower == "list":
            layouts = adapter.list_layouts()
            return json.dumps({
                "success": True,
                "count": len(layouts),
                "layouts": layouts,
            }, indent=2, ensure_ascii=False)

        elif action_lower in ("create", "new"):
            if not name:
                name = "Plano_01"

            res = adapter.create_layout(
                name=name,
                paper_size=paper_size,
                orientation=orientation,
            )

            # Auto-add title block if requested or if title is provided
            tb_info = None
            if title or author:
                tb_info = adapter.add_titleblock(
                    layout_name=name,
                    title=title or name.replace("_", " ").upper(),
                    author=author or "",
                    date=date or "",
                    scale=scale,
                    sheet_number=sheet_number,
                    paper_size=paper_size,
                    orientation=orientation,
                )

            # Auto-add centered viewport
            vp_handle = None
            pw = res.get("width_mm", 420.0)
            ph = res.get("height_mm", 297.0)

            mc = (0.0, 0.0)
            if model_center:
                from mcp_tools.helpers import parse_coordinate
                mc_coord = parse_coordinate(model_center)
                mc = (mc_coord[0], mc_coord[1])

            if viewport_rect:
                parts = [float(p.strip()) for p in viewport_rect.split(",")]
                if len(parts) >= 4:
                    vp_handle = adapter.add_viewport(
                        layout_name=name,
                        center=(parts[0], parts[1]),
                        width=parts[2],
                        height=parts[3],
                        view_center=mc,
                        scale=scale,
                        unit=unit,
                    )
            else:
                # Centered viewport occupying top/center area of sheet
                vp_w = pw - 40.0
                vp_h = ph - (65.0 if tb_info else 40.0)
                vp_cx = pw / 2.0
                vp_cy = ph - (vp_h / 2.0) - 15.0
                vp_handle = adapter.add_viewport(
                    layout_name=name,
                    center=(vp_cx, vp_cy),
                    width=vp_w,
                    height=vp_h,
                    view_center=mc,
                    scale=scale,
                    unit=unit,
                )

            return json.dumps({
                "success": True,
                "layout": res,
                "viewport_handle": vp_handle,
                "titleblock": tb_info,
                "message": f"Layout sheet '{name}' created ({paper_size} {orientation}, scale {scale}).",
            }, indent=2, ensure_ascii=False)

        elif action_lower in ("activate", "switch"):
            if not name:
                return json.dumps({"success": False, "error": "Layout 'name' required to activate."})
            ok = adapter.activate_layout(name)
            return json.dumps({"success": ok, "name": name})

        elif action_lower in ("delete", "remove"):
            if not name:
                return json.dumps({"success": False, "error": "Layout 'name' required to delete."})
            ok = adapter.delete_layout(name)
            return json.dumps({"success": ok, "deleted": name})

        elif action_lower == "add_viewport":
            if not name:
                return json.dumps({"success": False, "error": "Layout 'name' required."})
            mc = (0.0, 0.0)
            if model_center:
                from mcp_tools.helpers import parse_coordinate
                mc_coord = parse_coordinate(model_center)
                mc = (mc_coord[0], mc_coord[1])

            cx, cy, w, h = 200.0, 150.0, 300.0, 200.0
            if viewport_rect:
                parts = [float(p.strip()) for p in viewport_rect.split(",")]
                if len(parts) >= 4:
                    cx, cy, w, h = parts[0], parts[1], parts[2], parts[3]

            vh = adapter.add_viewport(
                layout_name=name,
                center=(cx, cy),
                width=w,
                height=h,
                view_center=mc,
                scale=scale,
                unit=unit,
            )
            return json.dumps({
                "success": True,
                "layout": name,
                "viewport_handle": vh,
                "scale": scale,
                "center": (cx, cy),
                "size": (w, h),
            }, indent=2, ensure_ascii=False)

        elif action_lower == "add_titleblock":
            if not name:
                return json.dumps({"success": False, "error": "Layout 'name' required."})
            tb = adapter.add_titleblock(
                layout_name=name,
                title=title or "PLANO DE PROYECTO",
                author=author or "",
                date=date or "",
                scale=scale,
                sheet_number=sheet_number,
                paper_size=paper_size,
                orientation=orientation,
            )
            return json.dumps({"success": True, "titleblock": tb}, indent=2, ensure_ascii=False)

        else:
            return json.dumps({"success": False, "error": f"Unknown layout action: {action}"})
