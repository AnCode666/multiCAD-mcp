"""
Manipulation mixin for AutoCAD adapter.

Handles entity manipulation operations (move, rotate, scale, copy, paste, arrays).
"""

import logging
import time
from typing import List, Optional, Any, TYPE_CHECKING

from mcp_tools.constants import (
    SS_COPY,
    SELECTION_SET_IMPLIED,
    CLIPBOARD_DELAY,
    CLIPBOARD_STABILITY_DELAY,
)

logger = logging.getLogger(__name__)


class ManipulationMixin:
    """Mixin for entity manipulation operations."""

    if TYPE_CHECKING:
        # Tell type checker this mixin is used with CADAdapterProtocol
        from typing import Any
        from core import Point, Coordinate

        def _validate_connection(self) -> None: ...
        def _get_document(self, operation: str = "operation") -> Any: ...
        def _get_application(self, operation: str = "operation") -> Any: ...
        def _to_variant_array(self, point: Point) -> Any: ...
        def _to_radians(self, degrees: float) -> float: ...
        def _delete_selection_set(self, document: Any, name: str) -> None: ...
        def refresh_view(self) -> bool: ...
        def _get_color_index(self, color_name: str) -> int: ...

    def move_entities(
        self, handles: List[str], offset_x: float, offset_y: float
    ) -> bool:
        """Translate entities by the given X/Y offset via COM Move().

        Args:
            handles: List of entity handle strings to move.
            offset_x: Displacement in the X direction (drawing units).
            offset_y: Displacement in the Y direction (drawing units).

        Returns:
            True if at least one entity was moved successfully, False otherwise.
        """
        try:
            self._validate_connection()
            document = self._get_document("move_entities")

            moved_count = 0
            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)

                    from_point = self._to_variant_array((0.0, 0.0, 0.0))
                    to_point = self._to_variant_array((offset_x, offset_y, 0.0))

                    entity.Move(from_point, to_point)
                    moved_count += 1
                    logger.debug(f"Moved entity {handle} by ({offset_x}, {offset_y})")

                except Exception as e:
                    logger.warning(f"Failed to move entity {handle}: {e}")

            logger.info(f"Moved {moved_count}/{len(handles)} entities")
            self.refresh_view()
            return moved_count > 0
        except Exception as e:
            logger.error(f"Failed to move entities: {e}")
            return False

    def rotate_entities(
        self, handles: List[str], center_x: float, center_y: float, angle: float
    ) -> bool:
        """Rotate entities around a specified centre point via COM Rotate().

        Args:
            handles: List of entity handle strings to rotate.
            center_x: X coordinate of the rotation centre (drawing units).
            center_y: Y coordinate of the rotation centre (drawing units).
            angle: Rotation angle in degrees (counter-clockwise positive).

        Returns:
            True if at least one entity was rotated successfully, False otherwise.
        """
        try:
            self._validate_connection()
            document = self._get_document("rotate_entities")

            rotated_count = 0
            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)
                    center_point = self._to_variant_array((center_x, center_y, 0.0))
                    radians = self._to_radians(angle)

                    entity.Rotate(center_point, radians)
                    rotated_count += 1
                    logger.debug(f"Rotated entity {handle} by {angle}°")

                except Exception as e:
                    logger.warning(f"Failed to rotate entity {handle}: {e}")

            logger.info(f"Rotated {rotated_count}/{len(handles)} entities")
            self.refresh_view()
            return rotated_count > 0
        except Exception as e:
            logger.error(f"Failed to rotate entities: {e}")
            return False

    def scale_entities(
        self, handles: List[str], center_x: float, center_y: float, scale_factor: float
    ) -> bool:
        """Scale entities uniformly around a specified centre point via COM ScaleEntity().

        Args:
            handles: List of entity handle strings to scale.
            center_x: X coordinate of the scale base point (drawing units).
            center_y: Y coordinate of the scale base point (drawing units).
            scale_factor: Uniform scale factor (e.g. 2.0 doubles the size).

        Returns:
            True if at least one entity was scaled successfully, False otherwise.
        """
        try:
            self._validate_connection()
            document = self._get_document("scale_entities")

            scaled_count = 0
            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)
                    center_point = self._to_variant_array((center_x, center_y, 0.0))
                    entity.ScaleEntity(center_point, scale_factor)
                    scaled_count += 1
                    logger.debug(f"Scaled entity {handle} by {scale_factor}")

                except Exception as e:
                    logger.warning(f"Failed to scale entity {handle}: {e}")

            logger.info(f"Scaled {scaled_count}/{len(handles)} entities")
            self.refresh_view()
            return scaled_count > 0
        except Exception as e:
            logger.error(f"Failed to scale entities: {e}")
            return False

    def copy_entities(self, handles: List[str]) -> bool:
        """Copy the specified entities to the CAD clipboard via the COPY SendCommand.

        Args:
            handles: List of entity handle strings to copy.

        Returns:
            True if the copy command was issued successfully, False otherwise.
        """
        try:
            self._validate_connection()
            document = self._get_document("copy_entities")
            app = self._get_application("copy_entities")

            # Create a selection set with entities to copy
            try:
                self._delete_selection_set(document, SS_COPY)
            except Exception:
                pass

            ss = document.SelectionSets.Add(SS_COPY)
            try:
                for handle in handles:
                    entity = document.HandleToObject(handle)
                    ss.Select(SELECTION_SET_IMPLIED, None, entity)

                # Use SendCommand to execute COPY command
                app.ActiveDocument.SendCommand("_copy\n")
                time.sleep(CLIPBOARD_DELAY / 1000.0)

                logger.info(f"Copied {len(handles)} entities to clipboard")
                return True
            finally:
                self._delete_selection_set(document, SS_COPY)
        except Exception as e:
            logger.error(f"Failed to copy entities: {e}")
            return False

    def paste_entities(self, base_point_x: float, base_point_y: float) -> List[str]:
        """Paste previously copied entities from the CAD clipboard via SendCommand.

        Args:
            base_point_x: X coordinate of the paste base point (drawing units).
            base_point_y: Y coordinate of the paste base point (drawing units).

        Returns:
            List of new entity handle strings. Currently always returns an empty list
            because pasted entity handles cannot be reliably tracked via COM.
        """
        try:
            self._validate_connection()
            document = self._get_document("paste_entities")
            app = self._get_application("paste_entities")

            # Get count before paste
            count_before = sum(1 for _ in document.ModelSpace)

            # Paste using SendCommand (more reliable)
            app.ActiveDocument.SendCommand("^V\n")
            time.sleep(CLIPBOARD_STABILITY_DELAY / 1000.0)

            # Get new entities (simplified approach)
            count_after = sum(1 for _ in document.ModelSpace)
            logger.info(f"Pasted {count_after - count_before} entities")

            return []  # Return empty list as we can't reliably track new entities
        except Exception as e:
            logger.error(f"Failed to paste entities: {e}")
            return []

    def change_entity_color(self, handles: List[str], color: str | int) -> bool:
        """Change the color of the specified entities via COM.

        Args:
            handles: List of entity handle strings to recolor.
            color: New color as a name (e.g. ``"red"``) or ACI index (1–255).

        Returns:
            True if at least one entity's color was changed, False otherwise.
        """
        try:
            self._validate_connection()
            document = self._get_document("change_entity_color")

            if isinstance(color, str):
                color = self._get_color_index(color)

            changed_count = 0
            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)
                    entity.Color = color
                    changed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to change color of entity {handle}: {e}")

            logger.info(f"Changed color of {changed_count}/{len(handles)} entities")
            self.refresh_view()
            return changed_count > 0
        except Exception as e:
            logger.error(f"Failed to change entity color: {e}")
            return False

    def change_entity_layer(self, handles: List[str], layer_name: str) -> bool:
        """Move the specified entities to a different layer via COM.

        Creates the target layer if it does not already exist.

        Args:
            handles: List of entity handle strings to reassign.
            layer_name: Name of the destination layer.

        Returns:
            True if at least one entity's layer was changed, False otherwise.
        """
        try:
            self._validate_connection()
            document = self._get_document("change_entity_layer")

            # Ensure layer exists
            try:
                document.Layers.Item(layer_name)
            except Exception:
                logger.warning(f"Layer '{layer_name}' not found, creating it")
                document.Layers.Add(layer_name)

            changed_count = 0
            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)
                    entity.Layer = layer_name
                    changed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to change layer of entity {handle}: {e}")

            logger.info(
                f"Moved {changed_count}/{len(handles)} entities to layer '{layer_name}'"
            )
            self.refresh_view()
            return changed_count > 0
        except Exception as e:
            logger.error(f"Failed to change entity layer: {e}")
            return False

    def create_rectangular_array(
        self,
        handles: List[str],
        rows: int,
        columns: int,
        row_spacing: float,
        column_spacing: float,
    ) -> List[str]:
        """Create a rectangular grid of copies of the specified entities.

        The original entities remain at row 0, column 0. Copies are created for
        all other grid positions.

        Args:
            handles: List of entity handle strings to array.
            rows: Number of rows in the grid.
            columns: Number of columns in the grid.
            row_spacing: Distance between rows (drawing units, Y direction).
            column_spacing: Distance between columns (drawing units, X direction).

        Returns:
            List of handle strings for the newly created copy entities.
        """
        try:
            self._validate_connection()
            document = self._get_document("create_rectangular_array")

            new_handles = []
            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)

                    # Create copies in a grid pattern
                    for row in range(rows):
                        for col in range(columns):
                            # Skip the original position (0, 0)
                            if row == 0 and col == 0:
                                continue

                            # Calculate offset for this position
                            offset_x = col * column_spacing
                            offset_y = row * row_spacing

                            # Copy the entity
                            copied_entity = entity.Copy()

                            # Move to the correct position
                            from_point = self._to_variant_array((0.0, 0.0, 0.0))
                            to_point = self._to_variant_array((offset_x, offset_y, 0.0))
                            copied_entity.Move(from_point, to_point)

                            # Get handle of copied entity
                            new_handles.append(copied_entity.Handle)

                            logger.debug(
                                f"Created array copy at row {row}, col {col} for entity {handle}"
                            )

                except Exception as e:
                    logger.warning(
                        f"Failed to create array copies for entity {handle}: {e}"
                    )

            logger.info(
                f"Created rectangular array: {len(new_handles)} copies "
                f"({rows}x{columns} grid)"
            )
            self.refresh_view()
            return new_handles
        except Exception as e:
            logger.error(f"Failed to create rectangular array: {e}")
            return []

    def create_polar_array(
        self,
        handles: List[str],
        center_x: float,
        center_y: float,
        count: int,
        angle_to_fill: float = 360.0,
        rotate_items: bool = True,
    ) -> List[str]:
        """Create a circular array of copies of the specified entities around a centre.

        The original entities remain at their position (angle 0). Copies are placed
        at evenly-spaced angular intervals within ``angle_to_fill``.

        Args:
            handles: List of entity handle strings to array.
            center_x: X coordinate of the array centre (drawing units).
            center_y: Y coordinate of the array centre (drawing units).
            count: Total number of items in the array (including the original).
            angle_to_fill: Total arc angle to distribute copies over (default: 360.0°).
            rotate_items: When True, each copy is also rotated to face outward.

        Returns:
            List of handle strings for the newly created copy entities.
        """
        try:
            self._validate_connection()
            document = self._get_document("create_polar_array")

            new_handles = []
            center_point = self._to_variant_array((center_x, center_y, 0.0))

            # Calculate angle increment
            angle_increment = angle_to_fill / count

            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)

                    # Create copies at each angle
                    for i in range(1, count):  # Skip first (original position)
                        angle = i * angle_increment

                        # Copy the entity
                        copied_entity = entity.Copy()

                        # Rotate around center point
                        radians = self._to_radians(angle)
                        copied_entity.Rotate(center_point, radians)

                        # Optionally rotate the items themselves
                        if not rotate_items:
                            # Rotate back to original orientation
                            copied_entity.Rotate(center_point, -radians)

                        # Get handle of copied entity
                        new_handles.append(copied_entity.Handle)

                        logger.debug(
                            f"Created polar array copy at {angle}° for entity {handle}"
                        )

                except Exception as e:
                    logger.warning(
                        f"Failed to create polar array copies for entity {handle}: {e}"
                    )

            logger.info(
                f"Created polar array: {len(new_handles)} copies "
                f"({count} items, {angle_to_fill}°)"
            )
            self.refresh_view()
            return new_handles
        except Exception as e:
            logger.error(f"Failed to create polar array: {e}")
            return []

    def create_path_array(
        self,
        handles: List[str],
        path_points: List,
        count: int,
        align_items: bool = True,
    ) -> List[str]:
        """Create copies of entities distributed evenly along a polyline path.

        The original entities remain at their position. Copies are interpolated
        along the path defined by ``path_points``.

        Args:
            handles: List of entity handle strings to array.
            path_points: Ordered list of 2-D or 3-D points defining the path.
            count: Total number of items in the array (including the original).
            align_items: When True, each copy is rotated to align with the local
                path direction.

        Returns:
            List of handle strings for the newly created copy entities.
        """
        try:
            self._validate_connection()
            document = self._get_document("create_path_array")

            new_handles = []

            # Calculate total path length and segment lengths
            import math

            def distance(p1, p2):
                """Calculate distance between two points."""
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                return math.sqrt(dx * dx + dy * dy)

            def angle_between(p1, p2):
                """Calculate angle in radians from p1 to p2."""
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                return math.atan2(dy, dx)

            # Calculate cumulative distances along path
            cumulative_distances = [0.0]
            for i in range(len(path_points) - 1):
                p1 = path_points[i]
                p2 = path_points[i + 1]
                cumulative_distances.append(cumulative_distances[-1] + distance(p1, p2))

            total_length = cumulative_distances[-1]
            spacing = total_length / (count - 1) if count > 1 else 0

            for handle in handles:
                try:
                    entity = document.HandleToObject(handle)

                    # Create copies along the path
                    for i in range(1, count):  # Skip first (original position)
                        target_distance = i * spacing

                        # Find which segment this point is on
                        segment_idx = 0
                        for j in range(len(cumulative_distances) - 1):
                            if cumulative_distances[j + 1] >= target_distance:
                                segment_idx = j
                                break

                        # Interpolate position within segment
                        p1 = path_points[segment_idx]
                        p2 = path_points[segment_idx + 1]

                        segment_start = cumulative_distances[segment_idx]
                        segment_length = (
                            cumulative_distances[segment_idx + 1] - segment_start
                        )
                        t = (
                            (target_distance - segment_start) / segment_length
                            if segment_length > 0
                            else 0
                        )

                        # Calculate interpolated position
                        x = p1[0] + t * (p2[0] - p1[0])
                        y = p1[1] + t * (p2[1] - p1[1])

                        # Copy the entity
                        copied_entity = entity.Copy()

                        # Get original position (approximate as 0,0 for offset calculation)
                        from_point = self._to_variant_array((0.0, 0.0, 0.0))
                        to_point = self._to_variant_array((x, y, 0.0))
                        copied_entity.Move(from_point, to_point)

                        # Optionally align to path direction
                        if align_items:
                            angle = angle_between(p1, p2)
                            center = self._to_variant_array((x, y, 0.0))
                            copied_entity.Rotate(center, angle)

                        # Get handle of copied entity
                        new_handles.append(copied_entity.Handle)

                        logger.debug(
                            f"Created path array copy at ({x:.2f}, {y:.2f}) for entity {handle}"
                        )

                except Exception as e:
                    logger.warning(
                        f"Failed to create path array copies for entity {handle}: {e}"
                    )

            logger.info(f"Created path array: {len(new_handles)} copies along path")
            self.refresh_view()
            return new_handles
        except Exception as e:
            logger.error(f"Failed to create path array: {e}")
            return []

    def offset_entity(
        self, handle: str, distance: float, side_point: Optional[Any] = None
    ) -> List[str]:
        """Offset a line, arc, circle, or polyline by distance via COM."""
        self._validate_connection()
        document = self._get_document("offset_entity")
        entity = document.HandleToObject(handle)
        new_handles = []
        try:
            res = entity.Offset(distance)
            if res:
                if isinstance(res, (tuple, list)):
                    for e in res:
                        new_handles.append(str(e.Handle))
                else:
                    new_handles.append(str(res.Handle))
            self.refresh_view()
            return new_handles
        except Exception as e:
            logger.error(f"Failed to offset entity {handle}: {e}")
            return []

    def fillet_entities(
        self, handle1: str, handle2: str, radius: float = 0.0
    ) -> Optional[str]:
        """Fillet two entities with radius via COM."""
        self._validate_connection()
        document = self._get_document("fillet_entities")
        try:
            cmd = f"_FILLET R {radius} (handent \"{handle1}\") (handent \"{handle2}\")\n"
            document.SendCommand(cmd)
            self.refresh_view()
            return handle1
        except Exception as e:
            logger.error(f"Failed to fillet entities {handle1}, {handle2}: {e}")
            return None

    def chamfer_entities(
        self, handle1: str, handle2: str, dist1: float = 0.0, dist2: float = 0.0
    ) -> Optional[str]:
        """Chamfer two entities with setback distances via COM."""
        self._validate_connection()
        document = self._get_document("chamfer_entities")
        try:
            cmd = f"_CHAMFER D {dist1} {dist2} (handent \"{handle1}\") (handent \"{handle2}\")\n"
            document.SendCommand(cmd)
            self.refresh_view()
            return handle1
        except Exception as e:
            logger.error(f"Failed to chamfer entities {handle1}, {handle2}: {e}")
            return None

    def explode_entity(self, handle: str) -> List[str]:
        """Explode a composite entity (block or polyline) into primitives via COM."""
        self._validate_connection()
        document = self._get_document("explode_entity")
        entity = document.HandleToObject(handle)
        new_handles = []
        try:
            exploded = entity.Explode()
            if exploded:
                for e in exploded:
                    new_handles.append(str(e.Handle))
            self.refresh_view()
            return new_handles
        except Exception as e:
            logger.error(f"Failed to explode entity {handle}: {e}")
            return []

    def match_properties(self, source_handle: str, target_handles: List[str]) -> bool:
        """Copy layer, color, linetype, and lineweight from source to target entities via COM."""
        self._validate_connection()
        document = self._get_document("match_properties")
        source = document.HandleToObject(source_handle)
        src_layer = source.Layer
        src_color = source.Color
        src_linetype = source.Linetype
        src_weight = getattr(source, "Lineweight", 0)

        for th in target_handles:
            try:
                target = document.HandleToObject(th)
                target.Layer = src_layer
                target.Color = src_color
                target.Linetype = src_linetype
                if hasattr(target, "Lineweight"):
                    target.Lineweight = src_weight
            except Exception as e:
                logger.warning(f"Failed to match properties on {th}: {e}")
        self.refresh_view()
        return True

    def create_boundary(
        self, internal_point: Any, layer: str = "0"
    ) -> Optional[str]:
        """Detect closed boundary around internal point and create polyline via COM."""
        self._validate_connection()
        document = self._get_document("create_boundary")
        try:
            pt = (float(internal_point[0]), float(internal_point[1]))
            # Count entities before
            count_before = document.ModelSpace.Count
            document.SendCommand(f"_-BOUNDARY {pt[0]},{pt[1]} \n")
            self.refresh_view()
            if document.ModelSpace.Count > count_before:
                new_entity = document.ModelSpace.Item(document.ModelSpace.Count - 1)
                if layer and layer != "0":
                    new_entity.Layer = layer
                return str(new_entity.Handle)
            return None
        except Exception as e:
            logger.error(f"Failed to create boundary at {internal_point}: {e}")
            return None

    def join_entities(
        self, handles: List[str], tolerance: float = 0.01
    ) -> Optional[str]:
        """Join loose connected lines and arcs into a polyline via COM."""
        self._validate_connection()
        document = self._get_document("join_entities")
        if not handles or len(handles) < 2:
            return None
        try:
            count_before = document.ModelSpace.Count
            sel_lisp = " ".join([f'(handent "{h}")' for h in handles])
            document.SendCommand(f"_JOIN {sel_lisp} \n")
            self.refresh_view()
            # If joined into a single polyline, the first handle or newly created one is returned
            return handles[0]
        except Exception as e:
            logger.error(f"Failed to join entities {handles}: {e}")
            return None

    def trim_extend_entity(
        self, handle: str, boundary_handle: str, mode: str = "trim"
    ) -> bool:
        """Trim or extend a line against a boundary edge via COM."""
        self._validate_connection()
        document = self._get_document("trim_extend_entity")
        try:
            cmd = "_TRIM" if mode.lower() == "trim" else "_EXTEND"
            document.SendCommand(f"{cmd} (handent \"{boundary_handle}\") \n (handent \"{handle}\") \n\n")
            self.refresh_view()
            return True
        except Exception as e:
            logger.error(f"Failed to {mode} entity {handle} against {boundary_handle}: {e}")
            return False


