"""
Drawing tools for creating geometric entities.

Provides tools for:
- Drawing lines, circles, arcs
- Drawing rectangles, polylines, ellipses
- Adding text and dimensions
"""

import logging
from typing import Optional

from mcp.server.fastmcp import Context

from core import InvalidParameterError
from mcp_tools.decorators import cad_tool
from mcp_tools.helpers import parse_coordinate
from mcp_tools.decorators import get_current_adapter

logger = logging.getLogger(__name__)


def register_drawing_tools(mcp):
    """Register drawing tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @cad_tool(mcp, "draw_line")
    def draw_line(
        ctx: Context,
        start: str,
        end: str,
        color: str = "white",
        layer: str = "0",
        lineweight: int = 0,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw a line between two points.

        Args:
            start: Start point as "x,y" or "x,y,z"
            end: End point as "x,y" or "x,y,z"
            color: Line color
            layer: Layer to draw on
            lineweight: Line weight
            cad_type: CAD application to use

        Returns:
            Entity handle/ID of the created line
        """
        start_pt = parse_coordinate(start)
        end_pt = parse_coordinate(end)
        return get_current_adapter().draw_line(
            start_pt, end_pt, layer, color, lineweight
        )

    @cad_tool(mcp, "draw_circle")
    def draw_circle(
        ctx: Context,
        center: str,
        radius: float,
        color: str = "white",
        layer: str = "0",
        lineweight: int = 0,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw a circle.

        Args:
            center: Center point as "x,y" or "x,y,z"
            radius: Circle radius
            color: Circle color
            layer: Layer to draw on
            lineweight: Line weight
            cad_type: CAD application to use

        Returns:
            Entity handle/ID of the created circle
        """
        if radius <= 0:
            raise InvalidParameterError("radius", radius, "positive number")

        center_pt = parse_coordinate(center)
        return get_current_adapter().draw_circle(
            center_pt, radius, layer, color, lineweight
        )

    @cad_tool(mcp, "draw_arc")
    def draw_arc(
        ctx: Context,
        center: str,
        radius: float,
        start_angle: float,
        end_angle: float,
        color: str = "white",
        layer: str = "0",
        lineweight: int = 0,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw an arc.

        Args:
            center: Center point as "x,y" or "x,y,z"
            radius: Arc radius
            start_angle: Start angle in degrees
            end_angle: End angle in degrees
            color: Arc color
            layer: Layer to draw on
            lineweight: Line weight
            cad_type: CAD application to use

        Returns:
            Entity handle/ID of the created arc
        """
        center_pt = parse_coordinate(center)
        return get_current_adapter().draw_arc(
            center_pt, radius, start_angle, end_angle, layer, color, lineweight
        )

    @cad_tool(mcp, "draw_rectangle")
    def draw_rectangle(
        ctx: Context,
        corner1: str,
        corner2: str,
        color: str = "white",
        layer: str = "0",
        lineweight: int = 0,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw a rectangle from two opposite corners.

        Args:
            corner1: First corner as "x,y" or "x,y,z"
            corner2: Opposite corner as "x,y" or "x,y,z"
            color: Rectangle color
            layer: Layer to draw on
            lineweight: Line weight
            cad_type: CAD application to use

        Returns:
            Entity handle/ID of the created rectangle
        """
        pt1 = parse_coordinate(corner1)
        pt2 = parse_coordinate(corner2)
        return get_current_adapter().draw_rectangle(pt1, pt2, layer, color, lineweight)

    @cad_tool(mcp, "draw_polyline")
    def draw_polyline(
        ctx: Context,
        points: str,
        closed: bool = False,
        color: str = "white",
        layer: str = "0",
        lineweight: int = 0,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Draw a polyline through multiple points.

        Args:
            points: Points as "x1,y1|x2,y2|x3,y3|..." (pipe-separated)
            closed: Whether to close the polyline
            color: Polyline color
            layer: Layer to draw on
            lineweight: Line weight
            cad_type: CAD application to use

        Returns:
            Entity handle/ID of the created polyline
        """
        point_list = [parse_coordinate(p.strip()) for p in points.split("|")]

        if len(point_list) < 2:
            raise InvalidParameterError("points", points, "at least 2 points")

        return get_current_adapter().draw_polyline(
            point_list, closed, layer, color, lineweight
        )

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

    @cad_tool(mcp, "draw_text")
    def draw_text(
        ctx: Context,
        position: str,
        text: str,
        height: float = 2.5,
        rotation: float = 0.0,
        color: str = "white",
        layer: str = "0",
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Add text to the drawing.

        Args:
            position: Text position as "x,y" or "x,y,z"
            text: Text content
            height: Text height
            rotation: Rotation angle in degrees
            color: Text color
            layer: Layer to draw on
            cad_type: CAD application to use

        Returns:
            Entity handle/ID of the created text
        """
        pos = parse_coordinate(position)
        return get_current_adapter().draw_text(
            pos, text, height, rotation, layer, color
        )

    @cad_tool(mcp, "add_dimension")
    def add_dimension(
        ctx: Context,
        start: str,
        end: str,
        color: str = "white",
        layer: str = "0",
        text: Optional[str] = None,
        offset: float = 10.0,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Add a dimension annotation.

        Args:
            start: Start point as "x,y" or "x,y,z"
            end: End point as "x,y" or "x,y,z"
            color: Dimension color
            layer: Layer to draw on
            text: Optional custom text
            offset: Distance to offset the dimension line from the edge (default: 10.0)
            cad_type: CAD application to use

        Returns:
            Entity handle/ID of the created dimension
        """
        start_pt = parse_coordinate(start)
        end_pt = parse_coordinate(end)
        return get_current_adapter().add_dimension(
            start_pt, end_pt, None, text, layer, color, offset
        )
