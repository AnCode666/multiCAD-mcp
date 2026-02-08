"""
Unified drawing tool for creating geometric entities.

Replaces 10 individual drawing tools with a single `draw_entities` tool
that accepts a simple shorthand format for ~85% token reduction.

SHORTHAND FORMAT (one per line):
    line|start|end|color|layer                                 → line|0,0|10,10|red|walls
    circle|center|radius|color                                 → circle|5,5|3|blue
    rect|corner1|corner2|color                                 → rect|0,0|20,15
    text|pos|text|height|color                                 → text|5,5|Hello|2.5
    arc|center|radius|start|end                                → arc|0,0|5|0|90
    polyline|points(;)|closed|color                            → polyline|0,0;10,10;20,0|closed
    spline|points(;)|closed|color                              → spline|0,0;5,10;10,0
    leader|puntos|texto|altura|color|capa|tipo                → leader|0,0;10,10;20,10|Mi nota|2.5|red
    leader|grupo1(~~)grupo2(~~)...|texto|altura|color|capa     → leader|0,0;10,10~~0,0;-10,10|Varios

DEFAULTS: color=white, layer=0

Leader automatically detects single vs multiple arrows:
    Flecha simple:   leader|0,0;10,10|My text
    Múltiples:       leader|0,0;10,10~~0,0;-10,10|My text
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple

from mcp.server.fastmcp import Context
from pydantic import ValidationError

from core.models import (
    DrawLineRequest,
    DrawCircleRequest,
    DrawArcRequest,
    DrawRectangleRequest,
    DrawPolylineRequest,
    DrawTextRequest,
    DrawSplineRequest,
    DrawLeaderRequest,
    DrawMLeaderRequest,
)
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate
from mcp_tools.shorthand import parse_drawing_input

logger = logging.getLogger(__name__)


# ========== Entity Handlers ==========
# Each handler: (spec_dict) -> entity_handle
# Adapter is accessed via get_current_adapter() since @cad_tool sets it up.


def _draw_line(spec: Dict[str, Any]) -> str:
    validated = DrawLineRequest(
        start=parse_coordinate(spec["start"]),
        end=parse_coordinate(spec["end"]),
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
        lineweight=spec.get("lineweight", 25),
    )
    return get_current_adapter().draw_line(
        validated.start,
        validated.end,
        validated.layer,
        validated.color,
        validated.lineweight,
        _skip_refresh=True,
    )


def _draw_circle(spec: Dict[str, Any]) -> str:
    validated = DrawCircleRequest(
        center=parse_coordinate(spec["center"]),
        radius=spec["radius"],
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
        lineweight=spec.get("lineweight", 25),
    )
    return get_current_adapter().draw_circle(
        validated.center,
        validated.radius,
        validated.layer,
        validated.color,
        validated.lineweight,
        _skip_refresh=True,
    )


def _draw_arc(spec: Dict[str, Any]) -> str:
    validated = DrawArcRequest(
        center=parse_coordinate(spec["center"]),
        radius=spec["radius"],
        start_angle=spec["start_angle"],
        end_angle=spec["end_angle"],
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
        lineweight=spec.get("lineweight", 25),
    )
    return get_current_adapter().draw_arc(
        validated.center,
        validated.radius,
        validated.start_angle,
        validated.end_angle,
        validated.layer,
        validated.color,
        validated.lineweight,
        _skip_refresh=True,
    )


def _draw_rectangle(spec: Dict[str, Any]) -> str:
    validated = DrawRectangleRequest(
        corner1=parse_coordinate(spec["corner1"]),
        corner2=parse_coordinate(spec["corner2"]),
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
        lineweight=spec.get("lineweight", 25),
    )
    return get_current_adapter().draw_rectangle(
        validated.corner1,
        validated.corner2,
        validated.layer,
        validated.color,
        validated.lineweight,
        _skip_refresh=True,
    )


def _draw_polyline(spec: Dict[str, Any]) -> str:
    points_str = spec["points"]
    point_list = [parse_coordinate(p.strip()) for p in points_str.split("|")]
    validated = DrawPolylineRequest(
        points=point_list,
        closed=spec.get("closed", False),
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
        lineweight=spec.get("lineweight", 25),
    )
    return get_current_adapter().draw_polyline(
        validated.points,
        validated.closed,
        validated.layer,
        validated.color,
        validated.lineweight,
        _skip_refresh=True,
    )


def _draw_text(spec: Dict[str, Any]) -> str:
    validated = DrawTextRequest(
        position=parse_coordinate(spec["position"]),
        text=spec["text"],
        height=spec.get("height", 2.5),
        rotation=spec.get("rotation", 0.0),
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
    )
    return get_current_adapter().draw_text(
        validated.position,
        validated.text,
        validated.height,
        validated.rotation,
        validated.layer,
        validated.color,
        _skip_refresh=True,
    )


def _draw_spline(spec: Dict[str, Any]) -> str:
    points_str = spec["points"]
    point_list = [parse_coordinate(p.strip()) for p in points_str.split("|")]
    validated = DrawSplineRequest(
        points=point_list,
        closed=spec.get("closed", False),
        degree=spec.get("degree", 3),
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
        lineweight=spec.get("lineweight", 25),
    )
    return get_current_adapter().draw_spline(
        validated.points,
        validated.closed,
        validated.degree,
        validated.layer,
        validated.color,
        validated.lineweight,
        _skip_refresh=True,
    )


def _add_dimension(spec: Dict[str, Any]) -> str:
    start_pt = parse_coordinate(spec["start"])
    end_pt = parse_coordinate(spec["end"])
    return get_current_adapter().add_dimension(
        start_pt,
        end_pt,
        None,
        spec.get("text"),
        spec.get("layer", "0"),
        spec.get("color", "white"),
        spec.get("offset", 10.0),
        _skip_refresh=True,
    )


def _draw_leader(spec: Dict[str, Any]) -> str:
    # Leader can now be simple (single arrow) or multi (multiple arrows)
    # Simple: leader|0,0;10,10|texto
    # Multi:  leader|0,0;10,10~~0,0;-10,10|texto

    points_or_groups = spec["points"]

    # Check if this is multi-arrow format (contains ~~)
    if "~~" in points_or_groups:
        # Multi-arrow leader - convert to mleader format
        groups_str = points_or_groups
        base_pt_str = spec.get("base_point", "0,0")

        base_pt = parse_coordinate(base_pt_str)
        leader_groups = []

        for group_str in groups_str.split("~~"):
            group_str = group_str.strip()
            if group_str:
                group_points = [
                    parse_coordinate(p.strip()) for p in group_str.split("|")
                ]
                if group_points:
                    leader_groups.append(group_points)

        if not leader_groups:
            raise ValueError("leader must contain at least one arrow")

        validated = DrawMLeaderRequest(
            base_point=base_pt,
            leader_groups=leader_groups,
            text=spec.get("text"),
            text_height=spec.get("text_height", 2.5),
            color=spec.get("color", "white"),
            layer=spec.get("layer", "0"),
            arrow_style=spec.get("arrow_style", "_ARROW"),
        )

        return get_current_adapter().draw_mleader(
            validated.base_point,
            validated.leader_groups,
            validated.text,
            validated.text_height,
            validated.layer,
            validated.color,
            validated.arrow_style,
            _skip_refresh=True,
        )
    else:
        # Simple single-arrow leader
        point_list = [parse_coordinate(p.strip()) for p in points_or_groups.split("|")]
        validated = DrawLeaderRequest(
            points=point_list,
            text=spec.get("text"),
            text_height=spec.get("text_height", 2.5),
            color=spec.get("color", "white"),
            layer=spec.get("layer", "0"),
            leader_type=spec.get("leader_type", "line_with_arrow"),
        )
        return get_current_adapter().draw_leader(
            validated.points,
            validated.text,
            validated.text_height,
            validated.layer,
            validated.color,
            validated.leader_type,
            _skip_refresh=True,
        )


def _draw_mleader(spec: Dict[str, Any]) -> str:
    base_pt = parse_coordinate(spec["base_point"])

    # Parse leader groups: groups separated by ~~ with points separated by |
    groups_str = spec["leader_groups"]
    leader_groups = []
    for group_str in groups_str.split("~~"):
        group_str = group_str.strip()
        if group_str:
            group_points = [
                parse_coordinate(p.strip()) for p in group_str.split("|")
            ]
            if group_points:
                leader_groups.append(group_points)

    if not leader_groups:
        raise ValueError("leader_groups must contain at least one group with points")

    validated = DrawMLeaderRequest(
        base_point=base_pt,
        leader_groups=leader_groups,
        text=spec.get("text"),
        text_height=spec.get("text_height", 2.5),
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
        arrow_style=spec.get("arrow_style", "_ARROW"),
    )
    return get_current_adapter().draw_mleader(
        validated.base_point,
        validated.leader_groups,
        validated.text,
        validated.text_height,
        validated.layer,
        validated.color,
        validated.arrow_style,
        _skip_refresh=True,
    )


# Dispatch table: type name -> (handler, required_fields)
ENTITY_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "line": (_draw_line, ["start", "end"]),
    "circle": (_draw_circle, ["center", "radius"]),
    "arc": (_draw_arc, ["center", "radius", "start_angle", "end_angle"]),
    "rectangle": (_draw_rectangle, ["corner1", "corner2"]),
    "polyline": (_draw_polyline, ["points"]),
    "text": (_draw_text, ["position", "text"]),
    "spline": (_draw_spline, ["points"]),
    "dimension": (_add_dimension, ["start", "end"]),
    "leader": (_draw_leader, ["points"]),
    "mleader": (_draw_mleader, ["base_point", "leader_groups"]),
}


def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], entity_type: str
) -> Optional[str]:
    """Check required fields are present. Returns error message or None."""
    missing = [f for f in required if f not in spec]
    if missing:
        return f"{entity_type} requires fields: {', '.join(missing)}"
    return None


# ========== Tool Registration ==========


def register_drawing_tools(mcp):
    """Register the unified draw_entities tool with FastMCP."""

    @cad_tool(mcp, "draw_entities")
    def draw_entities(
        ctx: Context,
        entities: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw multiple entities of any type in a single operation.

        Args:
            entities: Entity specifications in SHORTHAND format (one per line):

                line|start|end|color|layer                    → line|0,0|10,10|red|walls
                circle|center|radius|color                    → circle|5,5|3|blue
                rect|corner1|corner2|color                    → rect|0,0|20,15
                text|pos|text|height|color                    → text|5,5|Hello|2.5
                arc|center|radius|start|end                   → arc|0,0|5|0|90
                polyline|points(;)|closed|color               → polyline|0,0;10,10;20,0|closed
                spline|points(;)|closed|color                 → spline|0,0;5,10;10,0
                dimension|start|end|color                     → dimension|0,0|10,0
                leader|puntos|texto|altura|color|capa         → leader|0,0;10,10|Mi nota|2.5|red
                leader|grupo1~~grupo2~~...|texto|altura|color → leader|0,0;10,10~~0,0;-10,10|Nota

                DEFAULTS: color=white, layer=0

                Example:
                    line|0,0|100,0|red|walls
                    line|100,0|100,80|red|walls
                    circle|50,40|10|blue
                    text|50,40|Center|2.5|white
                    leader|50,40;60,50|Dimension|2.5|blue
                    leader|0,0;10,10~~0,0;-10,10|Multiple arrows|2.5|red

                IMPORTANT: Use 'leader' for all arrows and annotations.
                Automatically detects single vs multiple arrows based on input.
                NEVER combine 'line' and 'text' manually for annotations.

                Coordinates: "x,y" or "x,y,z"
                Points: semicolon-separated "0,0;10,10;20,0"
                Multiple arrow groups: double-tilde separated "0,0;10,10~~0,0;20,-5"
                Leader types: line_with_arrow (default), line_no_arrow, spline_with_arrow, spline_no_arrow

                JSON format also supported for backwards compatibility.

            cad_type: CAD application to use

        Returns:
            JSON result with per-entity status and created handles
        """
        try:
            entities_data = parse_drawing_input(entities)
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

        adapter = get_current_adapter()
        results = []

        for i, spec in enumerate(entities_data):
            entity_type = spec.get("type")

            # Validate type field
            if not entity_type:
                results.append(
                    {
                        "index": i,
                        "success": False,
                        "error": "Missing 'type' field. Supported: "
                        + ", ".join(ENTITY_DISPATCH.keys()),
                    }
                )
                continue

            entity_type = entity_type.lower()
            dispatch_entry = ENTITY_DISPATCH.get(entity_type)

            if not dispatch_entry:
                results.append(
                    {
                        "index": i,
                        "type": entity_type,
                        "success": False,
                        "error": f"Unknown type '{entity_type}'. Supported: "
                        + ", ".join(ENTITY_DISPATCH.keys()),
                    }
                )
                continue

            handler, required_fields = dispatch_entry

            # Validate required fields before calling handler
            field_error = _validate_required_fields(spec, required_fields, entity_type)
            if field_error:
                results.append(
                    {
                        "index": i,
                        "type": entity_type,
                        "success": False,
                        "error": field_error,
                    }
                )
                continue

            try:
                handle = handler(spec)
                results.append(
                    {
                        "index": i,
                        "type": entity_type,
                        "handle": handle,
                        "success": True,
                    }
                )
            except ValidationError as e:
                error_msg = f"Validation error: {e.errors()[0]['msg']}"
                logger.error(
                    f"Validation error for entity {i} ({entity_type}): {error_msg}"
                )
                results.append(
                    {
                        "index": i,
                        "type": entity_type,
                        "success": False,
                        "error": error_msg,
                    }
                )
            except Exception as e:
                logger.error(f"Error drawing entity {i} ({entity_type}): {e}")
                results.append(
                    {
                        "index": i,
                        "type": entity_type,
                        "success": False,
                        "error": str(e),
                    }
                )

        # Single refresh after all entities drawn
        if any(r["success"] for r in results):
            adapter.refresh_view()

        return json.dumps(
            {
                "total": len(entities_data),
                "created": sum(1 for r in results if r["success"]),
                "results": results,
            },
            indent=2,
        )
