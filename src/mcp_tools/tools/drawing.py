"""
Drawing tools for creating geometric entities.

Provides tools for:
- Drawing lines, circles, arcs, rectangles, polylines, text, dimensions
- Batch operations for efficient multi-entity creation
"""

import json
import logging
from typing import Optional, TypedDict, List, Any

from mcp.server.fastmcp import Context

from core import InvalidParameterError
from mcp_tools.decorators import cad_tool
from mcp_tools.helpers import parse_coordinate
from mcp_tools.decorators import get_current_adapter

logger = logging.getLogger(__name__)


# ========== TypedDict Specifications ==========


class LineSpec(TypedDict, total=False):
    """Specification for a line to draw."""

    start: str
    end: str
    color: str
    layer: str
    lineweight: int


class CircleSpec(TypedDict, total=False):
    """Specification for a circle to draw."""

    center: str
    radius: float
    color: str
    layer: str
    lineweight: int


class ArcSpec(TypedDict, total=False):
    """Specification for an arc to draw."""

    center: str
    radius: float
    start_angle: float
    end_angle: float
    color: str
    layer: str
    lineweight: int


class RectangleSpec(TypedDict, total=False):
    """Specification for a rectangle to draw."""

    corner1: str
    corner2: str
    color: str
    layer: str
    lineweight: int


class PolylineSpec(TypedDict, total=False):
    """Specification for a polyline to draw."""

    points: str
    closed: bool
    color: str
    layer: str
    lineweight: int


class TextSpec(TypedDict, total=False):
    """Specification for text to draw."""

    position: str
    text: str
    height: float
    rotation: float
    color: str
    layer: str


class DimensionSpec(TypedDict, total=False):
    """Specification for a dimension to add."""

    start: str
    end: str
    color: str
    layer: str
    text: Optional[str]
    offset: float


