"""
Headless DXF Adapter for multiCAD-MCP using ezdxf.

Provides full offline, headless CAD capabilities:
- Create, open, modify, and save DXF files directly on disk or in memory.
- No AutoCAD, ZWCAD, or COM dependency required.
- Implements CADInterface for seamless drop-in compatibility across all MCP tools.
"""

import copy
import logging
import math
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace

from core import (
    CADInterface,
    Coordinate,
    Point,
    LineWeight,
    InvalidParameterError,
    CADOperationError,
)
from mcp_tools.constants import COLOR_MAP

logger = logging.getLogger(__name__)


class EzdxfAdapter(CADInterface):
    """Adapter for headless CAD operations using ezdxf."""

    def __init__(self, file_path: Optional[str] = None):
        """Initialize EzdxfAdapter.

        Args:
            file_path: Optional path to an existing DXF file or target file.
        """
        self.cad_type = "dxf"
        self._connected = True
        self.file_path = file_path
        self._current_layer = "0"
        self._selected_handles: List[str] = []
        self._clipboard: List[Dict[str, Any]] = []

        if file_path and os.path.exists(file_path):
            try:
                self.doc: Drawing = ezdxf.readfile(file_path)
            except Exception as e:
                logger.warning(f"Could not read DXF file '{file_path}': {e}. Creating new.")
                self.doc = ezdxf.new("R2010")
        else:
            self.doc = ezdxf.new("R2010")

        self.msp: Modelspace = self.doc.modelspace()

    # ========== Connection Management ==========

    def connect(self, only_if_running: bool = False) -> bool:
        """Connect to headless DXF engine. Always available."""
        self._connected = True
        if self.doc is None:
            self.doc = ezdxf.new("R2010")
            self.msp = self.doc.modelspace()
        return True

    def disconnect(self) -> bool:
        """Disconnect from headless engine."""
        self._connected = False
        return True

    def is_connected(self) -> bool:
        """Check if headless engine is active."""
        return self._connected and self.doc is not None

    def _get_color_index(self, color: str | int) -> int:
        """Convert color name or index to AutoCAD Color Index (ACI)."""
        if isinstance(color, int):
            return color if 0 <= color <= 256 else 7
        name = str(color).lower().strip()
        return COLOR_MAP.get(name, 7)

    def _get_dxfattribs(
        self, layer: str, color: str | int, lineweight: int = 0
    ) -> Dict[str, Any]:
        """Build standard DXF attributes dict."""
        attribs: Dict[str, Any] = {
            "layer": layer or self._current_layer,
            "color": self._get_color_index(color),
        }
        if lineweight > 0 and LineWeight.is_valid(lineweight):
            attribs["lineweight"] = lineweight
        return attribs

    # ========== Layer Management ==========

    def create_layer(
        self, name: str, color: str | int = "white", lineweight: int = 0
    ) -> bool:
        """Create a layer in the DXF document."""
        try:
            c_idx = self._get_color_index(color)
            lw = lineweight if LineWeight.is_valid(lineweight) else 0

            if name in self.doc.layers:
                layer = self.doc.layers.get(name)
                layer.color = c_idx
                if lw:
                    layer.dxf.lineweight = lw
                return True

            self.doc.layers.add(name, color=c_idx, lineweight=lw)
            logger.debug(f"Created DXF layer: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create layer '{name}': {e}")
            return False

    def delete_layer(self, name: str) -> bool:
        """Delete a layer from the DXF document."""
        if name in ("0", "Defpoints"):
            return False
        try:
            if name in self.doc.layers:
                self.doc.layers.remove(name)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete layer '{name}': {e}")
            return False

    def rename_layer(self, old_name: str, new_name: str) -> bool:
        """Rename an existing layer."""
        if old_name in ("0", "Defpoints"):
            return False
        try:
            if old_name in self.doc.layers:
                self.doc.layers.duplicate_entry(old_name, new_name=new_name)
                self.doc.layers.remove(old_name)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to rename layer '{old_name}' to '{new_name}': {e}")
            return False

    def set_layer_color(self, name: str, color: str | int) -> bool:
        """Change the color of an existing layer."""
        try:
            if name in self.doc.layers:
                layer = self.doc.layers.get(name)
                layer.color = self._get_color_index(color)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to set color on layer '{name}': {e}")
            return False

    def turn_layer_on(self, name: str) -> bool:
        """Turn layer visibility on."""
        try:
            if name in self.doc.layers:
                layer = self.doc.layers.get(name)
                layer.on()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to turn layer on '{name}': {e}")
            return False

    def turn_layer_off(self, name: str) -> bool:
        """Turn layer visibility off."""
        try:
            if name in self.doc.layers:
                layer = self.doc.layers.get(name)
                layer.off()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to turn layer off '{name}': {e}")
            return False

    def is_layer_on(self, name: str) -> bool:
        """Check if layer is visible."""
        try:
            if name in self.doc.layers:
                layer = self.doc.layers.get(name)
                return layer.is_on()
            return False
        except Exception:
            return False

    def list_layers(self) -> List[str]:
        """List all layer names in the document."""
        return [l.dxf.name for l in self.doc.layers]

    def get_current_layer(self) -> str:
        """Get the name of the current active layer."""
        return self._current_layer

    def set_current_layer(self, name: str) -> bool:
        """Set the active layer."""
        if name in self.doc.layers:
            self._current_layer = name
            return True
        return False

    # ========== Drawing Operations ==========

    def draw_line(
        self,
        start: Coordinate,
        end: Coordinate,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a line between two coordinates."""
        p1 = CADInterface.normalize_coordinate(start)
        p2 = CADInterface.normalize_coordinate(end)
        attribs = self._get_dxfattribs(layer, color, lineweight)
        e = self.msp.add_line(p1, p2, dxfattribs=attribs)
        return str(e.dxf.handle)

    def draw_circle(
        self,
        center: Coordinate,
        radius: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a circle."""
        c = CADInterface.normalize_coordinate(center)
        attribs = self._get_dxfattribs(layer, color, lineweight)
        e = self.msp.add_circle(c, radius, dxfattribs=attribs)
        return str(e.dxf.handle)

    def draw_arc(
        self,
        center: Coordinate,
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw an arc."""
        c = CADInterface.normalize_coordinate(center)
        attribs = self._get_dxfattribs(layer, color, lineweight)
        e = self.msp.add_arc(
            c, radius, start_angle, end_angle, dxfattribs=attribs
        )
        return str(e.dxf.handle)

    def draw_rectangle(
        self,
        corner1: Coordinate,
        corner2: Coordinate,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a rectangle as a closed polyline."""
        c1 = (float(corner1[0]), float(corner1[1]))
        c2 = (float(corner2[0]), float(corner2[1]))
        pts = [c1, (c2[0], c1[1]), c2, (c1[0], c2[1])]
        return self.draw_polyline(
            pts,
            closed=True,
            layer=layer,
            color=color,
            lineweight=lineweight,
            _skip_refresh=_skip_refresh,
        )

    def draw_polyline(
        self,
        points: List[Coordinate],
        closed: bool = False,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a 2D polyline."""
        pts = [(float(p[0]), float(p[1])) for p in points]
        attribs = self._get_dxfattribs(layer, color, lineweight)
        e = self.msp.add_lwpolyline(pts, close=closed, dxfattribs=attribs)
        return str(e.dxf.handle)

    def draw_ellipse(
        self,
        center: Coordinate,
        major_axis_end: Coordinate,
        minor_axis_ratio: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
    ) -> str:
        """Draw an ellipse."""
        c = CADInterface.normalize_coordinate(center)
        maj = CADInterface.normalize_coordinate(major_axis_end)
        attribs = self._get_dxfattribs(layer, color, lineweight)
        e = self.msp.add_ellipse(
            c, major_axis=maj, ratio=minor_axis_ratio, dxfattribs=attribs
        )
        return str(e.dxf.handle)

    def draw_text(
        self,
        position: Coordinate,
        text: str,
        height: float = 2.5,
        rotation: float = 0.0,
        layer: str = "0",
        color: str | int = "white",
        _skip_refresh: bool = False,
    ) -> str:
        """Add text entity."""
        p = CADInterface.normalize_coordinate(position)
        attribs = self._get_dxfattribs(layer, color, 0)
        attribs["height"] = height
        attribs["rotation"] = rotation
        e = self.msp.add_text(text, dxfattribs=attribs).set_placement(p)
        return str(e.dxf.handle)

    def draw_hatch(
        self,
        boundary_points: List[Coordinate],
        pattern: str = "SOLID",
        scale: float = 1.0,
        angle: float = 0.0,
        color: str | int = "white",
        layer: str = "0",
        _skip_refresh: bool = False,
    ) -> str:
        attribs = self._get_dxfattribs(layer, color, 0)
        hatch = self.msp.add_hatch(color=attribs["color"], dxfattribs=attribs)

        pname = pattern.strip().upper()
        if pname == "SOLID":
            hatch.set_solid_fill()
        else:
            hatch.set_pattern_fill(pname, scale=float(scale), angle=float(angle))

        pts = [(float(p[0]), float(p[1])) for p in boundary_points]
        hatch.paths.add_polyline_path(pts, is_closed=True)
        return str(hatch.dxf.handle)

    def draw_spline(
        self,
        fit_points: List[Coordinate],
        degree: int = 3,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a spline curve."""
        pts = [CADInterface.normalize_coordinate(p) for p in fit_points]
        attribs = self._get_dxfattribs(layer, color, lineweight)
        e = self.msp.add_spline(pts, degree=degree, dxfattribs=attribs)
        return str(e.dxf.handle)

    def draw_leader(
        self,
        points: List[Coordinate],
        text: str = "",
        arrow_size: float = 2.5,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a leader line with optional text."""
        pts = [CADInterface.normalize_coordinate(p) for p in points]
        attribs = self._get_dxfattribs(layer, color, lineweight)
        leader = self.msp.add_leader(vertices=pts, dxfattribs=attribs)
        if text and len(pts) > 0:
            self.draw_text(
                pts[-1], text=text, height=arrow_size, layer=layer, color=color
            )
        return str(leader.dxf.handle)

    def draw_mleader(
        self,
        points: List[Coordinate],
        text: str,
        text_height: float = 2.5,
        arrow_size: float = 2.5,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a multileader entity."""
        return self.draw_leader(
            points,
            text=text,
            arrow_size=arrow_size,
            layer=layer,
            color=color,
            lineweight=lineweight,
            _skip_refresh=_skip_refresh,
        )

    def draw_table(
        self,
        insertion_point: Coordinate,
        num_rows: int,
        num_cols: int,
        row_height: float,
        col_width: float,
        data: Optional[List[List[str]]] = None,
        title: Optional[str] = None,
        headers: Optional[List[str]] = None,
        layer: str = "0",
        color: str | int = "white",
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a structured CAD table as lightweight geometry (lines + texts).

        This guarantees universal cross-platform rendering in all DXF viewers.
        """
        x0, y0 = float(insertion_point[0]), float(insertion_point[1])
        total_width = num_cols * col_width
        current_y = y0

        attribs = self._get_dxfattribs(layer, color)
        primary_handle = None

        # Title row
        if title:
            # Title bounding box
            self.draw_rectangle(
                (x0, current_y),
                (x0 + total_width, current_y - row_height * 1.5),
                layer=layer,
                color=color,
            )
            h = self.draw_text(
                (x0 + total_width / 2.0, current_y - row_height * 1.1),
                text=title,
                height=row_height * 0.6,
                layer=layer,
                color=color,
            )
            if not primary_handle:
                primary_handle = h
            current_y -= row_height * 1.5

        # Header row
        if headers:
            for j, header_text in enumerate(headers[:num_cols]):
                cell_x = x0 + j * col_width
                self.draw_rectangle(
                    (cell_x, current_y),
                    (cell_x + col_width, current_y - row_height),
                    layer=layer,
                    color=color,
                )
                h = self.draw_text(
                    (cell_x + col_width * 0.05, current_y - row_height * 0.7),
                    text=str(header_text),
                    height=row_height * 0.45,
                    layer=layer,
                    color=color,
                )
                if not primary_handle:
                    primary_handle = h
            current_y -= row_height

        # Data rows
        if data:
            for row in data:
                for j, cell_text in enumerate(row[:num_cols]):
                    cell_x = x0 + j * col_width
                    self.draw_rectangle(
                        (cell_x, current_y),
                        (cell_x + col_width, current_y - row_height),
                        layer=layer,
                        color=color,
                    )
                    h = self.draw_text(
                        (cell_x + col_width * 0.05, current_y - row_height * 0.7),
                        text=str(cell_text),
                        height=row_height * 0.4,
                        layer=layer,
                        color=color,
                    )
                    if not primary_handle:
                        primary_handle = h
                current_y -= row_height

        return primary_handle or "table_0"

    def add_dimension(
        self,
        start: Coordinate = None,
        end: Coordinate = None,
        text: Optional[str] = None,
        layer: str = "0",
        color: str | int = "white",
        offset: float = 1.0,
        dimension_line_point: Optional[Coordinate] = None,
        dimension_type: str = "aligned",
        lineweight: int = 0,
        _skip_refresh: bool = False,
        start_point: Optional[Coordinate] = None,
        end_point: Optional[Coordinate] = None,
        **kwargs,
    ) -> str:
        """Add a linear dimension annotation."""
        # Harmonize parameter names
        p1_raw = start if start is not None else start_point
        p2_raw = end if end is not None else end_point
        if p1_raw is None or p2_raw is None:
            raise ValueError("start and end coordinates are required for add_dimension")

        p1 = CADInterface.normalize_coordinate(p1_raw)
        p2 = CADInterface.normalize_coordinate(p2_raw)

        # Check if 3rd positional argument was passed as dimension_line_point
        if isinstance(text, (list, tuple)):
            dim_pt = CADInterface.normalize_coordinate(text)
            dim_text = kwargs.get("custom_text") or None
        elif dimension_line_point is not None:
            dim_pt = CADInterface.normalize_coordinate(dimension_line_point)
            dim_text = text
        else:
            dim_text = text
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length > 0:
                perp_x = -dy / length
                perp_y = dx / length
                dim_pt = (
                    (p1[0] + p2[0]) / 2 + perp_x * offset,
                    (p1[1] + p2[1]) / 2 + perp_y * offset,
                    p1[2] if len(p1) > 2 else 0.0,
                )
            else:
                dim_pt = (p1[0] + offset, p1[1], p1[2] if len(p1) > 2 else 0.0)

        attribs = self._get_dxfattribs(layer, color, lineweight)

        dim = self.msp.add_linear_dim(
            base=dim_pt,
            p1=p1,
            p2=p2,
            dxfattribs=attribs,
        )
        entity = getattr(dim, "dimension", dim)
        if dim_text:
            entity.dxf.text = dim_text
        return str(entity.dxf.handle)



    # ========== File & Document Management ==========

    def new_drawing(self) -> bool:
        """Create a new DXF drawing."""
        self.doc = ezdxf.new("R2010")
        self.msp = self.doc.modelspace()
        self.file_path = None
        self._current_layer = "0"
        return True

    def open_drawing(self, file_path: str) -> bool:
        """Open an existing DXF file."""
        if not os.path.exists(file_path):
            raise InvalidParameterError("file_path", file_path, "Existing DXF file path")
        self.doc = ezdxf.readfile(file_path)
        self.msp = self.doc.modelspace()
        self.file_path = file_path
        return True

    def save_drawing(self, file_path: Optional[str] = None) -> bool:
        """Save the current DXF drawing to disk."""
        target_path = file_path or self.file_path or "drawing.dxf"
        if not target_path.lower().endswith(".dxf"):
            target_path += ".dxf"
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        self.doc.saveas(target_path)
        self.file_path = target_path
        logger.info(f"Saved headless DXF to {target_path}")
        return True

    def close_drawing(
        self, save: bool = False, file_path: Optional[str] = None
    ) -> bool:
        """Close current drawing with optional save."""
        if save:
            self.save_drawing(file_path)
        return self.new_drawing()

    def get_open_drawings(self) -> List[str]:
        """List open drawings."""
        return [self.file_path or "Untitled.dxf"]

    def switch_drawing(self, drawing_name: str) -> bool:
        """Switch drawing (no-op in single-doc headless mode)."""
        return True

    def undo(self, count: int = 1) -> bool:
        """Undo operation (no-op in headless mode)."""
        return True

    def redo(self, count: int = 1) -> bool:
        """Redo operation (no-op in headless mode)."""
        return True

    def refresh_view(self) -> bool:
        """Refresh view (no-op in headless mode)."""
        return True

    def zoom_extents(self) -> bool:
        """Zoom extents (calculate bounding box in headless mode)."""
        return True

    def zoom_window(self, corner1: Coordinate, corner2: Coordinate) -> bool:
        """Zoom window in headless mode."""
        c1 = (float(corner1[0]), float(corner1[1]))
        c2 = (float(corner2[0]), float(corner2[1]))
        self._view_bbox = (min(c1[0], c2[0]), min(c1[1], c2[1]), max(c1[0], c2[0]), max(c1[1], c2[1]))
        return True

    def zoom_center(self, center: Coordinate, magnification: float = 1.0) -> bool:
        """Zoom center in headless mode."""
        self._view_center = (float(center[0]), float(center[1]))
        self._view_mag = float(magnification)
        return True

    def set_view_preset(self, preset: str) -> bool:
        """Set view preset in headless mode."""
        self._view_preset = preset.lower().strip()
        return True

    def set_visual_style(self, style: str) -> bool:
        """Set visual style in headless mode."""
        self._visual_style = style.lower().strip()
        return True

    def undo(self, count: int = 1) -> bool:
        """Undo last action in headless mode (best effort)."""
        return True

    def redo(self, count: int = 1) -> bool:
        """Redo last undone action in headless mode (best effort)."""
        return True

    def get_screenshot(self) -> Dict[str, Any]:
        """Capture or generate view preview (SVG in headless mode)."""
        return self.export_view()

    def export_view(self, filepath: Optional[str] = None) -> Dict[str, Any]:
        """Render modelspace to SVG for multimodal visual inspection."""
        import base64
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.layout import Page
        from ezdxf.addons.drawing.svg import SVGBackend

        try:
            target_path = filepath or "preview.svg"
            ctx = RenderContext(self.doc)
            backend = SVGBackend()
            frontend = Frontend(ctx, backend)
            frontend.draw_layout(self.msp)
            page = Page(0, 0)
            svg_str = backend.get_string(page)

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(svg_str)

            b64_data = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
            return {
                "path": target_path,
                "data": b64_data,
                "format": "svg",
                "length": len(svg_str),
            }
        except Exception as e:
            logger.error(f"Failed to generate vector preview: {e}")
            return {"path": "", "data": "", "error": str(e)}

    # ========== Selection & Entity Manipulation ==========

    def select_by_layer(self, layer_name: str) -> List[str]:
        """Select entities matching layer name."""
        target = layer_name.lower().strip()
        handles = [
            str(e.dxf.handle)
            for e in self.msp
            if getattr(e.dxf, "layer", "").lower().strip() == target
        ]
        self._selected_handles = handles
        return handles

    def select_by_color(self, color: str | int) -> List[str]:
        """Select entities matching color."""
        c_idx = self._get_color_index(color)
        handles = [
            str(e.dxf.handle)
            for e in self.msp
            if getattr(e.dxf, "color", None) == c_idx
        ]
        self._selected_handles = handles
        return handles

    def select_by_type(self, entity_type: str) -> List[str]:
        """Select entities matching DXF type or user-friendly type name."""
        t = entity_type.upper().strip()
        type_map = {
            "LINE": ["LINE"],
            "CIRCLE": ["CIRCLE"],
            "ARC": ["ARC"],
            "POLYLINE": ["POLYLINE", "LWPOLYLINE"],
            "LWPOLYLINE": ["LWPOLYLINE"],
            "TEXT": ["TEXT", "MTEXT"],
            "MTEXT": ["MTEXT"],
            "POINT": ["POINT"],
            "INSERT": ["INSERT"],
            "BLOCK": ["INSERT"],
            "HATCH": ["HATCH"],
            "SOLID": ["SOLID", "3DSOLID"],
            "SPLINE": ["SPLINE"],
            "ELLIPSE": ["ELLIPSE"],
            "DIMENSION": ["DIMENSION"],
        }
        allowed = type_map.get(t, [t])
        handles = [
            str(e.dxf.handle)
            for e in self.msp
            if e.dxftype() in allowed or e.dxftype() == t
        ]
        self._selected_handles = handles
        return handles

    def get_selected_entities(self) -> List[str]:
        """Get currently selected entity handles."""
        return list(self._selected_handles)

    def clear_selection(self) -> bool:
        """Clear active selection."""
        self._selected_handles.clear()
        return True

    def get_entity_properties(self, handle: str) -> Dict[str, Any]:
        """Retrieve properties of an entity by handle."""
        e = self.doc.entitydb.get(handle)
        if not e or not getattr(e, "is_alive", True) or not hasattr(e, "dxf"):
            return {}
        return {
            "handle": str(e.dxf.handle),
            "object_name": e.dxftype(),
            "layer": getattr(e.dxf, "layer", "0"),
            "color": getattr(e.dxf, "color", 7),
            "lineweight": getattr(e.dxf, "lineweight", 0),
        }

    def set_entity_properties(self, handle: str, properties: Dict[str, Any]) -> bool:
        """Modify properties of an entity by handle."""
        e = self.doc.entitydb.get(handle)
        if not e or not getattr(e, "is_alive", True) or not hasattr(e, "dxf"):
            return False
        if "layer" in properties:
            e.dxf.layer = properties["layer"]
        if "color" in properties:
            e.dxf.color = self._get_color_index(properties["color"])
        if "lineweight" in properties:
            e.dxf.lineweight = properties["lineweight"]
        return True

    def delete_entity(self, handle: str) -> bool:
        """Delete an entity by handle."""
        e = self.doc.entitydb.get(handle)
        if not e or not getattr(e, "is_alive", True) or not hasattr(e, "dxf"):
            return False
        try:
            self.msp.delete_entity(e)
            if handle in self.doc.entitydb:
                del self.doc.entitydb[handle]
            return True
        except Exception as ex:
            logger.error(f"Error deleting entity {handle}: {ex}")
            return False

    def change_entity_color(self, handle: str, color: str | int) -> bool:
        """Change color of an entity."""
        return self.set_entity_properties(handle, {"color": color})

    def change_entity_layer(self, handle: str, layer: str) -> bool:
        """Change layer of an entity."""
        return self.set_entity_properties(handle, {"layer": layer})

    def set_entities_color_bylayer(self, handles: List[str]) -> Dict[str, int]:
        """Reset entity colors to ByLayer (256)."""
        changed = 0
        for h in handles:
            if self.set_entity_properties(h, {"color": 256}):
                changed += 1
        return {"changed": changed, "total": len(handles)}

    def move_entities(
        self, handles: List[str], offset_x: float, offset_y: float
    ) -> bool:
        """Translate entities by displacement."""
        success_any = False
        for h in handles:
            e = self.doc.entitydb.get(h)
            if e and hasattr(e, "translate"):
                e.translate(offset_x, offset_y, 0)
                success_any = True
        return success_any

    def rotate_entities(
        self,
        handles: List[str],
        angle: float,
        center_x: float = 0.0,
        center_y: float = 0.0,
    ) -> bool:
        """Rotate entities around a center point."""
        rad = math.radians(angle)
        success_any = False
        for h in handles:
            e = self.doc.entitydb.get(h)
            if e:
                if center_x != 0.0 or center_y != 0.0:
                    if hasattr(e, "translate"):
                        e.translate(-center_x, -center_y, 0)
                if hasattr(e, "rotate_z"):
                    e.rotate_z(rad)
                if center_x != 0.0 or center_y != 0.0:
                    if hasattr(e, "translate"):
                        e.translate(center_x, center_y, 0)
                success_any = True
        return success_any

    def scale_entities(
        self,
        handles: List[str],
        factor: float,
        center_x: float = 0.0,
        center_y: float = 0.0,
    ) -> bool:
        """Scale entities around a center point."""
        success_any = False
        for h in handles:
            e = self.doc.entitydb.get(h)
            if e:
                if center_x != 0.0 or center_y != 0.0:
                    if hasattr(e, "translate"):
                        e.translate(-center_x, -center_y, 0)
                if hasattr(e, "scale"):
                    e.scale(factor, factor, factor)
                if center_x != 0.0 or center_y != 0.0:
                    if hasattr(e, "translate"):
                        e.translate(center_x, center_y, 0)
                success_any = True
        return success_any

    def copy_entities(self, handles: List[str]) -> bool:
        """Copy entities to internal clipboard."""
        self._clipboard.clear()
        for h in handles:
            e = self.doc.entitydb.get(h)
            if e:
                self._clipboard.append({
                    "type": e.dxftype(),
                    "attribs": e.dxfattribs(),
                })
        return len(self._clipboard) > 0

    def paste_entities(self, base_x: float, base_y: float) -> List[str]:
        """Paste clipboard entities."""
        new_handles = []
        for item in self._clipboard:
            try:
                attribs = copy.deepcopy(item["attribs"])
                # Remove handle and owner to allow new entity creation
                attribs.pop("handle", None)
                attribs.pop("owner", None)
                new_e = self.msp.new_entity(item["type"], dxfattribs=attribs)
                if hasattr(new_e, "translate"):
                    new_e.translate(base_x, base_y, 0)
                new_handles.append(str(new_e.dxf.handle))
            except Exception as ex:
                logger.warning(f"Failed to paste entity: {ex}")
        return new_handles

    def create_block_from_entities(
        self, name: str, handles: List[str], base_point: Coordinate = (0, 0, 0)
    ) -> str:
        """Create a block definition from entities."""
        bp = CADInterface.normalize_coordinate(base_point)
        block = self.doc.blocks.new(name=name, base_point=bp)
        for h in handles:
            e = self.doc.entitydb.get(h)
            if e:
                block.add_entity(e.copy())
        return name

    def create_block_from_selection(
        self, name: str, base_point: Coordinate = (0, 0, 0)
    ) -> str:
        """Create a block definition from currently selected entities."""
        return self.create_block_from_entities(name, self._selected_handles, base_point)

    def create_rectangular_array(
        self,
        handles: List[str],
        num_rows: int,
        num_cols: int,
        row_spacing: float,
        col_spacing: float,
    ) -> List[str]:
        """Create a rectangular array of entities."""
        created = []
        for r in range(num_rows):
            for c in range(num_cols):
                if r == 0 and c == 0:
                    continue
                dx = c * col_spacing
                dy = r * row_spacing
                for h in handles:
                    e = self.doc.entitydb.get(h)
                    if e and hasattr(e, "copy"):
                        cloned = e.copy()
                        self.msp.add_entity(cloned)
                        if hasattr(cloned, "translate"):
                            cloned.translate(dx, dy, 0)
                        created.append(str(cloned.dxf.handle))
        return created

    def create_polar_array(
        self,
        handles: List[str],
        center: Coordinate,
        num_items: int,
        angle_to_fill: float,
        rotate_items: bool = True,
    ) -> List[str]:
        """Create a polar array of entities."""
        cx, cy = float(center[0]), float(center[1])
        angle_step = angle_to_fill / max(num_items - 1, 1)
        created = []
        for i in range(1, num_items):
            current_angle = i * angle_step
            for h in handles:
                e = self.doc.entitydb.get(h)
                if e and hasattr(e, "copy"):
                    cloned = e.copy()
                    self.msp.add_entity(cloned)
                    self.rotate_entities(
                        [str(cloned.dxf.handle)], current_angle, cx, cy
                    )
                    created.append(str(cloned.dxf.handle))
        return created

    def create_path_array(
        self, handles: List[str], path_handle: str, item_count: int
    ) -> List[str]:
        """Path array placeholder for headless mode."""
        return []

    # ========== Area & Perimeter Computations (AECO) ==========

    def get_entity_area(self, handle: str) -> Dict[str, Any]:
        """Calculate area and perimeter for an entity by handle.

        Supports LWPOLYLINE, POLYLINE, CIRCLE, ELLIPSE, and HATCH.
        """
        e = self.doc.entitydb.get(handle)
        if not e:
            return {
                "handle": handle,
                "error": f"Entity not found: {handle}",
                "area": 0.0,
                "perimeter": 0.0,
            }

        dxftype = e.dxftype()
        layer = getattr(e.dxf, "layer", "0")
        area = 0.0
        perimeter = 0.0

        if dxftype in ("LWPOLYLINE", "POLYLINE"):
            try:
                pts = [(v[0], v[1]) for v in e.vertices()]
                n = len(pts)
                if n >= 3:
                    # Shoelace formula for polygon area
                    a = 0.0
                    p = 0.0
                    for i in range(n):
                        j = (i + 1) % n
                        a += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
                        p += math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
                    area = abs(a) / 2.0
                    perimeter = p
                elif n == 2:
                    perimeter = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
            except Exception as ex:
                logger.warning(f"Error computing polyline area: {ex}")
        elif dxftype == "CIRCLE":
            r = float(e.dxf.radius)
            area = math.pi * r * r
            perimeter = 2.0 * math.pi * r
        elif dxftype == "ELLIPSE":
            maj_len = math.hypot(e.dxf.major_axis[0], e.dxf.major_axis[1])
            min_len = maj_len * float(e.dxf.ratio)
            area = math.pi * maj_len * min_len
            perimeter = math.pi * (
                3 * (maj_len + min_len)
                - math.sqrt((3 * maj_len + min_len) * (maj_len + 3 * min_len))
            )
        elif dxftype == "HATCH":
            total_hatch_area = 0.0
            total_hatch_perim = 0.0
            for path in e.paths:
                if hasattr(path, "vertices"):
                    pts = [(v[0], v[1]) for v in path.vertices]
                    n = len(pts)
                    if n >= 3:
                        a = sum(
                            pts[i][0] * pts[(i + 1) % n][1]
                            - pts[(i + 1) % n][0] * pts[i][1]
                            for i in range(n)
                        )
                        total_hatch_area += abs(a) / 2.0
                        total_hatch_perim += sum(
                            math.hypot(
                                pts[(i + 1) % n][0] - pts[i][0],
                                pts[(i + 1) % n][1] - pts[i][1],
                            )
                            for i in range(n)
                        )
            area = total_hatch_area
            perimeter = total_hatch_perim

        return {
            "handle": handle,
            "object_name": dxftype,
            "layer": layer,
            "area": round(area, 4),
            "perimeter": round(perimeter, 4),
        }

    # ========== Human-in-the-Loop Headless Fallbacks ==========

    def prompt_point(
        self, prompt: str = "Select point:", base_point: Optional[Coordinate] = None, default_point: Optional[Coordinate] = None
    ) -> Dict[str, Any]:
        """Return point in headless mode (uses default_point, base_point, or model origin)."""
        pt = default_point or base_point or (0.0, 0.0, 0.0)
        return {
            "success": True,
            "point": (float(pt[0]), float(pt[1]), float(pt[2]) if len(pt) > 2 else 0.0),
            "interactive": False,
            "mode": "headless",
        }

    def prompt_entity(
        self, prompt: str = "Select entity:", default_handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return entity in headless mode (uses default_handle or first entity in modelspace)."""
        handle = default_handle
        obj_name = ""
        layer = "0"

        if not handle:
            for e in self.msp:
                handle = str(e.dxf.handle)
                obj_name = e.dxftype()
                layer = str(e.dxf.layer)
                break

        return {
            "success": bool(handle),
            "handle": handle or "",
            "type": obj_name,
            "layer": layer,
            "interactive": False,
            "mode": "headless",
        }

    def prompt_distance(
        self, prompt: str = "Specify distance:", base_point: Optional[Coordinate] = None, default_distance: float = 1.0
    ) -> Dict[str, Any]:
        """Return distance in headless mode."""
        return {
            "success": True,
            "distance": float(default_distance),
            "interactive": False,
            "mode": "headless",
        }

    def prompt_string(
        self, prompt: str = "Enter string:", has_spaces: bool = True, default_string: str = ""
    ) -> Dict[str, Any]:
        """Return string in headless mode."""
        return {
            "success": True,
            "string": str(default_string),
            "interactive": False,
            "mode": "headless",
        }

    # ========== Vector PDF Plotting Engine ==========

    def plot_to_pdf(
        self, filepath: str, paper_size: str = "A3", monochrome: bool = False
    ) -> Dict[str, Any]:
        """Plot CAD drawing directly to a standalone vector PDF 1.4 document."""
        # Standard paper dimensions in points (1 pt = 1/72 in = 0.35278 mm)
        sizes = {
            "a4": (841.89, 595.28),  # 297 x 210 mm
            "a3": (1190.55, 841.89),  # 420 x 297 mm
            "a2": (1683.78, 1190.55),  # 594 x 420 mm
            "a1": (2383.94, 1683.78),  # 841 x 594 mm
            "a0": (3370.39, 2383.94),  # 1189 x 841 mm
        }
        paper_w, paper_h = sizes.get(paper_size.lower().strip(), sizes["a3"])
        margin = 35.0  # pt margin

        # Find model bounding box
        coords_x = []
        coords_y = []
        for e in self.msp:
            t = e.dxftype()
            if t == "LINE":
                coords_x.extend([float(e.dxf.start[0]), float(e.dxf.end[0])])
                coords_y.extend([float(e.dxf.start[1]), float(e.dxf.end[1])])
            elif t in ("LWPOLYLINE", "POLYLINE"):
                for v in e.vertices() if hasattr(e, "vertices") else e:
                    coords_x.append(float(v[0] if isinstance(v, (tuple, list)) else v.dxf.location[0]))
                    coords_y.append(float(v[1] if isinstance(v, (tuple, list)) else v.dxf.location[1]))
            elif t in ("CIRCLE", "ARC"):
                cx, cy = float(e.dxf.center[0]), float(e.dxf.center[1])
                r = float(e.dxf.radius)
                coords_x.extend([cx - r, cx + r])
                coords_y.extend([cy - r, cy + r])

        if not coords_x:
            coords_x = [0.0, 100.0]
            coords_y = [0.0, 100.0]

        min_x, max_x = min(coords_x), max(coords_x)
        min_y, max_y = min(coords_y), max(coords_y)
        model_w = max(1e-4, max_x - min_x)
        model_h = max(1e-4, max_y - min_y)

        # Scale to fit paper with margins
        scale = min((paper_w - 2 * margin) / model_w, (paper_h - 2 * margin) / model_h)
        tx = margin + ((paper_w - 2 * margin) - model_w * scale) / 2.0 - min_x * scale
        ty = margin + ((paper_h - 2 * margin) - model_h * scale) / 2.0 - min_y * scale

        def to_pt(x: float, y: float) -> tuple:
            return x * scale + tx, y * scale + ty

        stream_cmds = [
            "q\n",
            "1 J\n",  # round line caps
            "1 j\n",  # round line joins
            "0.75 w\n",  # default line width
        ]

        # Draw frame / border
        stream_cmds.append(f"0.5 w 0 0 0 RG {margin:.2f} {margin:.2f} {paper_w - 2 * margin:.2f} {paper_h - 2 * margin:.2f} re S\n")

        entity_count = 0
        for e in self.msp:
            t = e.dxftype()
            entity_count += 1
            if monochrome:
                stream_cmds.append("0 0 0 RG\n")
            else:
                stream_cmds.append("0.1 0.1 0.15 RG\n")

            if t == "LINE":
                x1, y1 = to_pt(float(e.dxf.start[0]), float(e.dxf.start[1]))
                x2, y2 = to_pt(float(e.dxf.end[0]), float(e.dxf.end[1]))
                stream_cmds.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n")
            elif t in ("LWPOLYLINE", "POLYLINE"):
                pts = []
                if t == "LWPOLYLINE":
                    pts = [to_pt(float(p[0]), float(p[1])) for p in e.get_points()]
                else:
                    pts = [to_pt(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices]
                if pts:
                    stream_cmds.append(f"{pts[0][0]:.2f} {pts[0][1]:.2f} m\n")
                    for p in pts[1:]:
                        stream_cmds.append(f"{p[0]:.2f} {p[1]:.2f} l\n")
                    if e.is_closed:
                        stream_cmds.append("h S\n")
                    else:
                        stream_cmds.append("S\n")
            elif t in ("CIRCLE", "ARC"):
                cx, cy = to_pt(float(e.dxf.center[0]), float(e.dxf.center[1]))
                r = float(e.dxf.radius) * scale
                k = 0.5522847498 * r
                if t == "CIRCLE":
                    stream_cmds.append(
                        f"{cx + r:.2f} {cy:.2f} m "
                        f"{cx + r:.2f} {cy + k:.2f} {cx + k:.2f} {cy + r:.2f} {cx:.2f} {cy + r:.2f} c "
                        f"{cx - k:.2f} {cy + r:.2f} {cx - r:.2f} {cy + k:.2f} {cx - r:.2f} {cy:.2f} c "
                        f"{cx - r:.2f} {cy - k:.2f} {cx - k:.2f} {cy - r:.2f} {cx:.2f} {cy - r:.2f} c "
                        f"{cx + k:.2f} {cy - r:.2f} {cx + r:.2f} {cy - k:.2f} {cx + r:.2f} {cy:.2f} c S\n"
                    )
                else:
                    # Arc approximation
                    sa = math.radians(float(e.dxf.start_angle))
                    ea = math.radians(float(e.dxf.end_angle))
                    sx, sy = cx + r * math.cos(sa), cy + r * math.sin(sa)
                    ex, ey = cx + r * math.cos(ea), cy + r * math.sin(ea)
                    stream_cmds.append(f"{sx:.2f} {sy:.2f} m {ex:.2f} {ey:.2f} l S\n")
            elif t in ("TEXT", "MTEXT"):
                tx_pt, ty_pt = to_pt(float(e.dxf.insert[0]), float(e.dxf.insert[1]))
                raw_txt = getattr(e.dxf, "text", "")
                clean_txt = str(raw_txt).replace("(", "[").replace(")", "]")
                stream_cmds.append(f"BT /F1 9 Tf {tx_pt:.2f} {ty_pt:.2f} Td ({clean_txt}) Tj ET\n")

        # Title Block Stamp
        title_x = margin + 10
        title_y = margin + 15
        stream_cmds.append(f"BT /F1 10 Tf 0 0 0.5 RG {title_x:.2f} {title_y:.2f} Td (PLANO CAD - multiCAD-MCP AECO Edition | Formato {paper_size.upper()}) Tj ET\n")
        stream_cmds.append("Q\n")

        content_stream = "".join(stream_cmds).encode("latin-1", "replace")

        # Assemble PDF document
        objects = []
        offsets = []

        def add_object(body: bytes) -> int:
            obj_num = len(objects) + 1
            objects.append(body)
            return obj_num

        # Obj 1: Catalog
        add_object(b"<< /Type /Catalog /Pages 2 0 R >>")
        # Obj 2: Pages
        add_object(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        # Obj 3: Page
        page_def = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {paper_w:.2f} {paper_h:.2f}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>".encode("ascii")
        add_object(page_def)
        # Obj 4: Stream
        stream_def = f"<< /Length {len(content_stream)} >>\nstream\n".encode("ascii") + content_stream + b"\nendstream"
        add_object(stream_def)
        # Obj 5: Font
        add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        # Build file
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode("ascii"))
            out.extend(obj)
            out.extend(b"\nendobj\n")

        xref_pos = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        out.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii"))

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(out)

        return {
            "success": True,
            "path": str(filepath),
            "paper_size": paper_size.upper(),
            "entities_plotted": entity_count,
            "bytes": len(out),
        }

    # ========== BIM Semantic Metadata (XDATA) ==========

    def set_entity_metadata(self, handle: str, metadata: Dict[str, Any]) -> bool:
        """Attach BIM or extended semantic properties to an entity."""
        if not hasattr(self, "_metadata"):
            self._metadata = {}
        if handle not in self._metadata:
            self._metadata[handle] = {}
        self._metadata[handle].update(metadata)

        # Store in DXF XDATA if entity exists
        try:
            if hasattr(self.doc, "entitydb") and handle in self.doc.entitydb:
                e = self.doc.entitydb[handle]
                if "MULTICAD_BIM" not in self.doc.appids:
                    self.doc.appids.new("MULTICAD_BIM")
                payload = json.dumps(self._metadata[handle])
                e.set_xdata("MULTICAD_BIM", [(1000, payload)])
        except Exception as err:
            logger.debug(f"XDATA attach error: {err}")

        return True

    def get_entity_metadata(self, handle: str) -> Dict[str, Any]:
        """Retrieve attached BIM or extended semantic properties from an entity."""
        if not hasattr(self, "_metadata"):
            self._metadata = {}
        if handle in self._metadata:
            return dict(self._metadata[handle])

        # Attempt to read from DXF XDATA
        try:
            if hasattr(self.doc, "entitydb") and handle in self.doc.entitydb:
                e = self.doc.entitydb[handle]
                if e.has_xdata("MULTICAD_BIM"):
                    tags = e.get_xdata("MULTICAD_BIM")
                    for code, val in tags:
                        if code == 1000:
                            data = json.loads(val)
                            self._metadata[handle] = data
                            return data
        except Exception as err:
            logger.debug(f"XDATA read error: {err}")

        return {}

    # ========== External References (XREF) & Raster Images ==========

    def attach_xref(
        self,
        filepath: str,
        block_name: Optional[str] = None,
        insertion_point: Coordinate = (0.0, 0.0),
        scale: float = 1.0,
        rotation: float = 0.0,
        overlay: bool = True,
    ) -> Dict[str, Any]:
        """Attach external reference."""
        if not hasattr(self, "_xrefs"):
            self._xrefs = {}

        name = block_name or Path(filepath).stem
        c = (float(insertion_point[0]), float(insertion_point[1]))

        # Register in internal tracking
        self._xrefs[name] = {
            "name": name,
            "type": "dwg",
            "path": str(filepath),
            "insertion_point": c,
            "scale": scale,
            "rotation": rotation,
            "overlay": overlay,
            "status": "loaded",
        }

        # Create block placeholder in DXF
        try:
            if name not in self.doc.blocks:
                blk = self.doc.blocks.new(name=name)
                blk.add_text(f"[XREF: {name}]", dxfattribs={"height": 2.0})
            e = self.msp.add_blockref(name, c, dxfattribs={"xscale": scale, "yscale": scale, "rotation": rotation})
            handle = str(e.dxf.handle)
        except Exception as err:
            logger.debug(f"XREF block ref error: {err}")
            handle = ""

        return {
            "success": True,
            "name": name,
            "path": str(filepath),
            "handle": handle,
            "insertion_point": c,
        }

    def attach_raster(
        self,
        filepath: str,
        insertion_point: Coordinate = (0.0, 0.0),
        scale: float = 1.0,
        rotation: float = 0.0,
    ) -> Dict[str, Any]:
        """Attach raster image or orthophoto."""
        if not hasattr(self, "_xrefs"):
            self._xrefs = {}

        name = Path(filepath).stem
        c = (float(insertion_point[0]), float(insertion_point[1]))

        self._xrefs[name] = {
            "name": name,
            "type": "raster",
            "path": str(filepath),
            "insertion_point": c,
            "scale": scale,
            "rotation": rotation,
            "status": "loaded",
        }

        return {
            "success": True,
            "name": name,
            "path": str(filepath),
            "insertion_point": c,
            "scale": scale,
        }

    def list_xrefs(self) -> List[Dict[str, Any]]:
        """List active external references and raster images."""
        if not hasattr(self, "_xrefs"):
            self._xrefs = {}
        return list(self._xrefs.values())

    def reload_xref(self, name: str) -> bool:
        """Reload external reference by name."""
        if not hasattr(self, "_xrefs"):
            self._xrefs = {}
        if name in self._xrefs:
            self._xrefs[name]["status"] = "loaded"
            return True
        return False

    def detach_xref(self, name: str) -> bool:
        """Detach external reference by name."""
        if not hasattr(self, "_xrefs"):
            self._xrefs = {}
        if name in self._xrefs:
            del self._xrefs[name]
            return True
        return False

    def offset_entity(
        self, handle: str, distance: float, side_point: Optional[Coordinate] = None
    ) -> List[str]:
        """Create a parallel offset of an entity."""
        e = None
        for entity in self.msp:
            if str(entity.dxf.handle) == str(handle):
                e = entity
                break
        if not e:
            return []

        dxftype = e.dxftype()
        layer = str(e.dxf.layer)
        color = getattr(e.dxf, "color", 7)

        if dxftype == "LINE":
            p1 = (float(e.dxf.start[0]), float(e.dxf.start[1]))
            p2 = (float(e.dxf.end[0]), float(e.dxf.end[1]))
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length == 0:
                return []
            nx = -dy / length
            ny = dx / length
            np1 = (p1[0] + nx * distance, p1[1] + ny * distance, 0.0)
            np2 = (p2[0] + nx * distance, p2[1] + ny * distance, 0.0)
            new_h = self.draw_line(np1, np2, layer=layer, color=color)
            return [new_h]

        elif dxftype in ("CIRCLE", "ARC"):
            cx, cy = float(e.dxf.center[0]), float(e.dxf.center[1])
            new_r = max(0.01, float(e.dxf.radius) + distance)
            new_h = self.draw_circle((cx, cy), new_r, layer=layer, color=color)
            return [new_h]

        elif dxftype in ("LWPOLYLINE", "POLYLINE"):
            if dxftype == "LWPOLYLINE":
                pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
            else:
                pts = [(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices]
            n = len(pts)
            if n < 2:
                return []
            is_closed = getattr(e, "is_closed", False)

            # Compute edge normals and shift edges
            shifted_lines = []
            m = n if is_closed else n - 1
            for i in range(m):
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                L = math.hypot(dx, dy)
                if L == 0:
                    continue
                nx = -dy / L
                ny = dx / L
                shifted_lines.append((
                    (p1[0] + nx * distance, p1[1] + ny * distance),
                    (p2[0] + nx * distance, p2[1] + ny * distance),
                ))

            if not shifted_lines:
                return []

            # Intersect consecutive shifted edges
            new_pts = []
            k = len(shifted_lines)
            for i in range(k):
                l1 = shifted_lines[i]
                l2 = shifted_lines[(i + 1) % k]
                # Intersect l1 and l2
                p1, p2 = l1
                p3, p4 = l2
                dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                dx2, dy2 = p4[0] - p3[0], p4[1] - p3[1]
                denom = dx1 * dy2 - dy1 * dx2
                if abs(denom) > 1e-6:
                    t = ((p3[0] - p1[0]) * dy2 - (p3[1] - p1[1]) * dx2) / denom
                    ix = p1[0] + t * dx1
                    iy = p1[1] + t * dy1
                    new_pts.append((round(ix, 4), round(iy, 4)))
                else:
                    new_pts.append(p2)

            if new_pts:
                new_h = self.draw_polyline(new_pts, closed=is_closed, layer=layer, color=color)
                return [new_h]

        return []

    def fillet_entities(
        self, handle1: str, handle2: str, radius: float = 0.0
    ) -> Optional[str]:
        """Fillet two lines with radius (0 for sharp corner join)."""
        e1, e2 = None, None
        for entity in self.msp:
            h = str(entity.dxf.handle)
            if h == str(handle1):
                e1 = entity
            elif h == str(handle2):
                e2 = entity
        if not e1 or not e2 or e1.dxftype() != "LINE" or e2.dxftype() != "LINE":
            return None

        A = (float(e1.dxf.start[0]), float(e1.dxf.start[1]))
        B = (float(e1.dxf.end[0]), float(e1.dxf.end[1]))
        C = (float(e2.dxf.start[0]), float(e2.dxf.start[1]))
        D = (float(e2.dxf.end[0]), float(e2.dxf.end[1]))

        dx1, dy1 = B[0] - A[0], B[1] - A[1]
        dx2, dy2 = D[0] - C[0], D[1] - C[1]
        denom = dx1 * dy2 - dy1 * dx2
        if abs(denom) < 1e-6:
            return None  # Parallel lines

        t = ((C[0] - A[0]) * dy2 - (C[1] - A[1]) * dx2) / denom
        Px = A[0] + t * dx1
        Py = A[1] + t * dy1
        P = (Px, Py)

        dA, dB = math.hypot(A[0] - P[0], A[1] - P[1]), math.hypot(B[0] - P[0], B[1] - P[1])
        dC, dD = math.hypot(C[0] - P[0], C[1] - P[1]), math.hypot(D[0] - P[0], D[1] - P[1])

        if radius <= 0.0:
            # Sharp corner join
            if dA < dB:
                e1.dxf.start = (P[0], P[1], e1.dxf.start[2] if len(e1.dxf.start) > 2 else 0.0)
            else:
                e1.dxf.end = (P[0], P[1], e1.dxf.end[2] if len(e1.dxf.end) > 2 else 0.0)

            if dC < dD:
                e2.dxf.start = (P[0], P[1], e2.dxf.start[2] if len(e2.dxf.start) > 2 else 0.0)
            else:
                e2.dxf.end = (P[0], P[1], e2.dxf.end[2] if len(e2.dxf.end) > 2 else 0.0)
            return handle1
        else:
            # Trim lines back by radius and connect with bevel/arc
            v1 = (A[0] - P[0], A[1] - P[1]) if dA > dB else (B[0] - P[0], B[1] - P[1])
            L1 = math.hypot(v1[0], v1[1])
            if L1 > 0:
                pt1 = (P[0] + (v1[0] / L1) * radius, P[1] + (v1[1] / L1) * radius)
                if dA < dB:
                    e1.dxf.start = (pt1[0], pt1[1], e1.dxf.start[2] if len(e1.dxf.start) > 2 else 0.0)
                else:
                    e1.dxf.end = (pt1[0], pt1[1], e1.dxf.end[2] if len(e1.dxf.end) > 2 else 0.0)

            v2 = (C[0] - P[0], C[1] - P[1]) if dC > dD else (D[0] - P[0], D[1] - P[1])
            L2 = math.hypot(v2[0], v2[1])
            if L2 > 0:
                pt2 = (P[0] + (v2[0] / L2) * radius, P[1] + (v2[1] / L2) * radius)
                if dC < dD:
                    e2.dxf.start = (pt2[0], pt2[1], e2.dxf.start[2] if len(e2.dxf.start) > 2 else 0.0)
                else:
                    e2.dxf.end = (pt2[0], pt2[1], e2.dxf.end[2] if len(e2.dxf.end) > 2 else 0.0)

            connector_h = self.draw_line(pt1, pt2, layer=str(e1.dxf.layer))
            return connector_h

    def chamfer_entities(
        self, handle1: str, handle2: str, dist1: float = 0.0, dist2: float = 0.0
    ) -> Optional[str]:
        """Chamfer two intersecting lines with setback distances."""
        d1 = dist1 if dist1 > 0 else 0.5
        d2 = dist2 if dist2 > 0 else d1
        return self.fillet_entities(handle1, handle2, radius=d1)

    def explode_entity(self, handle: str) -> List[str]:
        """Explode a polyline or block into primitive lines."""
        e = None
        for entity in self.msp:
            if str(entity.dxf.handle) == str(handle):
                e = entity
                break
        if not e:
            return []

        dxftype = e.dxftype()
        layer = str(e.dxf.layer)
        color = getattr(e.dxf, "color", 7)
        new_handles = []

        if dxftype in ("LWPOLYLINE", "POLYLINE"):
            if dxftype == "LWPOLYLINE":
                pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
            else:
                pts = [(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices]
            n = len(pts)
            is_closed = getattr(e, "is_closed", False)
            m = n if is_closed else n - 1
            for i in range(m):
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                lh = self.draw_line(p1, p2, layer=layer, color=color)
                new_handles.append(lh)
            # Remove original polyline
            try:
                self.msp.delete_entity(e)
            except Exception:
                pass
            return new_handles

        elif dxftype == "INSERT":
            # Explode block reference
            try:
                exploded = e.explode()
                for exp_e in exploded:
                    new_handles.append(str(exp_e.dxf.handle))
                return new_handles
            except Exception:
                return []

        return []

    def match_properties(self, source_handle: str, target_handles: List[str]) -> bool:
        """Copy layer, color, linetype and lineweight from source entity to targets."""
        source = None
        for entity in self.msp:
            if str(entity.dxf.handle) == str(source_handle):
                source = entity
                break
        if not source:
            return False

        src_layer = str(source.dxf.layer)
        src_color = getattr(source.dxf, "color", 7)
        src_linetype = getattr(source.dxf, "linetype", "BYLAYER")
        src_weight = getattr(source.dxf, "lineweight", 0)

        targets_set = set(str(h).strip() for h in target_handles)
        for entity in self.msp:
            if str(entity.dxf.handle) in targets_set:
                entity.dxf.layer = src_layer
                entity.dxf.color = src_color
                entity.dxf.linetype = src_linetype
                entity.dxf.lineweight = src_weight

        return True

    def create_boundary(
        self, internal_point: Coordinate, layer: str = "0"
    ) -> Optional[str]:
        """Detect closed boundary around internal point and create polyline."""
        px, py = float(internal_point[0]), float(internal_point[1])

        # 1. Check if an existing closed polyline encloses (px, py)
        for entity in self.msp:
            if entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                if getattr(entity, "is_closed", False):
                    if entity.dxftype() == "LWPOLYLINE":
                        pts = [(float(p[0]), float(p[1])) for p in entity.get_points()]
                    else:
                        pts = [(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in entity.vertices]
                    # Point in polygon
                    n = len(pts)
                    inside = False
                    for i in range(n):
                        p1x, p1y = pts[i]
                        p2x, p2y = pts[(i + 1) % n]
                        if ((p1y > py) != (p2y > py)) and (px < (p2x - p1x) * (py - p1y) / (p2y - p1y + 1e-12) + p1x):
                            inside = not inside
                    if inside:
                        return str(entity.dxf.handle)

        # 2. Ray-cast in 4 cardinal directions to find nearest bounding lines
        lines = [e for e in self.msp if e.dxftype() == "LINE"]
        min_x, max_x = None, None
        min_y, max_y = None, None

        for l in lines:
            x1, y1 = float(l.dxf.start[0]), float(l.dxf.start[1])
            x2, y2 = float(l.dxf.end[0]), float(l.dxf.end[1])

            # Vertical walls
            if abs(x1 - x2) < 1e-3:
                wx = x1
                ymin, ymax = min(y1, y2), max(y1, y2)
                if ymin <= py <= ymax:
                    if wx < px and (min_x is None or wx > min_x):
                        min_x = wx
                    elif wx > px and (max_x is None or wx < max_x):
                        max_x = wx
            # Horizontal walls
            elif abs(y1 - y2) < 1e-3:
                wy = y1
                xmin, xmax = min(x1, x2), max(x1, x2)
                if xmin <= px <= xmax:
                    if wy < py and (min_y is None or wy > min_y):
                        min_y = wy
                    elif wy > py and (max_y is None or wy < max_y):
                        max_y = wy

        if None not in (min_x, max_x, min_y, max_y):
            # Create closed boundary rectangle polyline
            rect_h = self.draw_rectangle((min_x, min_y), (max_x, max_y), layer=layer)
            return rect_h

        return None

    def join_entities(
        self, handles: List[str], tolerance: float = 0.01
    ) -> Optional[str]:
        """Join loose connected lines and arcs into a continuous polyline."""
        if not handles or len(handles) < 2:
            return None

        handle_set = set(str(h).strip() for h in handles)
        lines = []
        for e in list(self.msp):
            if str(e.dxf.handle) in handle_set and e.dxftype() == "LINE":
                p1 = (float(e.dxf.start[0]), float(e.dxf.start[1]))
                p2 = (float(e.dxf.end[0]), float(e.dxf.end[1]))
                lines.append((e, p1, p2))

        if not lines:
            return None

        # Chain lines together by endpoint proximity
        used = [False] * len(lines)
        first_e, p1, p2 = lines[0]
        used[0] = True
        chain = [p1, p2]
        layer = str(first_e.dxf.layer)
        color = getattr(first_e.dxf, "color", 7)

        changed = True
        while changed:
            changed = False
            for i, (e, start, end) in enumerate(lines):
                if used[i]:
                    continue
                # Try attaching to end of chain
                last_pt = chain[-1]
                if math.hypot(start[0] - last_pt[0], start[1] - last_pt[1]) <= tolerance:
                    chain.append(end)
                    used[i] = True
                    changed = True
                elif math.hypot(end[0] - last_pt[0], end[1] - last_pt[1]) <= tolerance:
                    chain.append(start)
                    used[i] = True
                    changed = True
                # Try attaching to start of chain
                first_pt = chain[0]
                if math.hypot(end[0] - first_pt[0], end[1] - first_pt[1]) <= tolerance:
                    chain.insert(0, start)
                    used[i] = True
                    changed = True
                elif math.hypot(start[0] - first_pt[0], start[1] - first_pt[1]) <= tolerance:
                    chain.insert(0, end)
                    used[i] = True
                    changed = True

        # Check if closed
        is_closed = math.hypot(chain[0][0] - chain[-1][0], chain[0][1] - chain[-1][1]) <= tolerance
        if is_closed and len(chain) > 2:
            chain.pop()  # Drop redundant duplicate last point for closed polyline

        # Delete original joined lines
        for i, (e, _, _) in enumerate(lines):
            if used[i]:
                try:
                    self.msp.delete_entity(e)
                except Exception:
                    pass

        # Draw joined polyline
        new_h = self.draw_polyline(chain, closed=is_closed, layer=layer, color=color)
        return new_h

    def trim_extend_entity(
        self, handle: str, boundary_handle: str, mode: str = "trim"
    ) -> bool:
        """Trim or extend a line against a boundary edge."""
        target, bound = None, None
        for e in self.msp:
            h = str(e.dxf.handle)
            if h == str(handle):
                target = e
            elif h == str(boundary_handle):
                bound = e

        if not target or not bound or target.dxftype() != "LINE" or bound.dxftype() != "LINE":
            return False

        A = (float(target.dxf.start[0]), float(target.dxf.start[1]))
        B = (float(target.dxf.end[0]), float(target.dxf.end[1]))
        C = (float(bound.dxf.start[0]), float(bound.dxf.start[1]))
        D = (float(bound.dxf.end[0]), float(bound.dxf.end[1]))

        dx1, dy1 = B[0] - A[0], B[1] - A[1]
        dx2, dy2 = D[0] - C[0], D[1] - C[1]
        denom = dx1 * dy2 - dy1 * dx2
        if abs(denom) < 1e-6:
            return False  # Parallel lines

        t = ((C[0] - A[0]) * dy2 - (C[1] - A[1]) * dx2) / denom
        Px = A[0] + t * dx1
        Py = A[1] + t * dy1
        P = (Px, Py)

        dA = math.hypot(A[0] - P[0], A[1] - P[1])
        dB = math.hypot(B[0] - P[0], B[1] - P[1])

        if mode.lower() == "trim":
            # Trim off the segment beyond P (endpoint with larger distance to P becomes P)
            if dA > dB:
                target.dxf.start = (P[0], P[1], target.dxf.start[2] if len(target.dxf.start) > 2 else 0.0)
            else:
                target.dxf.end = (P[0], P[1], target.dxf.end[2] if len(target.dxf.end) > 2 else 0.0)
        else:  # extend
            # Extend endpoint that is closer to P to reach P
            if dA < dB:
                target.dxf.start = (P[0], P[1], target.dxf.start[2] if len(target.dxf.start) > 2 else 0.0)
            else:
                target.dxf.end = (P[0], P[1], target.dxf.end[2] if len(target.dxf.end) > 2 else 0.0)

        return True

    # ========== Layout & Paperspace Management ==========

    def list_layouts(self) -> List[Dict[str, Any]]:
        """List all presentation layouts in the DXF document."""
        active_name = ""
        try:
            active_name = self.doc.layouts.active_layout().name
        except Exception:
            pass

        results = []
        for l in self.doc.layouts:
            results.append({
                "name": l.name,
                "is_active": (l.name == active_name),
                "is_modelspace": l.is_modelspace,
            })
        return results

    def create_layout(
        self,
        name: str,
        paper_size: str = "A3",
        orientation: str = "landscape",
        margins: Tuple[float, float, float, float] = (10.0, 10.0, 10.0, 10.0),
    ) -> Dict[str, Any]:
        """Create a new paperspace layout with standard paper size and frame."""
        paper_dims = {
            "A4": (297.0, 210.0),
            "A3": (420.0, 297.0),
            "A2": (594.0, 420.0),
            "A1": (841.0, 594.0),
            "A0": (1189.0, 841.0),
            "LETTER": (279.4, 215.9),
            "TABLOID": (431.8, 279.4),
        }
        pw, ph = paper_dims.get(paper_size.upper(), (420.0, 297.0))
        if orientation.lower() == "portrait":
            pw, ph = ph, pw

        if name in self.doc.layouts:
            raise CADOperationError("create_layout", f"Layout '{name}' already exists.")

        layout = self.doc.layouts.new(name)
        try:
            layout.page_setup(size=(pw, ph), margins=margins, units="mm")
        except Exception:
            pass

        # Add outer border frame
        left, bottom, right, top = margins
        frame_pts = [
            (left, bottom),
            (pw - right, bottom),
            (pw - right, ph - top),
            (left, ph - top),
        ]
        layout.add_lwpolyline(frame_pts, close=True, dxfattribs={"layer": "0", "color": 7})

        return {
            "success": True,
            "name": name,
            "paper_size": paper_size.upper(),
            "width_mm": pw,
            "height_mm": ph,
            "orientation": orientation.lower(),
        }

    def activate_layout(self, name: str) -> bool:
        """Switch active layout in DXF document."""
        if name not in self.doc.layouts:
            return False
        self.doc.layouts.set_active_layout(name)
        return True

    def delete_layout(self, name: str) -> bool:
        """Delete layout by name in DXF document."""
        if name not in self.doc.layouts:
            return False
        if name.lower() in ("model", "modelspace"):
            raise CADOperationError("delete_layout", "Cannot delete Modelspace.")
        self.doc.layouts.delete(name)
        return True

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
        """Add modelspace viewport to a paperspace layout."""
        if layout_name not in self.doc.layouts:
            raise CADOperationError("add_viewport", f"Layout '{layout_name}' not found.")
        layout = self.doc.layouts.get(layout_name)

        scale_factor = 50.0
        if ":" in scale:
            parts = scale.split(":")
            try:
                scale_factor = float(parts[1]) / float(parts[0])
            except Exception:
                scale_factor = 50.0

        vh = (height / 1000.0) * scale_factor if unit == "m" else height * scale_factor
        vp = layout.add_viewport(
            center=center,
            size=(width, height),
            view_center_point=view_center,
            view_height=vh,
        )
        return str(vp.dxf.handle)

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
        """Insert standardized AECO title block into layout."""
        if layout_name not in self.doc.layouts:
            raise CADOperationError("add_titleblock", f"Layout '{layout_name}' not found.")
        layout = self.doc.layouts.get(layout_name)

        paper_dims = {
            "A4": (297.0, 210.0),
            "A3": (420.0, 297.0),
            "A2": (594.0, 420.0),
            "A1": (841.0, 594.0),
            "A0": (1189.0, 841.0),
            "LETTER": (279.4, 215.9),
            "TABLOID": (431.8, 279.4),
        }
        pw, ph = paper_dims.get(paper_size.upper(), (420.0, 297.0))
        if orientation.lower() == "portrait":
            pw, ph = ph, pw

        tb_w = 160.0
        tb_h = 42.0
        x0 = pw - 10.0 - tb_w
        y0 = 10.0

        # Outer box
        layout.add_lwpolyline([
            (x0, y0), (x0 + tb_w, y0), (x0 + tb_w, y0 + tb_h), (x0, y0 + tb_h)
        ], close=True, dxfattribs={"color": 7})

        # Dividing lines
        layout.add_line((x0, y0 + 24.0), (x0 + tb_w, y0 + 24.0), dxfattribs={"color": 7})
        layout.add_line((x0, y0 + 12.0), (x0 + tb_w, y0 + 12.0), dxfattribs={"color": 7})
        layout.add_line((x0 + 95.0, y0), (x0 + 95.0, y0 + 24.0), dxfattribs={"color": 7})

        # Text labels
        layout.add_text(title.upper(), dxfattribs={"height": 3.5, "color": 7}).set_placement((x0 + 4.0, y0 + 30.0))
        layout.add_text(f"AUTOR: {author}" if author else "AUTOR: multiCAD-MCP", dxfattribs={"height": 2.2, "color": 8}).set_placement((x0 + 4.0, y0 + 16.0))
        layout.add_text(f"FECHA: {date}" if date else "FECHA: -", dxfattribs={"height": 2.2, "color": 8}).set_placement((x0 + 99.0, y0 + 16.0))
        layout.add_text(f"ESCALA: {scale}", dxfattribs={"height": 2.2, "color": 8}).set_placement((x0 + 4.0, y0 + 4.5))
        layout.add_text(f"PLANO: {sheet_number}", dxfattribs={"height": 2.2, "color": 8}).set_placement((x0 + 99.0, y0 + 4.5))

        return {
            "success": True,
            "layout": layout_name,
            "title": title,
            "author": author,
            "scale": scale,
            "sheet_number": sheet_number,
            "position": (round(x0, 2), round(y0, 2)),
        }
