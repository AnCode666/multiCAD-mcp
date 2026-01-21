"""
Manipulation mixin for AutoCAD adapter.

Handles entity manipulation operations (move, rotate, scale, copy, paste, arrays).
"""

import logging
import time
from typing import List, TYPE_CHECKING

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
        """Move entities by an offset."""
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
        """Rotate entities around a point."""
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
        """Scale entities around a point."""
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
        """Copy entities to clipboard using SendCommand."""
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
        """Paste entities from clipboard."""
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
        """Change color of entities."""
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
        """Move entities to a different layer."""
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
        """Create a rectangular array of entities."""
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
        """Create a polar (circular) array of entities."""
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
        """Create an array of entities along a path."""
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
