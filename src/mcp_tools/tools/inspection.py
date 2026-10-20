"""
Spatial Intelligence & Interactive Drawing Viewer tools.

Features:
- inspect_drawing: Spatial intelligence, Point-in-Polygon query ("what is here?"),
  building bounding box, room distribution summary, and ASCII minimap.
- show_drawing_viewer: Generates and opens a standalone HTML5 interactive CAD viewer
  with pan/zoom, layer toggling, and interactive room inspector.
"""

import json
import math
import os
import webbrowser
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate
from core.config import get_config

logger = logging.getLogger(__name__)


def _point_in_polygon(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
    """Raycasting algorithm to test if (x, y) is inside a closed 2D polygon."""
    n = len(poly)
    if n < 3:
        return False
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _line_segment_intersection(
    p1: Tuple[float, float], p2: Tuple[float, float],
    p3: Tuple[float, float], p4: Tuple[float, float],
) -> Optional[Tuple[float, float]]:
    """Calculate intersection point of segment (p1-p2) with segment (p3-p4) if any."""
    dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
    dx2, dy2 = p4[0] - p3[0], p4[1] - p3[1]
    denom = dx1 * dy2 - dy1 * dx2
    if abs(denom) < 1e-9:
        return None  # Parallel or collinear

    t1 = ((p3[0] - p1[0]) * dy2 - (p3[1] - p1[1]) * dx2) / denom
    t2 = ((p3[0] - p1[0]) * dy1 - (p3[1] - p1[1]) * dx1) / denom

    if -1e-6 <= t1 <= 1.0 + 1e-6 and -1e-6 <= t2 <= 1.0 + 1e-6:
        ix = p1[0] + t1 * dx1
        iy = p1[1] + t1 * dy1
        return (round(ix, 4), round(iy, 4))
    return None


def _get_drawing_entities_data(adapter) -> Dict[str, Any]:

    """Extract entities, closed spaces, and layers from active drawing."""
    entities = []
    spaces = []
    layers_found = set()

    coords_x = []
    coords_y = []

    if hasattr(adapter, "msp"):
        for e in adapter.msp:
            dxftype = e.dxftype()
            handle = str(e.dxf.handle)
            layer = str(e.dxf.layer)
            layers_found.add(layer)

            # Metadata if any
            metadata = adapter.get_entity_metadata(handle) if hasattr(adapter, "get_entity_metadata") else {}

            if dxftype == "LINE":
                p1 = (float(e.dxf.start[0]), float(e.dxf.start[1]))
                p2 = (float(e.dxf.end[0]), float(e.dxf.end[1]))
                coords_x.extend([p1[0], p2[0]])
                coords_y.extend([p1[1], p2[1]])
                entities.append({
                    "handle": handle,
                    "type": "LINE",
                    "layer": layer,
                    "points": [p1, p2],
                    "metadata": metadata,
                })
            elif dxftype in ("LWPOLYLINE", "POLYLINE"):
                if dxftype == "LWPOLYLINE":
                    pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
                else:
                    pts = [(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices]
                for p in pts:
                    coords_x.append(p[0])
                    coords_y.append(p[1])
                is_closed = getattr(e, "is_closed", False)
                entities.append({
                    "handle": handle,
                    "type": dxftype,
                    "layer": layer,
                    "points": pts,
                    "closed": is_closed,
                    "metadata": metadata,
                })
                # If closed polyline, treat as space
                if is_closed and len(pts) >= 3 and hasattr(adapter, "get_entity_area"):
                    info = adapter.get_entity_area(handle)
                    area = float(info.get("area", 0.0))
                    perim = float(info.get("perimeter", 0.0))
                    if area > 0.5:
                        # Centroid
                        cx = sum(p[0] for p in pts) / len(pts)
                        cy = sum(p[1] for p in pts) / len(pts)
                        spaces.append({
                            "handle": handle,
                            "layer": layer,
                            "area": round(area, 2),
                            "perimeter": round(perim, 2),
                            "centroid": (round(cx, 2), round(cy, 2)),
                            "polygon": pts,
                            "metadata": metadata,
                        })
            elif dxftype in ("CIRCLE", "ARC"):
                cx, cy = float(e.dxf.center[0]), float(e.dxf.center[1])
                r = float(e.dxf.radius)
                coords_x.extend([cx - r, cx + r])
                coords_y.extend([cy - r, cy + r])
                entities.append({
                    "handle": handle,
                    "type": dxftype,
                    "layer": layer,
                    "center": (cx, cy),
                    "radius": r,
                    "metadata": metadata,
                })
            elif dxftype in ("TEXT", "MTEXT"):
                ins = (float(e.dxf.insert[0]), float(e.dxf.insert[1]))
                coords_x.append(ins[0])
                coords_y.append(ins[1])
                txt = getattr(e.dxf, "text", "")
                entities.append({
                    "handle": handle,
                    "type": dxftype,
                    "layer": layer,
                    "insert": ins,
                    "text": txt,
                    "metadata": metadata,
                })

    min_x = min(coords_x) if coords_x else 0.0
    max_x = max(coords_x) if coords_x else 10.0
    min_y = min(coords_y) if coords_y else 0.0
    max_y = max(coords_y) if coords_y else 10.0

    return {
        "entities": entities,
        "spaces": spaces,
        "layers": sorted(list(layers_found)),
        "bbox": {
            "min_x": round(min_x, 2),
            "min_y": round(min_y, 2),
            "max_x": round(max_x, 2),
            "max_y": round(max_y, 2),
            "width": round(max_x - min_x, 2),
            "length": round(max_y - min_y, 2),
            "area_bounding_m2": round((max_x - min_x) * (max_y - min_y), 2),
        },
    }


def _generate_ascii_minimap(spaces: List[Dict[str, Any]], bbox: Dict[str, Any]) -> str:
    """Generate an ASCII representation of the space layout for chat UI."""
    if not spaces:
        return "[ Plano sin recintos poligonales cerrados detectados ]"

    lines = []
    lines.append("┌" + "─" * 46 + "┐")
    lines.append(f"│ 📐 ESQUEMA DE DISTRIBUCIÓN CAD ({bbox['width']}m x {bbox['length']}m) │")
    lines.append("├" + "─" * 46 + "┤")

    for i, s in enumerate(spaces, 1):
        name = s.get("metadata", {}).get("nombre") or s.get("metadata", {}).get("tipo") or f"Recinto #{s['handle']}"
        layer = s["layer"]
        area = s["area"]
        cx, cy = s["centroid"]
        line_str = f"│ {i}. {name[:16]:<16} │ {area:>6.2f} m² │ ({cx:>5.1f}, {cy:>5.1f}) │"
        lines.append(line_str)

    lines.append("└" + "─" * 46 + "┘")
    return "\n".join(lines)


# ========== Tool Handlers ==========


def register_inspection_tools(mcp):
    """Register drawing inspection and interactive viewer tools with FastMCP."""

    @cad_tool(mcp, "inspect_drawing")
    def inspect_drawing(
        mode: str = "summary",
        point: Optional[str] = None,
        handle1: Optional[str] = None,
        handle2: Optional[str] = None,
        snap_types: str = "endpoint,midpoint,center",
        tolerance: float = 1.5,
        layer: Optional[str] = None,
    ) -> str:
        """
        Spatial Intelligence & Snapping: inspect drawing dimensions, intersections, and snap points.

        Modes:
        - "summary" (default): Global bounding box, room schedule, layers count, and ASCII minimap.
        - "point": Raycasting query ("what is at coordinates X,Y?"). Requires `point="x,y"`.
        - "intersections": Detect geometric crossing points between lines/entities. Optional: `handle1`, `handle2`, `layer`.
        - "snap": Object snap assistant. Finds closest endpoint, midpoint, or center to `point`. Requires `point="x,y"`.

        Examples:
            inspect_drawing(mode="summary")
            inspect_drawing(mode="point", point="4.5, 3.2")
            inspect_drawing(mode="intersections")
            inspect_drawing(mode="snap", point="10.1, 0.05", snap_types="endpoint,midpoint")
        """
        adapter = get_current_adapter()
        data = _get_drawing_entities_data(adapter)
        mode_lower = mode.lower().strip()

        if mode_lower in ("point", "location", "query"):
            if not point:
                return json.dumps({"success": False, "error": "Point mode requires 'point' parameter (e.g. '5.0, 3.2')"})
            pt = parse_coordinate(point)
            x, y = pt[0], pt[1]

            # Check which space contains the point
            matching_space = None
            for s in data["spaces"]:
                if _point_in_polygon(x, y, s["polygon"]):
                    matching_space = s
                    break

            if matching_space:
                return json.dumps({
                    "success": True,
                    "found": True,
                    "query_point": (x, y),
                    "space": {
                        "handle": matching_space["handle"],
                        "layer": matching_space["layer"],
                        "area_m2": matching_space["area"],
                        "perimeter_m": matching_space["perimeter"],
                        "centroid": matching_space["centroid"],
                        "metadata": matching_space["metadata"],
                    },
                    "description": (
                        f"Point ({x}, {y}) is INSIDE room '{matching_space['handle']}' "
                        f"(Layer: {matching_space['layer']}, Area: {matching_space['area']} m²)"
                    ),
                }, indent=2, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": True,
                    "found": False,
                    "query_point": (x, y),
                    "description": f"Point ({x}, {y}) is in open drawing space (outside defined closed rooms).",
                }, indent=2, ensure_ascii=False)

        elif mode_lower in ("intersections", "intersection", "cruces"):
            intersections = []
            target_entities = data["entities"]
            if layer:
                target_entities = [e for e in target_entities if e["layer"].lower() == layer.lower()]

            if handle1 and handle2:
                e1 = next((e for e in target_entities if e["handle"] == handle1), None)
                e2 = next((e for e in target_entities if e["handle"] == handle2), None)
                if e1 and e2 and e1.get("points") and e2.get("points"):
                    pts1, pts2 = e1["points"], e2["points"]
                    for i in range(len(pts1) - 1):
                        for j in range(len(pts2) - 1):
                            ix = _line_segment_intersection(pts1[i], pts1[i+1], pts2[j], pts2[j+1])
                            if ix:
                                intersections.append({"point": ix, "entity1": handle1, "entity2": handle2})
            else:
                line_entities = [e for e in target_entities if e.get("points") and len(e["points"]) >= 2]
                n_ent = len(line_entities)
                for i in range(n_ent):
                    for j in range(i + 1, n_ent):
                        e1, e2 = line_entities[i], line_entities[j]
                        pts1, pts2 = e1["points"], e2["points"]
                        for si in range(len(pts1) - 1):
                            for sj in range(len(pts2) - 1):
                                ix = _line_segment_intersection(pts1[si], pts1[si+1], pts2[sj], pts2[sj+1])
                                if ix:
                                    intersections.append({"point": ix, "entity1": e1["handle"], "entity2": e2["handle"]})

            return json.dumps({
                "success": True,
                "count": len(intersections),
                "intersections": intersections,
            }, indent=2, ensure_ascii=False)

        elif mode_lower in ("snap", "osnap", "probe"):
            if not point:
                return json.dumps({"success": False, "error": "Snap mode requires 'point' parameter (e.g. '5.0, 3.2')"})
            pt = parse_coordinate(point)
            px, py = pt[0], pt[1]

            allowed_types = set(s.strip().lower() for s in snap_types.split(","))
            candidates = []

            for e in data["entities"]:
                h = e["handle"]
                if e.get("points"):
                    pts = e["points"]
                    if "endpoint" in allowed_types:
                        for p in pts:
                            d = math.hypot(p[0] - px, p[1] - py)
                            if d <= tolerance:
                                candidates.append({"snap_type": "endpoint", "point": p, "distance": round(d, 4), "handle": h})
                    if "midpoint" in allowed_types:
                        for i in range(len(pts) - 1):
                            mx = (pts[i][0] + pts[i+1][0]) / 2.0
                            my = (pts[i][1] + pts[i+1][1]) / 2.0
                            d = math.hypot(mx - px, my - py)
                            if d <= tolerance:
                                candidates.append({"snap_type": "midpoint", "point": (round(mx, 4), round(my, 4)), "distance": round(d, 4), "handle": h})
                if "center" in allowed_types and e.get("center"):
                    c = e["center"]
                    d = math.hypot(c[0] - px, c[1] - py)
                    if d <= tolerance:
                        candidates.append({"snap_type": "center", "point": c, "distance": round(d, 4), "handle": h})

            if candidates:
                candidates.sort(key=lambda c: c["distance"])
                best = candidates[0]
                return json.dumps({
                    "success": True,
                    "snapped": True,
                    "best_snap": best,
                    "candidates_found": len(candidates),
                    "all_candidates": candidates[:5],
                }, indent=2, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": True,
                    "snapped": False,
                    "query_point": (px, py),
                    "tolerance": tolerance,
                    "message": f"No snap points found within tolerance {tolerance}",
                }, indent=2, ensure_ascii=False)


        # Summary mode
        total_usable_area = sum(s["area"] for s in data["spaces"])
        ascii_map = _generate_ascii_minimap(data["spaces"], data["bbox"])

        result = {
            "success": True,
            "bounding_box": data["bbox"],
            "total_entities": len(data["entities"]),
            "layers_count": len(data["layers"]),
            "layers": data["layers"],
            "spaces_count": len(data["spaces"]),
            "total_usable_area_m2": round(total_usable_area, 2),
            "spaces": [
                {
                    "handle": s["handle"],
                    "layer": s["layer"],
                    "area_m2": s["area"],
                    "perimeter_m": s["perimeter"],
                    "centroid": s["centroid"],
                    "metadata": s["metadata"],
                }
                for s in data["spaces"]
            ],
            "ascii_minimap": ascii_map,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    @cad_tool(mcp, "show_drawing_viewer")
    def show_drawing_viewer(
        filename: str = "visor_cad.html",
        open_browser: bool = True,
    ) -> str:
        """
        Generate and launch an interactive HTML5 CAD Viewer in the web browser.

        Features:
        - Smooth pan & zoom with mouse wheel and drag
        - Interactive layer toggle panel (hide/show layers on the fly)
        - Click on rooms to highlight and inspect usable area (m²), perimeter, and BIM data
        - Dark/Light mode toggle and export buttons

        Args:
            filename: HTML output filename (default: 'visor_cad.html')
            open_browser: If True, automatically launches default system browser (default: True)
        """
        adapter = get_current_adapter()
        data = _get_drawing_entities_data(adapter)

        config = get_config()
        output_dir = Path(config.output.directory).expanduser().resolve()
        clean_filename = filename if filename.lower().endswith(".html") else f"{filename}.html"
        target_path = output_dir / clean_filename

        output_dir.mkdir(parents=True, exist_ok=True)

        # Build self-contained HTML5 interactive viewer
        entities_json = json.dumps(data["entities"], ensure_ascii=False)
        spaces_json = json.dumps(data["spaces"], ensure_ascii=False)
        bbox_json = json.dumps(data["bbox"], ensure_ascii=False)
        layers_json = json.dumps(data["layers"], ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Visor CAD Interactivo | multiCAD-MCP AECO</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #1e293b;
      --text: #f8fafc;
      --accent: #38bdf8;
      --accent-sub: #10b981;
      --border: #334155;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }}
    #sidebar {{
      width: 320px;
      background: var(--panel);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 10;
    }}
    .header {{
      padding: 16px;
      border-bottom: 1px solid var(--border);
      background: rgba(15, 23, 42, 0.4);
    }}
    .header h2 {{ font-size: 1.1rem; color: var(--accent); display: flex; align-items: center; gap: 8px; }}
    .header p {{ font-size: 0.8rem; color: #94a3b8; margin-top: 4px; }}
    .layers-list {{
      flex: 1;
      overflow-y: auto;
      padding: 12px 16px;
    }}
    .layer-item {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 0;
      font-size: 0.85rem;
      cursor: pointer;
    }}
    .layer-item input {{ cursor: pointer; }}
    .info-panel {{
      padding: 16px;
      border-top: 1px solid var(--border);
      background: rgba(15, 23, 42, 0.6);
      font-size: 0.85rem;
    }}
    .info-card {{
      background: #0f172a;
      border: 1px solid var(--accent);
      border-radius: 8px;
      padding: 12px;
      margin-top: 8px;
    }}
    #canvas-container {{
      flex: 1;
      position: relative;
      cursor: grab;
      background: radial-gradient(#1e293b 1px, transparent 1px);
      background-size: 24px 24px;
    }}
    #canvas-container:active {{ cursor: grabbing; }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    .toolbar {{
      position: absolute;
      top: 16px;
      right: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      display: flex;
      gap: 8px;
      padding: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }}
    .btn {{
      background: #334155;
      color: #fff;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .btn:hover {{ background: var(--accent); color: #000; }}
  </style>
</head>
<body>
  <div id="sidebar">
    <div class="header">
      <h2>📐 multiCAD AECO Viewer</h2>
      <p>Dimensiones: <span id="dim-label"></span></p>
    </div>
    <div class="layers-list">
      <h3 style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; margin-bottom: 8px;">Capas del Plano</h3>
      <div id="layers-container"></div>
    </div>
    <div class="info-panel">
      <h3 style="font-size: 0.75rem; text-transform: uppercase; color: #64748b;">Inspector de Recinto</h3>
      <div id="space-info" class="info-card">Haz clic en cualquier recinto del plano para ver sus m² y parámetros.</div>
    </div>
  </div>

  <div id="canvas-container">
    <div class="toolbar">
      <button class="btn" onclick="resetView()">Encuadrar (Zoom E)</button>
    </div>
    <canvas id="cadCanvas"></canvas>
  </div>

  <script>
    const entities = {entities_json};
    const spaces = {spaces_json};
    const bbox = {bbox_json};
    const layers = {layers_json};

    document.getElementById("dim-label").innerText = `${{bbox.width}}m x ${{bbox.length}}m (${{bbox.area_bounding_m2}} m²)`;

    // Layer checkboxes
    const visibleLayers = new Set(layers);
    const container = document.getElementById("layers-container");
    layers.forEach(l => {{
      const div = document.createElement("div");
      div.className = "layer-item";
      div.innerHTML = `<input type="checkbox" checked id="layer-${{l}}"> <label for="layer-${{l}}">${{l}}</label>`;
      div.querySelector("input").addEventListener("change", (e) => {{
        if (e.target.checked) visibleLayers.add(l);
        else visibleLayers.delete(l);
        draw();
      }});
      container.appendChild(div);
    }});

    const canvas = document.getElementById("cadCanvas");
    const ctx = canvas.getContext("2d");

    let scale = 20.0;
    let offsetX = 100.0;
    let offsetY = 100.0;
    let isDragging = false;
    let startX = 0, startY = 0;
    let selectedSpace = null;

    function resize() {{
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
      resetView();
    }}
    window.addEventListener("resize", resize);

    function resetView() {{
      const cw = canvas.width;
      const ch = canvas.height;
      const mw = Math.max(1, bbox.width);
      const mh = Math.max(1, bbox.length);
      scale = Math.min((cw - 120) / mw, (ch - 120) / mh);
      offsetX = (cw - mw * scale) / 2 - bbox.min_x * scale;
      offsetY = (ch + mh * scale) / 2 + bbox.min_y * scale; // Invert CAD Y
      draw();
    }}

    function worldToScreen(wx, wy) {{
      return [wx * scale + offsetX, -wy * scale + offsetY];
    }}
    function screenToWorld(sx, sy) {{
      return [(sx - offsetX) / scale, -(sy - offsetY) / scale];
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw spaces (shaded backgrounds)
      spaces.forEach(s => {{
        if (!visibleLayers.has(s.layer)) return;
        ctx.beginPath();
        const first = worldToScreen(s.polygon[0][0], s.polygon[0][1]);
        ctx.moveTo(first[0], first[1]);
        for (let i = 1; i < s.polygon.length; i++) {{
          const pt = worldToScreen(s.polygon[i][0], s.polygon[i][1]);
          ctx.lineTo(pt[0], pt[1]);
        }}
        ctx.closePath();
        if (selectedSpace === s) {{
          ctx.fillStyle = "rgba(56, 189, 248, 0.4)";
          ctx.strokeStyle = "#38bdf8";
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }} else {{
          ctx.fillStyle = "rgba(51, 65, 85, 0.25)";
        }}
        ctx.fill();

        // Label
        const c = worldToScreen(s.centroid[0], s.centroid[1]);
        ctx.fillStyle = "#94a3b8";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(`${{s.area}} m²`, c[0], c[1]);
      }});

      // Draw entities
      entities.forEach(e => {{
        if (!visibleLayers.has(e.layer)) return;
        ctx.strokeStyle = "#cbd5e1";
        ctx.lineWidth = 1.2;

        if (e.type === "LINE") {{
          const p1 = worldToScreen(e.points[0][0], e.points[0][1]);
          const p2 = worldToScreen(e.points[1][0], e.points[1][1]);
          ctx.beginPath();
          ctx.moveTo(p1[0], p1[1]);
          ctx.lineTo(p2[0], p2[1]);
          ctx.stroke();
        }} else if (e.type === "LWPOLYLINE" || e.type === "POLYLINE") {{
          if (e.points.length > 0) {{
            ctx.beginPath();
            const p0 = worldToScreen(e.points[0][0], e.points[0][1]);
            ctx.moveTo(p0[0], p0[1]);
            for (let i = 1; i < e.points.length; i++) {{
              const p = worldToScreen(e.points[i][0], e.points[i][1]);
              ctx.lineTo(p[0], p[1]);
            }}
            if (e.closed) ctx.closePath();
            ctx.stroke();
          }}
        }} else if (e.type === "CIRCLE") {{
          const c = worldToScreen(e.center[0], e.center[1]);
          ctx.beginPath();
          ctx.arc(c[0], c[1], e.radius * scale, 0, Math.PI * 2);
          ctx.stroke();
        }}
      }});
    }}

    // Pan & Zoom
    canvas.parentElement.addEventListener("mousedown", (e) => {{
      isDragging = true;
      startX = e.clientX - offsetX;
      startY = e.clientY - offsetY;
    }});
    window.addEventListener("mouseup", () => {{ isDragging = false; }});
    window.addEventListener("mousemove", (e) => {{
      if (isDragging) {{
        offsetX = e.clientX - startX;
        offsetY = e.clientY - startY;
        draw();
      }}
    }});
    canvas.parentElement.addEventListener("wheel", (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      offsetX = mx - (mx - offsetX) * zoomFactor;
      offsetY = my - (my - offsetY) * zoomFactor;
      scale *= zoomFactor;
      draw();
    }}, {{ passive: false }});

    // Click inspection
    canvas.addEventListener("click", (e) => {{
      const rect = canvas.getBoundingClientRect();
      const [wx, wy] = screenToWorld(e.clientX - rect.left, e.clientY - rect.top);

      let found = null;
      for (let s of spaces) {{
        // Raycast
        let inside = false;
        const poly = s.polygon;
        for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {{
          const xi = poly[i][0], yi = poly[i][1];
          const xj = poly[j][0], yj = poly[j][1];
          const intersect = ((yi > wy) !== (yj > wy)) && (wx < (xj - xi) * (wy - yi) / (yj - yi) + xi);
          if (intersect) inside = !inside;
        }}
        if (inside) {{
          found = s;
          break;
        }}
      }}

      selectedSpace = found;
      if (found) {{
        document.getElementById("space-info").innerHTML = `
          <strong>Recinto #${{found.handle}}</strong><br>
          Capa: ${{found.layer}}<br>
          Superficie: <span style="color:#38bdf8;font-weight:bold;">${{found.area}} m²</span><br>
          Perímetro: ${{found.perimeter}} m<br>
          Centroide: (${{found.centroid[0]}}, ${{found.centroid[1]}})
        `;
      }} else {{
        document.getElementById("space-info").innerHTML = "Haz clic en cualquier recinto del plano para ver sus m² y parámetros.";
      }}
      draw();
    }});

    setTimeout(resize, 100);
  </script>
</body>
</html>"""

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        if open_browser:
            try:
                webbrowser.open(target_path.as_uri())
            except Exception as e:
                logger.warning(f"Could not open browser: {e}")

        return json.dumps({
            "success": True,
            "viewer_path": str(target_path),
            "opened_in_browser": open_browser,
            "spaces_count": len(data["spaces"]),
            "entities_count": len(data["entities"]),
            "message": f"Interactive CAD Viewer generated at {target_path}",
        }, indent=2, ensure_ascii=False)
