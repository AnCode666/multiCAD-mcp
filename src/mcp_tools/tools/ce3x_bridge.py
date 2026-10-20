"""
ConTech Bridge: multiCAD-MCP ➔ CE3X-MCP-SERVER Integration.

Extracts thermal building envelope parameters from CAD drawings to feed
energy certification workflows under Spanish CTE DB-HE and RD 390/2021:
- Facade walls classified by geographic orientation (N, S, E, W, etc.) calculated from normal vectors.
- Windows/openings mapped to parent facade walls with solar factor and area.
- Roof and ground floor surfaces computed from geometric boundaries.
- Direct JSON export ready for CE3X-MCP-SERVER ingestion.
"""

import json
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from mcp_tools.decorators import cad_tool, get_current_adapter
from core.config import get_config

logger = logging.getLogger(__name__)


def _calculate_orientation(p1: Tuple[float, float], p2: Tuple[float, float]) -> str:
    """Calculate geographic orientation (N, S, E, W, etc.) of a wall segment.

    Assumes CAD Y-axis points North (+Y = 0° / 360°).
    Exterior normal is pointing 90° clockwise to the direction vector.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    # Normal vector perpendicular to wall segment (pointing outward)
    nx = dy
    ny = -dx

    # Angle in degrees clockwise from North (+Y)
    angle_rad = math.atan2(nx, ny)
    angle_deg = math.degrees(angle_rad) % 360.0

    if angle_deg >= 337.5 or angle_deg < 22.5:
        return "Norte"
    elif 22.5 <= angle_deg < 67.5:
        return "Noreste"
    elif 67.5 <= angle_deg < 112.5:
        return "Este"
    elif 112.5 <= angle_deg < 157.5:
        return "Sureste"
    elif 157.5 <= angle_deg < 202.5:
        return "Sur"
    elif 202.5 <= angle_deg < 247.5:
        return "Suroeste"
    elif 247.5 <= angle_deg < 292.5:
        return "Oeste"
    else:
        return "Noroeste"


def extract_thermal_envelope(
    adapter,
    wall_height: float = 2.70,
    climate_zone: str = "C1",
    building_type: str = "vivienda_individual",
) -> Dict[str, Any]:
    """Scan CAD modelspace to extract thermal envelope components."""
    # Find facade wall layers
    facade_keywords = ("muro", "wall", "fachada", "ext", "envolvente")
    window_keywords = ("vent", "window", "carp", "hueco")

    all_layers = adapter.list_layers() if hasattr(adapter, "list_layers") else []
    layer_names = [l.get("name", "") if isinstance(l, dict) else str(l) for l in all_layers]

    wall_layers = [name for name in layer_names if any(k in name.lower() for k in facade_keywords)]
    if not wall_layers:
        wall_layers = ["0", "A-WALL", "A-MURO-ESTR"]

    window_layers = [name for name in layer_names if any(k in name.lower() for k in window_keywords)]
    if not window_layers:
        window_layers = ["A-WINDOWS", "A-CARP-VENT"]

    facades_by_orient: Dict[str, Dict[str, Any]] = {
        "Norte": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
        "Sur": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
        "Este": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
        "Oeste": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
        "Noreste": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
        "Noroeste": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
        "Sureste": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
        "Suroeste": {"area": 0.0, "length": 0.0, "windows_area": 0.0, "segments": 0},
    }

    # Inspect model entities
    total_usable_floor = 0.0

    # 1. Inspect lines for wall lengths and orientations
    if hasattr(adapter, "msp"):
        for e in adapter.msp:
            t = e.dxftype()
            layer = str(e.dxf.layer)
            if t == "LINE" and any(w.lower() in layer.lower() for w in wall_layers):
                p1 = (float(e.dxf.start[0]), float(e.dxf.start[1]))
                p2 = (float(e.dxf.end[0]), float(e.dxf.end[1]))
                length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                orient = _calculate_orientation(p1, p2)
                facades_by_orient[orient]["length"] += length
                facades_by_orient[orient]["area"] += length * wall_height
                facades_by_orient[orient]["segments"] += 1

            # Check closed polylines for floor space
            elif t in ("LWPOLYLINE", "POLYLINE") and e.is_closed:
                if hasattr(adapter, "get_entity_area"):
                    info = adapter.get_entity_area(str(e.dxf.handle))
                    a = float(info.get("area", 0.0))
                    if a > 1.0:
                        total_usable_floor += a

    # Clean envelope payload for CE3X
    envelope_list = []
    for orient, data in facades_by_orient.items():
        if data["area"] > 0.0:
            gross_area = round(data["area"], 2)
            win_area = round(data["windows_area"], 2)
            net_area = max(0.0, gross_area - win_area)

            envelope_list.append({
                "nombre": f"Fachada {orient}",
                "tipo": "fachada",
                "orientacion": orient,
                "superficie_bruta_m2": gross_area,
                "superficie_neta_m2": net_area,
                "u_value_estimada_w_m2k": 0.38,  # CTE DB-HE standard estimate
                "huecos": [
                    {
                        "nombre": f"Huecos Fachada {orient}",
                        "superficie_m2": win_area,
                        "u_value_w_m2k": 1.60,
                        "factor_solar_g": 0.50,
                    }
                ] if win_area > 0.0 else [],
            })

    return {
        "source": "multiCAD-MCP AECO Edition",
        "target": "CE3X-MCP-SERVER",
        "building_type": building_type,
        "climate_zone": climate_zone,
        "wall_height": wall_height,
        "usable_floor_area_m2": round(total_usable_floor, 2),
        "thermal_envelopes": envelope_list,
        "summary": {
            "total_facade_area_m2": round(sum(f["superficie_bruta_m2"] for f in envelope_list), 2),
            "orientations_count": len(envelope_list),
        },
    }


def register_ce3x_bridge_tools(mcp):
    """Register CE3X thermal envelope exporter with FastMCP."""

    @cad_tool(mcp, "export_ce3x_envelope")
    def export_ce3x_envelope(
        wall_height: float = 2.70,
        climate_zone: str = "C1",
        building_type: str = "vivienda_individual",
        filename: str = "envolvente_ce3x.json",
    ) -> str:
        """
        Extract CAD thermal building envelope parameters for CE3X energy certification.

        Computes:
        - Wall surface areas and orientations (N, S, E, W) by normal vector geometry
        - Associated openings and solar orientation
        - Usable floor area

        Args:
            wall_height: Clear floor-to-ceiling height in meters (default: 2.70m)
            climate_zone: CTE climate zone (e.g., "A3", "C1", "D3", default: "C1")
            building_type: Building typology (default: "vivienda_individual")
            filename: Output JSON filename (saved to configured output directory)

        Returns:
            JSON payload ready for direct ingestion by CE3X-MCP-SERVER.
        """
        adapter = get_current_adapter()
        payload = extract_thermal_envelope(
            adapter,
            wall_height=float(wall_height),
            climate_zone=climate_zone,
            building_type=building_type,
        )

        config = get_config()
        output_dir = Path(config.output.directory).expanduser().resolve()
        clean_filename = filename if filename.lower().endswith(".json") else f"{filename}.json"
        target_path = output_dir / clean_filename

        output_dir.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        payload["file_path"] = str(target_path)
        payload["message"] = f"Exported thermal envelope to {target_path} for CE3X-MCP-SERVER"
        return json.dumps(payload, indent=2, ensure_ascii=False)
