"""
Drawing mixin for AutoCAD adapter.

Handles all drawing operations (lines, circles, arcs, polylines, text, dimensions, etc.).
"""

import logging
import math
from typing import List, Optional, TYPE_CHECKING, Any

from core import (
    CADInterface,
    InvalidParameterError,
    CADOperationError,
    Coordinate,
    Point,
)

logger = logging.getLogger(__name__)


class DrawingMixin:
    """Mixin for drawing operations."""

    if TYPE_CHECKING:

        def _validate_connection(self) -> None: ...

        def _get_document(self, operation: str = "operation") -> Any: ...

        def _to_variant_array(self, point: Point) -> Any: ...

        def _to_radians(self, degrees: float) -> float: ...

        def _points_to_variant_array(self, points: List[Point]) -> Any: ...

        def _apply_properties(
            self, entity: Any, layer: str, color: str | int, lineweight: int = 0
        ) -> None: ...

        def _track_entity(self, entity: Any, entity_type: str) -> None: ...

        def refresh_view(self) -> bool: ...

    def _finalize_entity(
        self,
        entity: Any,
        layer: str,
        color: str | int,
        lineweight: int = 0,
        entity_type: str = "entity",
        _skip_refresh: bool = False,
        log_msg: Optional[str] = None,
    ) -> str:
        """Helper to apply properties, track entity, refresh view, and return handle."""
        self._apply_properties(entity, layer, color, lineweight)
        self._track_entity(entity, entity_type)
        if not _skip_refresh:
            self.refresh_view()
        if log_msg:
            logger.debug(log_msg)
        return str(entity.Handle)

    def draw_line(
        self,
        start: Coordinate,
        end: Coordinate,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a line.

        Args:
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        document = self._get_document("draw_line")

        start_pt = CADInterface.normalize_coordinate(start)
        end_pt = CADInterface.normalize_coordinate(end)

        start_array = self._to_variant_array(start_pt)
        end_array = self._to_variant_array(end_pt)

        line = document.ModelSpace.AddLine(start_array, end_array)
        
        return self._finalize_entity(
            line, layer, color, lineweight, "line", _skip_refresh,
            f"Drew line from {start} to {end}"
        )

    def draw_circle(
        self,
        center: Coordinate,
        radius: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a circle.

        Args:
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        document = self._get_document("draw_circle")

        if radius <= 0:
            raise InvalidParameterError("radius", radius, "positive number")

        center_pt = CADInterface.normalize_coordinate(center)
        center_array = self._to_variant_array(center_pt)

        circle = document.ModelSpace.AddCircle(center_array, radius)
        
        return self._finalize_entity(
            circle, layer, color, lineweight, "circle", _skip_refresh,
            f"Drew circle at {center} with radius {radius}"
        )

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
        """Draw an arc.

        Args:
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        document = self._get_document("draw_arc")

        center_pt = CADInterface.normalize_coordinate(center)
        center_array = self._to_variant_array(center_pt)

        arc = document.ModelSpace.AddArc(
            center_array,
            radius,
            self._to_radians(start_angle),
            self._to_radians(end_angle),
        )
        
        return self._finalize_entity(
            arc, layer, color, lineweight, "arc", _skip_refresh,
            f"Drew arc at {center} from {start_angle}° to {end_angle}°"
        )

    def draw_rectangle(
        self,
        corner1: Coordinate,
        corner2: Coordinate,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a rectangle from two corners.

        Args:
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        self._validate_connection()
        pt1 = CADInterface.normalize_coordinate(corner1)
        pt2 = CADInterface.normalize_coordinate(corner2)

        # Create rectangle corners
        points: List[Coordinate] = [
            (pt1[0], pt1[1], pt1[2]),
            (pt2[0], pt1[1], pt1[2]),
            (pt2[0], pt2[1], pt2[2]),
            (pt1[0], pt2[1], pt2[2]),
            (pt1[0], pt1[1], pt1[2]),  # Close
        ]

        # Use polyline for rectangle
        return self.draw_polyline(
            points,
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
        """Draw a polyline through points.

        Args:
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        document = self._get_document("draw_polyline")

        if len(points) < 2:
            raise InvalidParameterError("points", points, "at least 2 points")

        # Convert to 3D points and flatten to variant array
        normalized_points = [CADInterface.normalize_coordinate(p) for p in points]
        variant_points = self._points_to_variant_array(normalized_points)

        polyline = document.ModelSpace.AddPolyline(variant_points)

        if closed:
            polyline.Closed = True

        return self._finalize_entity(
            polyline, layer, color, lineweight, "polyline", _skip_refresh,
            f"Drew polyline with {len(points)} points"
        )

    def draw_ellipse(
        self,
        center: Coordinate,
        major_axis_end: Coordinate,
        minor_axis_ratio: float,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw an ellipse."""
        document = self._get_document("draw_ellipse")

        center_pt = CADInterface.normalize_coordinate(center)
        major_end = CADInterface.normalize_coordinate(major_axis_end)

        center_array = self._to_variant_array(center_pt)
        major_array = self._to_variant_array(major_end)

        ellipse = document.ModelSpace.AddEllipse(
            center_array, major_array, minor_axis_ratio
        )
        
        return self._finalize_entity(
            ellipse, layer, color, lineweight, "ellipse", False, # Always refresh for ellipse in original code, but cleaner to pass _skip_refresh if we update signature. original didn't have _skip_refresh
            f"Drew ellipse at {center}"
        )

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
        """Add text to drawing.

        Args:
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        document = self._get_document("draw_text")

        pos = CADInterface.normalize_coordinate(position)
        pos_array = self._to_variant_array(pos)

        text_obj = document.ModelSpace.AddText(text, pos_array, height)
        text_obj.Rotation = self._to_radians(rotation)

        return self._finalize_entity(
            text_obj, layer, color, 0, "text", _skip_refresh,
            f"Added text '{text}' at {position}"
        )

    def draw_hatch(
        self,
        boundary_points: List[Coordinate],
        pattern: str = "SOLID",
        scale: float = 1.0,
        angle: float = 0.0,
        color: str | int = "white",
        layer: str = "0",
    ) -> str:
        """Create a hatch (filled area)."""
        document = self._get_document("draw_hatch")

        # Create boundary polyline (invisible)
        boundary_polyline = document.ModelSpace.AddPolyline(
            self._points_to_variant_array(
                [CADInterface.normalize_coordinate(p) for p in boundary_points]
            )
        )
        boundary_polyline.Closed = True

        # Create hatch
        hatch = document.ModelSpace.AddHatch(
            0, pattern, True
        )  # 0 = Normal, True = Associative
        hatch.AppendOuterLoop([boundary_polyline])
        hatch.Evaluate()

        return self._finalize_entity(
            hatch, layer, color, 0, "hatch", False, # hatch always refreshed in original
            f"Created hatch with pattern {pattern}"
        )

    def add_dimension(
        self,
        start: Coordinate,
        end: Coordinate,
        text_position: Optional[Coordinate] = None,
        text: Optional[str] = None,
        layer: str = "0",
        color: str | int = "white",
        offset: float = 10.0,
        _skip_refresh: bool = False,
    ) -> str:
        """Add a dimension annotation with optional offset from the edge.

        Args:
            start: Start point of the dimension
            end: End point of the dimension
            text_position: Position for dimension text (optional)
            text: Custom dimension text (optional)
            layer: Layer name
            color: Color name or index
            offset: Distance to offset the dimension line from the edge (default: 10.0)
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            Entity handle of the created dimension
        """
        document = self._get_document("add_dimension")

        start_pt = CADInterface.normalize_coordinate(start)
        end_pt = CADInterface.normalize_coordinate(end)

        start_array = self._to_variant_array(start_pt)
        end_array = self._to_variant_array(end_pt)

        # Calculate perpendicular offset point for the dimension line
        dx = end_pt[0] - start_pt[0]
        dy = end_pt[1] - start_pt[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length > 0:
            # Perpendicular to (dx, dy) is (-dy, dx)
            perp_x = -dy / length
            perp_y = dx / length

            # Apply offset in perpendicular direction
            offset_x = perp_x * offset
            offset_y = perp_y * offset

            # Midpoint of the dimension line, offset perpendicularly
            mid_x = (start_pt[0] + end_pt[0]) / 2 + offset_x
            mid_y = (start_pt[1] + end_pt[1]) / 2 + offset_y
            mid_z = start_pt[2]

            dim_position = self._to_variant_array((mid_x, mid_y, mid_z))
        else:
            # If start and end are the same, use default offset
            dim_position = self._to_variant_array(
                (start_pt[0] + offset, start_pt[1], start_pt[2])
            )

        # Use aligned dimension with offset position
        dim = document.ModelSpace.AddDimAligned(start_array, end_array, dim_position)

        if text:
            dim.TextOverride = text

        return self._finalize_entity(
            dim, layer, color, 0, "dimension", _skip_refresh,
            f"Added dimension from {start} to {end} with offset {offset}"
        )

    def draw_spline(
        self,
        points: List[Coordinate],
        closed: bool = False,
        degree: int = 3,
        layer: str = "0",
        color: str | int = "white",
        lineweight: int = 0,
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a spline curve through points."""
        document = self._get_document("draw_spline")

        if len(points) < 2:
            raise InvalidParameterError("points", points, "at least 2 points")

        if not (1 <= degree <= 3):
            raise InvalidParameterError("degree", degree, "value between 1 and 3")

        # Convert to 3D points and flatten to variant array
        normalized_points = [CADInterface.normalize_coordinate(p) for p in points]
        variant_points = self._points_to_variant_array(normalized_points)

        # Create spline
        # AutoCAD expects: points array, start tangent, end tangent, degree
        # For a natural spline, we can pass empty tangents
        spline = document.ModelSpace.AddSpline(variant_points, None, None, degree)

        if closed:
            spline.Closed = True

        return self._finalize_entity(
            spline, layer, color, lineweight, "spline", _skip_refresh,
            f"Drew spline with {len(points)} points (degree={degree}, closed={closed})"
        )

    def draw_leader(
        self,
        points: List[Coordinate],
        text: Optional[str] = None,
        text_height: float = 2.5,
        layer: str = "0",
        color: str | int = "white",
        leader_type: str = "line_with_arrow",
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a leader (dimension leader line) with optional text annotation.

        NOTE: Internally uses MLeader for proper text rendering.
        A single leader line is created as a multi-leader with one arrow.

        Args:
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        if len(points) < 2:
            raise InvalidParameterError("points", points, "at least 2 points")

        # Map leader type names to arrow styles for MLeader
        # Note: MLeader uses arrow head symbols instead of type constants
        leader_type_to_arrow = {
            "line_no_arrow": "_NONE",
            "line_with_arrow": "_ARROW",
            "spline_with_arrow": "_ARROW",  # MLeader uses arrow style, not spline type
            "spline_no_arrow": "_NONE",
        }

        leader_type_lower = leader_type.lower()
        if leader_type_lower not in leader_type_to_arrow:
            raise InvalidParameterError(
                "leader_type",
                leader_type,
                f"one of: {', '.join(leader_type_to_arrow.keys())}",
            )

        arrow_style = leader_type_to_arrow[leader_type_lower]

        # Normalize points - first point is base, rest are the leader line
        normalized_points = [CADInterface.normalize_coordinate(p) for p in points]

        # For MLeader, base_point is where text goes (usually first point)
        # and leader_groups contains the line points
        base_point = normalized_points[0]
        leader_group = normalized_points  # Include all points in the leader line

        # Use draw_mleader internally with a single group
        # This ensures text is always rendered correctly
        return self.draw_mleader(
            base_point=base_point,
            leader_groups=[leader_group],
            text=text,
            text_height=text_height,
            layer=layer,
            color=color,
            arrow_style=arrow_style,
            _skip_refresh=_skip_refresh,
        )

    def draw_mleader(
        self,
        base_point: Coordinate,
        leader_groups: List[List[Coordinate]],
        text: Optional[str] = None,
        text_height: float = 2.5,
        layer: str = "0",
        color: str | int = "white",
        arrow_style: str = "_ARROW",
        _skip_refresh: bool = False,
    ) -> str:
        """Draw a multi-leader with multiple arrow lines.

        Args:
            base_point: Base point for annotation (Text Position)
            leader_groups: List of point lists, each defining one leader line.
                          Order: [ArrowHead, ..., TextPosition]
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)
        """
        logger.info(f"draw_mleader called with {len(leader_groups)} groups: {leader_groups}")

        document = self._get_document("draw_mleader")

        if not leader_groups:
            raise InvalidParameterError("leader_groups", leader_groups, "at least 1 group")

        for i, group in enumerate(leader_groups):
            if len(group) < 2:
                raise InvalidParameterError(
                    f"leader_groups[{i}]", group, "at least 2 points per group"
                )

        # Normalize base point to 3D
        base_pt = CADInterface.normalize_coordinate(base_point)
        base_array = self._to_variant_array(base_pt)

        try:
            # Create MLeader with base point
            # Note: ZWCAD/AutoCAD AddMLeader often takes (PointsArray, Index)
            # We use just the base point for initial creation, or the first group's points?
            # AddMLeader documentation says: Adds an MLeader object to the drawing.
            # RetVal = object.AddMLeader(pointsArray, leaderIndex)
            
            # Use the first group's points for the initial creation if possible, 
            # but AddMLeader expects a points array. 
            # If we pass just base_array, it might fail if it expects more points.
            # However, typical usage is creating with the full point list of the first leader.
            first_group = leader_groups[0]
            normalized_first_group = [CADInterface.normalize_coordinate(p) for p in first_group]
            variant_first_group = self._points_to_variant_array(normalized_first_group)
            
            # Create the MLeader
            # index 0 is usually the leader index to add to
            # Try creating MLeader with index 0
            # Some CAD versions might need different arguments, but standard is (points, index)
            try:
                result = document.ModelSpace.AddMLeader(variant_first_group, 0)
            except Exception as e:
                 logger.debug(f"AddMLeader(pts, 0) failed, trying AddMLeader(pts): {e}")
                 result = document.ModelSpace.AddMLeader(variant_first_group)

            # Handle tuple return
            mleader = result[0] if isinstance(result, tuple) else result

            # Helper to safely set properties
            def set_prop(obj, prop, val):
                try:
                    setattr(obj, prop, val)
                except Exception as ex:
                    logger.warning(f"Could not set {prop}={val}: {ex}")

            # Set Content (Text)
            if text:
                # ContentType: 2 = MText
                set_prop(mleader, "ContentType", 2)
                
                # Apply Arial Font formatting using MText codes
                formatted_text = r"{\fArial|b0|i0|c0|p34;" + text + "}"
                set_prop(mleader, "TextString", formatted_text)
                
                # Attempt to set text height if possible
                try:
                    # Some MLeaders expose TextHeight directly
                    mleader.TextHeight = text_height
                except:
                    # Otherwise try via MText attribute if exposed
                    try:
                        mleader.MText.Height = text_height
                    except:
                        pass
            else:
                set_prop(mleader, "ContentType", 0) # None

            # Set Arrow Style
            try:
                mleader.ArrowHeadSymbol = arrow_style
            except Exception as e:
                logger.warning(f"Could not set arrow style '{arrow_style}': {e}")

            # Force update to ensure geometry is calculated
            try:
                mleader.Update()
            except: pass

            # Handle additional leader groups using _MLEADEREDIT command
            if len(leader_groups) > 1:
                try:
                    # Force Regen to ensure handle is recognized
                    try:
                        self.document.Regen(1) # acAllViewports = 1
                    except: pass

                    # Construct the command string
                    # Syntax: _AIMLEADEREDITADD (handent "HANDLE") PT1 PT2 ... \x1B
                    cmd_parts = [f'_AIMLEADEREDITADD (handent "{mleader.Handle}")']
                    
                    for group in leader_groups[1:]:
                        normalized_group = [CADInterface.normalize_coordinate(p) for p in group]
                        
                        # Arrow point is the FIRST point in the group (from input)
                        # We need to format it as "X,Y,Z"
                        arrow_pt = normalized_group[0] 
                        pt_str = f"{arrow_pt[0]},{arrow_pt[1]},{arrow_pt[2]}"
                        
                        cmd_parts.append(pt_str)
                    
                    # Terminate command with ESC
                    cmd_parts.append('\x1B')
                    
                    full_cmd = " ".join(cmd_parts)
                    logger.info(f"Adding {len(leader_groups)-1} extra arrows via command: {full_cmd}")
                    
                    self.document.SendCommand(full_cmd)
                    
                except Exception as e:
                    logger.error(f"Failed to add extra arrows via command: {e}")

            # Match color (moved here to ensure it applies to the whole entity)
            if isinstance(color, int):
                try:
                    # Try direct assignment first (ZWCAD simple property)
                    mleader.Color = color
                except:
                    try:
                        # Try via ColorIndex property (AutoCAD/Complex property)
                        mleader.Color.ColorIndex = color
                    except Exception as e:
                        logger.warning(f"Could not set MLeader color: {e}")

            # Force update
            try:
                mleader.Update()
            except: pass

            return self._finalize_entity(
                mleader, layer, color, 0, "mleader", _skip_refresh,
                f"Drew multi-leader with {len(leader_groups)} lines (arrow_style={arrow_style}, text={text})"
            )

        except Exception as e:
            logger.error(f"Failed to create MLeader: {e}")
            raise CADOperationError("draw_mleader", f"Failed to create MLeader: {e}")


