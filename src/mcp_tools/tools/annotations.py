"""
Smart Architectural Annotations & Dimensioning tools.

Features:
- manage_annotations: Automated dimensioning (bounding box, polyline segments),
  space labeling (centroids with calculated m² and room names), and callouts/leaders.
"""

import json
import math
import logging
from typing import Dict, Any, List, Optional, Union

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate
from mcp_tools.tools.inspection import _get_drawing_entities_data

logger = logging.getLogger(__name__)


def register_annotation_tools(mcp):
    """Register architectural annotation tools with FastMCP."""

    @cad_tool(mcp, "manage_annotations")
    def manage_annotations(
        action: str = "label_spaces",
        handles: Optional[Union[List[str], str]] = None,
        style: str = "overall",
        offset: float = 1.0,
        text_height: float = 0.35,
        prefix: str = "",
        suffix: str = " m²",
        layer: Optional[str] = None,
        color: Optional[str] = None,
    ) -> str:
        """
        Smart architectural annotation and automated dimensioning.

        Actions:
        - "label_spaces": Automatically place room name and calculated m² text at
          the centroid of closed rooms/spaces.
        - "auto_dimension": Automatically create linear dimension annotations for
          bounding boxes ("overall") or individual polyline segments ("segments").
        - "add_leader": Create a leader callout pointing to an entity or coordinate.

        Args:
            action: "label_spaces", "auto_dimension", or "add_leader" (default: "label_spaces")
            handles: Specific entity handle(s) to process. If None, processes all spaces.
            style: Dimension style: "overall" (bounding box) or "segments" (each wall/edge).
            offset: Offset distance from geometry for dimension lines (default: 1.0).
            text_height: Height of annotation text (default: 0.35).
            prefix: Text prefix for space labels (e.g., "S = ").
            suffix: Text suffix for space labels (default: " m²").
            layer: Destination layer (default: "A-ANNO-TEXT" for labels, "A-ANNO-DIMS" for dims).
            color: Color name or code for annotations.

        Examples:
            manage_annotations(action="label_spaces")
            manage_annotations(action="auto_dimension", style="overall", offset=1.5)
            manage_annotations(action="auto_dimension", handles=["1A4"], style="segments")
        """
        adapter = get_current_adapter()
        action_lower = action.lower().strip()

        # Normalize handles if passed as string or comma-separated list
        target_handles = None
        if handles:
            if isinstance(handles, str):
                target_handles = [h.strip() for h in handles.split(",") if h.strip()]
            else:
                target_handles = [str(h).strip() for h in handles]

        # Extract drawing data
        data = _get_drawing_entities_data(adapter)
        spaces = data["spaces"]
        if target_handles:
            spaces = [s for s in spaces if s["handle"] in target_handles]

        created_entities = []

        # ==========================================
        # ACTION: label_spaces
        # ==========================================
        if action_lower in ("label_spaces", "label", "etiquetar", "rotular"):
            target_layer = layer or "A-ANNO-TEXT"
            text_color = color or "yellow"

            # Ensure layer exists
            if hasattr(adapter, "create_layer"):
                try:
                    adapter.create_layer(target_layer, color=text_color)
                except Exception:
                    pass

            for s in spaces:
                cx, cy = s["centroid"]
                area = s["area"]
                metadata = s.get("metadata", {})
                room_name = (
                    metadata.get("nombre")
                    or metadata.get("name")
                    or metadata.get("tipo")
                    or metadata.get("type")
                    or f"Espacio #{s['handle']}"
                )

                label_text = f"{room_name}\n{prefix}{area:.2f}{suffix}"

                # Draw text using adapter
                if hasattr(adapter, "draw_text"):
                    h = adapter.draw_text(
                        position=(cx, cy, 0.0),
                        text=label_text,
                        height=text_height,
                        layer=target_layer,
                        color=text_color,
                    )
                    created_entities.append({
                        "handle": h,
                        "type": "TEXT",
                        "text": label_text,
                        "position": (cx, cy),
                        "room_handle": s["handle"],
                        "area_m2": area,
                    })

            return json.dumps({
                "success": True,
                "action": "label_spaces",
                "layer": target_layer,
                "count": len(created_entities),
                "labels": created_entities,
                "message": f"Successfully labeled {len(created_entities)} spaces with centroid areas.",
            }, indent=2, ensure_ascii=False)

        # ==========================================
        # ACTION: auto_dimension
        # ==========================================
        elif action_lower in ("auto_dimension", "dimension", "acotar", "cotas"):
            target_layer = layer or "A-ANNO-DIMS"
            dim_color = color or "cyan"

            if hasattr(adapter, "create_layer"):
                try:
                    adapter.create_layer(target_layer, color=dim_color)
                except Exception:
                    pass

            style_lower = style.lower().strip()

            if style_lower in ("overall", "bbox", "exterior", "general"):
                # Dimension the overall bounding box (Horizontal bottom + Vertical left)
                bbox = data["bbox"]
                min_x, max_x = bbox["min_x"], bbox["max_x"]
                min_y, max_y = bbox["min_y"], bbox["max_y"]

                # Bottom horizontal dimension
                h_bot = adapter.add_dimension(
                    start=(min_x, min_y, 0.0),
                    end=(max_x, min_y, 0.0),
                    offset=offset,
                    layer=target_layer,
                    color=dim_color,
                )
                created_entities.append({
                    "handle": h_bot,
                    "type": "DIMENSION",
                    "subtype": "horizontal_overall",
                    "length": bbox["width"],
                    "start": (min_x, min_y),
                    "end": (max_x, min_y),
                })

                # Left vertical dimension
                h_left = adapter.add_dimension(
                    start=(min_x, min_y, 0.0),
                    end=(min_x, max_y, 0.0),
                    offset=offset,
                    layer=target_layer,
                    color=dim_color,
                )
                created_entities.append({
                    "handle": h_left,
                    "type": "DIMENSION",
                    "subtype": "vertical_overall",
                    "length": bbox["length"],
                    "start": (min_x, min_y),
                    "end": (min_x, max_y),
                })

            elif style_lower in ("segments", "walls", "perimetral", "tramos"):
                # Dimension each segment of selected closed polylines/rooms
                for s in spaces:
                    poly = s["polygon"]
                    n = len(poly)
                    for i in range(n):
                        p1 = poly[i]
                        p2 = poly[(i + 1) % n]
                        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                        if seg_len < 0.1:
                            continue

                        h_dim = adapter.add_dimension(
                            start=(p1[0], p1[1], 0.0),
                            end=(p2[0], p2[1], 0.0),
                            offset=offset,
                            layer=target_layer,
                            color=dim_color,
                        )
                        created_entities.append({
                            "handle": h_dim,
                            "type": "DIMENSION",
                            "subtype": "segment",
                            "room_handle": s["handle"],
                            "length": round(seg_len, 2),
                            "start": p1,
                            "end": p2,
                        })

            return json.dumps({
                "success": True,
                "action": "auto_dimension",
                "style": style_lower,
                "layer": target_layer,
                "count": len(created_entities),
                "dimensions": created_entities,
                "message": f"Created {len(created_entities)} dimension annotations.",
            }, indent=2, ensure_ascii=False)

        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown action '{action}'. Supported actions: 'label_spaces', 'auto_dimension'.",
            })