def register_drawing_tools(mcp):
    """Register drawing tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    # ========== BATCH OPERATIONS (Optimized for Multiple Entities) ==========

    @cad_tool(mcp, "draw_lines")
    def draw_lines(
        ctx: Context,
        lines: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw multiple lines in a single operation.

        Args:
            lines: JSON array of line specifications.
                   Example: [{"start": "0,0", "end": "10,10", "color": "red", "layer": "0", "lineweight": 0}]
                   Fields: start (required), end (required), color (default: "white"),
                           layer (default: "0"), lineweight (default: 0)
            cad_type: CAD application to use

        Returns:
            JSON result with created entity handles
        """
        try:
            lines_data = json.loads(lines) if isinstance(lines, str) else lines
            if not isinstance(lines_data, list):
                lines_data = [lines_data]

            results = []
            for i, line_spec in enumerate(lines_data):
                try:
                    start_pt = parse_coordinate(line_spec["start"])
                    end_pt = parse_coordinate(line_spec["end"])
                    color = line_spec.get("color", "white")
                    layer = line_spec.get("layer", "0")
                    lineweight = line_spec.get("lineweight", 0)

                    handle = get_current_adapter().draw_line(
                        start_pt, end_pt, layer, color, lineweight
                    )
                    results.append({"index": i, "handle": handle, "success": True})
                except Exception as e:
                    logger.error(f"Error drawing line {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(lines_data),
                    "created": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "draw_circles")
    def draw_circles(
        ctx: Context,
        circles: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw multiple circles in a single operation.

        Args:
            circles: JSON array of circle specifications.
                     Example: [{"center": "0,0", "radius": 5.0, "color": "blue", "layer": "0", "lineweight": 0}]
                     Fields: center (required), radius (required), color (default: "white"),
                             layer (default: "0"), lineweight (default: 0)
            cad_type: CAD application to use

        Returns:
            JSON result with created entity handles
        """
        try:
            circles_data = json.loads(circles) if isinstance(circles, str) else circles
            if not isinstance(circles_data, list):
                circles_data = [circles_data]

            results = []
            for i, circle_spec in enumerate(circles_data):
                try:
                    center_pt = parse_coordinate(circle_spec["center"])
                    radius = circle_spec["radius"]

                    if radius <= 0:
                        raise InvalidParameterError("radius", radius, "positive number")

                    color = circle_spec.get("color", "white")
                    layer = circle_spec.get("layer", "0")
                    lineweight = circle_spec.get("lineweight", 0)

                    handle = get_current_adapter().draw_circle(
                        center_pt, radius, layer, color, lineweight
                    )
                    results.append({"index": i, "handle": handle, "success": True})
                except Exception as e:
                    logger.error(f"Error drawing circle {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(circles_data),
                    "created": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "draw_arcs")
    def draw_arcs(
        ctx: Context,
        arcs: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw multiple arcs in a single operation.

        Args:
            arcs: JSON array of arc specifications.
                  Example: [{"center": "0,0", "radius": 5.0, "start_angle": 0, "end_angle": 90, "color": "green"}]
                  Fields: center (required), radius (required), start_angle (required), end_angle (required),
                          color (default: "white"), layer (default: "0"), lineweight (default: 0)
            cad_type: CAD application to use

        Returns:
            JSON result with created entity handles
        """
        try:
            arcs_data = json.loads(arcs) if isinstance(arcs, str) else arcs
            if not isinstance(arcs_data, list):
                arcs_data = [arcs_data]

            results = []
            for i, arc_spec in enumerate(arcs_data):
                try:
                    center_pt = parse_coordinate(arc_spec["center"])
                    radius = arc_spec["radius"]
                    start_angle = arc_spec["start_angle"]
                    end_angle = arc_spec["end_angle"]
                    color = arc_spec.get("color", "white")
                    layer = arc_spec.get("layer", "0")
                    lineweight = arc_spec.get("lineweight", 0)

                    handle = get_current_adapter().draw_arc(
                        center_pt,
                        radius,
                        start_angle,
                        end_angle,
                        layer,
                        color,
                        lineweight,
                    )
                    results.append({"index": i, "handle": handle, "success": True})
                except Exception as e:
                    logger.error(f"Error drawing arc {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(arcs_data),
                    "created": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "draw_rectangles")
    def draw_rectangles(
        ctx: Context,
        rectangles: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw multiple rectangles in a single operation.

        Args:
            rectangles: JSON array of rectangle specifications.
                        Example: [{"corner1": "0,0", "corner2": "10,10", "color": "yellow"}]
                        Fields: corner1 (required), corner2 (required), color (default: "white"),
                                layer (default: "0"), lineweight (default: 0)
            cad_type: CAD application to use

        Returns:
            JSON result with created entity handles
        """
        try:
            rects_data = (
                json.loads(rectangles) if isinstance(rectangles, str) else rectangles
            )
            if not isinstance(rects_data, list):
                rects_data = [rects_data]

            results = []
            for i, rect_spec in enumerate(rects_data):
                try:
                    pt1 = parse_coordinate(rect_spec["corner1"])
                    pt2 = parse_coordinate(rect_spec["corner2"])
                    color = rect_spec.get("color", "white")
                    layer = rect_spec.get("layer", "0")
                    lineweight = rect_spec.get("lineweight", 0)

                    handle = get_current_adapter().draw_rectangle(
                        pt1, pt2, layer, color, lineweight
                    )
                    results.append({"index": i, "handle": handle, "success": True})
                except Exception as e:
                    logger.error(f"Error drawing rectangle {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(rects_data),
                    "created": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "draw_polylines")
    def draw_polylines(
        ctx: Context,
        polylines: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw multiple polylines in a single operation.

        Args:
            polylines: JSON array of polyline specifications.
                       Example: [{"points": "0,0|10,10|20,0", "closed": true, "color": "cyan"}]
                       Fields: points (required, pipe-separated), closed (default: false),
                               color (default: "white"), layer (default: "0"), lineweight (default: 0)
            cad_type: CAD application to use

        Returns:
            JSON result with created entity handles
        """
        try:
            polylines_data = (
                json.loads(polylines) if isinstance(polylines, str) else polylines
            )
            if not isinstance(polylines_data, list):
                polylines_data = [polylines_data]

            results = []
            for i, poly_spec in enumerate(polylines_data):
                try:
                    points_str = poly_spec["points"]
                    point_list = [
                        parse_coordinate(p.strip()) for p in points_str.split("|")
                    ]

                    if len(point_list) < 2:
                        raise InvalidParameterError(
                            "points", points_str, "at least 2 points"
                        )

                    closed = poly_spec.get("closed", False)
                    color = poly_spec.get("color", "white")
                    layer = poly_spec.get("layer", "0")
                    lineweight = poly_spec.get("lineweight", 0)

                    handle = get_current_adapter().draw_polyline(
                        point_list, closed, layer, color, lineweight
                    )
                    results.append({"index": i, "handle": handle, "success": True})
                except Exception as e:
                    logger.error(f"Error drawing polyline {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(polylines_data),
                    "created": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "draw_texts")
    def draw_texts(
        ctx: Context,
        texts: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Add multiple text labels in a single operation.

        Args:
            texts: JSON array of text specifications.
                   Example: [{"position": "0,0", "text": "Label 1", "height": 2.5, "color": "red"}]
                   Fields: position (required), text (required), height (default: 2.5),
                           rotation (default: 0.0), color (default: "white"), layer (default: "0")
            cad_type: CAD application to use

        Returns:
            JSON result with created entity handles
        """
        try:
            texts_data = json.loads(texts) if isinstance(texts, str) else texts
            if not isinstance(texts_data, list):
                texts_data = [texts_data]

            results = []
            for i, text_spec in enumerate(texts_data):
                try:
                    pos = parse_coordinate(text_spec["position"])
                    text_content = text_spec["text"]
                    height = text_spec.get("height", 2.5)
                    rotation = text_spec.get("rotation", 0.0)
                    color = text_spec.get("color", "white")
                    layer = text_spec.get("layer", "0")

                    handle = get_current_adapter().draw_text(
                        pos, text_content, height, rotation, layer, color
                    )
                    results.append({"index": i, "handle": handle, "success": True})
                except Exception as e:
                    logger.error(f"Error drawing text {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(texts_data),
                    "created": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

    @cad_tool(mcp, "add_dimensions")
    def add_dimensions(
        ctx: Context,
        dimensions: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Add multiple dimension annotations in a single operation.

        Args:
            dimensions: JSON array of dimension specifications.
                        Example: [{"start": "0,0", "end": "10,10", "color": "white", "offset": 10.0}]
                        Fields: start (required), end (required), color (default: "white"),
                                layer (default: "0"), text (optional), offset (default: 10.0)
            cad_type: CAD application to use

        Returns:
            JSON result with created entity handles
        """
        try:
            dims_data = (
                json.loads(dimensions) if isinstance(dimensions, str) else dimensions
            )
            if not isinstance(dims_data, list):
                dims_data = [dims_data]

            results = []
            for i, dim_spec in enumerate(dims_data):
                try:
                    start_pt = parse_coordinate(dim_spec["start"])
                    end_pt = parse_coordinate(dim_spec["end"])
                    color = dim_spec.get("color", "white")
                    layer = dim_spec.get("layer", "0")
                    text = dim_spec.get("text")
                    offset = dim_spec.get("offset", 10.0)

                    handle = get_current_adapter().add_dimension(
                        start_pt, end_pt, None, text, layer, color, offset
                    )
                    results.append({"index": i, "handle": handle, "success": True})
                except Exception as e:
                    logger.error(f"Error adding dimension {i}: {e}")
                    results.append({"index": i, "success": False, "error": str(e)})

            return json.dumps(
                {
                    "total": len(dims_data),
                    "created": sum(1 for r in results if r["success"]),
                    "results": results,
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "results": [],
                },
                indent=2,
            )

    # ========== HELPER OPERATIONS (Specific Combinations) ==========

    @cad_tool(mcp, "draw_circle_and_line")
    def draw_circle_and_line(
        ctx: Context,
        line_start: str,
        line_end: str,
        circle_center: str,
        circle_radius: float,
        color: str = "white",
        layer: str = "0",
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw a circle and a line in a single operation.

        Args:
            line_start: Line start point as "x,y"
            line_end: Line end point as "x,y"
            circle_center: Circle center as "x,y"
            circle_radius: Circle radius
            color: Shape color
            layer: Layer to draw on
            cad_type: CAD application to use

        Returns:
            Status message with handles of created entities
        """
        line_handle = get_current_adapter().draw_line(
            parse_coordinate(line_start),
            parse_coordinate(line_end),
            layer,
            color,
        )
        circle_handle = get_current_adapter().draw_circle(
            parse_coordinate(circle_center),
            circle_radius,
            layer,
            color,
        )
        return f"Created line {line_handle} and circle {circle_handle}"
