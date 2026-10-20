"""
Unified drawing tool for creating geometric entities.

Replaces 10 individual drawing tools with a single `draw_entities` tool
that accepts a simple shorthand format for ~85% token reduction.

SHORTHAND FORMAT (one per line):
    line|start|end|color|layer                               → line|0,0|10,10|red|walls
    circle|center|radius|color                               → circle|5,5|3|blue
    rect|corner1|corner2|color                               → rect|0,0|20,15
    text|pos|text|height|color                               → text|5,5|Hello|2.5
    arc|center|radius|start|end                              → arc|0,0|5|0|90
    polyline|points(;)|closed|color                          → polyline|0,0;10,10;20,0|closed
    spline|points(;)|closed|color                            → spline|0,0;5,10;10,0
    leader|points|text|height|color|layer|type               → leader|0,0;10,10;20,10|Mi nota|2.5|red
    leader|group1~~group2~~...|text|height|color|layer       → leader|0,0;10,10~~0,0;-10,10|Nota

    DEFAULTS: color=white, layer=0

    IMPORTANT for Leaders:
    - Points order: [ArrowHead, ..., TextPosition]
    - First point is where the arrow starts. Last point is where the text attaches.
    - Use '~~' to separate multiple arrow groups.
    - Each group must have at least 2 points.

    Examples:
        Single arrow: leader|10,10;50,50|Label
                      -> Arrow at 10,10, Text at 50,50

        Multi arrow:  leader|10,10;50,50~~10,90;50,50|Label
                      -> Arrow 1 at 10,10, Arrow 2 at 10,90
                      -> Both converge to Text at 50,50
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple


from pydantic import ValidationError

from core.models import (
    DrawLineRequest,
    DrawCircleRequest,
    DrawArcRequest,
    DrawRectangleRequest,
    DrawPolylineRequest,
    DrawTextRequest,
    DrawSplineRequest,
    DrawMLeaderRequest,
    DrawTableRequest,
)
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate
from mcp_tools.shorthand import parse_drawing_input

logger = logging.getLogger(__name__)


# ========== Entity Handlers ==========
# Each handler: (spec_dict) -> entity_handle
# Adapter is accessed via get_current_adapter() since @cad_tool sets it up.


def _draw_line(spec: Dict[str, Any]) -> str:
    """Draw a line entity from start to end point.

    Args:
        spec: Entity spec with keys: start (str), end (str),
            color (str, optional), layer (str, optional), lineweight (int, optional).

    Returns:
        Entity handle string for the created line.
    """
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
    """Draw a circle entity with center and radius.

    Args:
        spec: Entity spec with keys: center (str), radius (float),
            color (str, optional), layer (str, optional), lineweight (int, optional).

    Returns:
        Entity handle string for the created circle.
    """
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
    """Draw an arc entity with center, radius, and angle range.

    Args:
        spec: Entity spec with keys: center (str), radius (float),
            start_angle (float), end_angle (float),
            color (str, optional), layer (str, optional), lineweight (int, optional).

    Returns:
        Entity handle string for the created arc.
    """
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
    """Draw a rectangle from two corner points.

    Args:
        spec: Entity spec with keys: corner1 (str), corner2 (str),
            color (str, optional), layer (str, optional), lineweight (int, optional).

    Returns:
        Entity handle string for the created rectangle.
    """
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
    """Draw a polyline from a sequence of points.

    Args:
        spec: Entity spec with keys: points (str, pipe or semicolon separated),
            closed (bool, optional), color (str, optional),
            layer (str, optional), lineweight (int, optional).

    Returns:
        Entity handle string for the created polyline.
    """
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
    """Draw a text entity at a given position.

    Args:
        spec: Entity spec with keys: position (str), text (str),
            height (float, optional), rotation (float, optional),
            color (str, optional), layer (str, optional).

    Returns:
        Entity handle string for the created text entity.
    """
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
    """Draw a spline curve through a sequence of points.

    Args:
        spec: Entity spec with keys: points (str, pipe or semicolon separated),
            closed (bool, optional), degree (int, optional),
            color (str, optional), layer (str, optional), lineweight (int, optional).

    Returns:
        Entity handle string for the created spline.
    """
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
    """Add a linear dimension between two points.

    Args:
        spec: Entity spec with keys: start (str), end (str),
            text (str, optional), layer (str, optional),
            color (str, optional), offset (float, optional).

    Returns:
        Entity handle string for the created dimension.
    """
    start_pt = parse_coordinate(spec["start"])
    end_pt = parse_coordinate(spec["end"])
    return get_current_adapter().add_dimension(
        start_pt,
        end_pt,
        spec.get("text"),
        spec.get("layer", "0"),
        spec.get("color", "white"),
        spec.get("offset", 10.0),
        _skip_refresh=True,
    )


def _draw_leader_unified(spec: Dict[str, Any]) -> str:
    """Unified handler for leader and mleader entities.

    Always creates an MLeader entity, even for single-line leaders.
    Input formats:
        Simple: leader|0,0;10,10|text...
        Multi:  leader|0,0;10,10~~20,0;10,10|text...
    """
    # 1. Determine base point and leader groups
    base_pt = None
    leader_groups = []

    if "leader_groups" in spec:
        # JSON/Explicit format (mleader)
        base_pt = parse_coordinate(spec["base_point"])
        groups_str = spec["leader_groups"]
        if isinstance(groups_str, list):
            # Already a list of points (from JSON)
            leader_groups = groups_str
        else:
            # String format: "0,0;10,10~~..."
            for group_str in groups_str.split("~~"):
                group_str = group_str.strip()
                if group_str:
                    group_points = [
                        parse_coordinate(p.strip()) for p in group_str.split(";")
                    ]
                    if group_points:
                        leader_groups.append(group_points)

    elif "points" in spec:
        # Shorthand format (leader)
        points_or_groups = spec["points"]

        if "~~" in points_or_groups:
            # Multi-arrow shorthand
            groups_str = points_or_groups
            # For shorthand, we don't need a separate base_point,
            # MLeader will use the first point of the first group usually.
            # But the adapter might need one. We'll use 0,0 provided, or infer it.
            base_pt_str = spec.get("base_point", "0,0")
            base_pt = parse_coordinate(base_pt_str)

            for group_str in groups_str.split("~~"):
                group_str = group_str.strip()
                if group_str:
                    # Handle both | and ; separators for robustness
                    # Shorthand might have converted ; to | already
                    clean_str = group_str.replace(";", "|")
                    group_points = [
                        parse_coordinate(p.strip())
                        for p in clean_str.split("|")
                        if p.strip()
                    ]

                    if len(group_points) < 2:
                        logger.warning(
                            f"Leader group parsed with < 2 points: {group_str} -> {group_points}"
                        )

                    if group_points:
                        leader_groups.append(group_points)
        else:
            # Simple single-arrow shorthand
            # Treat the whole points string as one group
            clean_str = points_or_groups.replace(";", "|")
            group_points = [
                parse_coordinate(p.strip()) for p in clean_str.split("|") if p.strip()
            ]
            if group_points:
                leader_groups.append(group_points)

            # Use the first point as base point if not specified
            if group_points:
                base_pt = group_points[0]
            else:
                base_pt = parse_coordinate(spec.get("base_point", "0,0"))

    if not leader_groups:
        raise ValueError("Leader must have at least one group of points")

    # Ensure base_pt is set (default to first point of first group)
    if base_pt is None and leader_groups and leader_groups[0]:
        base_pt = leader_groups[0][0]
    elif base_pt is None:
        base_pt = (0.0, 0.0, 0.0)

    logger.info(
        f"Unified Leader Groups Parsed: {len(leader_groups)} groups. Spec: {leader_groups}"
    )

    text_height_val = spec.get("text_height")
    if text_height_val is None:
        text_height_val = spec.get("height")
    if text_height_val is None:
        text_height_val = 2.5

    validated = DrawMLeaderRequest(
        base_point=base_pt,
        leader_groups=leader_groups,
        text=spec.get("text"),
        text_height=text_height_val,
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


def _draw_table(spec: Dict[str, Any]) -> str:
    """Draw a table entity.

    Args:
        spec: Entity spec with keys: insertion_point (str), num_rows (int), num_cols (int),
            row_height (float, optional), col_width (float, optional),
            title (str, optional), headers (str or list, optional), data (str or list, optional),
            color (str, optional), layer (str, optional).

    Returns:
        Entity handle string for the created table.
    """
    ins_pt = parse_coordinate(spec["insertion_point"])
    
    headers = spec.get("headers")
    if isinstance(headers, str):
        headers = [h.strip() for h in headers.split(";") if h.strip()]
        
    data = spec.get("data")
    if isinstance(data, str):
        parsed_data = []
        for row_str in data.split("~~"):
            row_str = row_str.strip()
            if row_str:
                row_cells = [c.strip() for c in row_str.split(";")]
                parsed_data.append(row_cells)
        data = parsed_data

    validated = DrawTableRequest(
        insertion_point=ins_pt,
        num_rows=int(spec["num_rows"]),
        num_cols=int(spec["num_cols"]),
        row_height=float(spec.get("row_height", 3.0)),
        col_width=float(spec.get("col_width", 15.0)),
        data=data,
        title=spec.get("title"),
        headers=headers,
        color=spec.get("color", "white"),
        layer=spec.get("layer", "0"),
    )
    
    return get_current_adapter().draw_table(
        validated.insertion_point,
        validated.num_rows,
        validated.num_cols,
        validated.row_height,
        validated.col_width,
        validated.data,
        validated.title,
        validated.headers,
        validated.layer,
        validated.color,
        _skip_refresh=True,
    )


def _draw_wall(spec: Dict[str, Any]) -> str:
    """Draw a wall macro as a closed rectangular polyline with thickness."""
    import math

    p1 = parse_coordinate(spec["start"])
    p2 = parse_coordinate(spec["end"])
    thickness = float(spec.get("thickness", 0.15))
    layer = str(spec.get("layer", "A-MURO-ESTR"))
    color = spec.get("color", "red")

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return ""

    half_th = thickness / 2.0
    nx = (-dy / length) * half_th
    ny = (dx / length) * half_th

    c1 = (p1[0] + nx, p1[1] + ny)
    c2 = (p2[0] + nx, p2[1] + ny)
    c3 = (p2[0] - nx, p2[1] - ny)
    c4 = (p1[0] - nx, p1[1] - ny)

    adapter = get_current_adapter()
    return adapter.draw_polyline(
        [c1, c2, c3, c4],
        closed=True,
        layer=layer,
        color=color,
        _skip_refresh=True,
    )


def _draw_door(spec: Dict[str, Any]) -> str:
    """Draw an architectural door macro (leaf line + 90-degree swing arc)."""
    import math

    hinge = parse_coordinate(spec["hinge"])
    width = float(spec.get("width", 0.82))
    base_angle = float(spec.get("angle", 0.0))
    layer = str(spec.get("layer", "A-CARP-PUER"))
    color = spec.get("color", "green")

    open_angle_rad = math.radians(base_angle + 90.0)
    leaf_end = (
        hinge[0] + width * math.cos(open_angle_rad),
        hinge[1] + width * math.sin(open_angle_rad),
    )

    adapter = get_current_adapter()
    leaf_handle = adapter.draw_line(
        hinge, leaf_end, layer=layer, color=color, _skip_refresh=True
    )
    adapter.draw_arc(
        hinge,
        radius=width,
        start_angle=base_angle,
        end_angle=base_angle + 90.0,
        layer=layer,
        color=color,
        _skip_refresh=True,
    )
    return leaf_handle


def _draw_window(spec: Dict[str, Any]) -> str:
    """Draw an architectural window macro (frame outline + central glass line)."""
    import math

    p1 = parse_coordinate(spec["start"])
    p2 = parse_coordinate(spec["end"])
    thickness = float(spec.get("thickness", 0.10))
    layer = str(spec.get("layer", "A-CARP-VENT"))
    color = spec.get("color", "cyan")

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return ""

    half_th = thickness / 2.0
    nx = (-dy / length) * half_th
    ny = (dx / length) * half_th

    c1 = (p1[0] + nx, p1[1] + ny)
    c2 = (p2[0] + nx, p2[1] + ny)
    c3 = (p2[0] - nx, p2[1] - ny)
    c4 = (p1[0] - nx, p1[1] - ny)

    adapter = get_current_adapter()
    frame_handle = adapter.draw_polyline(
        [c1, c2, c3, c4],
        closed=True,
        layer=layer,
        color=color,
        _skip_refresh=True,
    )
    adapter.draw_line(p1, p2, layer=layer, color=color, _skip_refresh=True)
    return frame_handle


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
    # Both leader types now use the unified handler
    "leader": (_draw_leader_unified, ["points"]),
    "mleader": (_draw_leader_unified, ["leader_groups"]),
    "table": (_draw_table, ["insertion_point", "num_rows", "num_cols"]),
    "wall": (_draw_wall, ["start", "end"]),
    "door": (_draw_door, ["hinge"]),
    "window": (_draw_window, ["start", "end"]),
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
        entities: str,
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
                table|ins|rows|cols|row_h|col_w|title|headers|data → table|0,0|4|3|3|15|Precios|Item;Cant;Val|Acero;10;150~~Mano;5;120

                DEFAULTS: color=white, layer=0

                Example:
                    line|0,0|100,0|red|walls
                    line|100,0|100,80|red|walls
                    circle|50,40|10|blue
                    text|50,40|Center|2.5|white
                    leader|50,40;60,50|Dimension|2.5|blue
                    leader|0,0;10,10~~20,0;10,10|Converging Arrows|2.5|red
                    table|0,0|4|3|3|15|Precios|Item;Cant;Val|Acero;10;150~~Pintura;5;50

                IMPORTANT for Leaders:
                - Always creates an MLeader entity.
                - Format: `leader|group1~~group2|text...`
                - Each group is a list of points: `arrow_start;...;text_attach_point`
                - To create multiple arrows pointing to the SAME text, ensure the LAST point
                  of every group is the SAME (the text position).

                IMPORTANT for Tables:
                - Creates a native AutoCAD table entity.
                - Row 0 is the Title. Row 1 contains column Headers. Row 2 and onwards are Data rows.
                - Headers: Semicolon-separated values for the columns.
                - Data: Rows separated by double tildes `~~`, and cell values within each row separated by semicolons `;`.

                Example of Multi-Arrow Leader (Converging):
                    `leader|10,10;50,50~~10,90;50,50|Label`
                    -> Arrow 1 starts at 10,10
                    -> Arrow 2 starts at 10,90
                    -> Both converge at 50,50 (where text "Label" is placed)

                Coordinates: "x,y" or "x,y,z"
                Points within group: semicolon-separated "10,10;50,50"
                Multiple groups: double-tilde separated "g1~~g2"

                JSON format also supported for backwards compatibility.

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
