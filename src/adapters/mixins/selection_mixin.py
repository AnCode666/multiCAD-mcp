"""
Selection mixin for AutoCAD adapter.

Handles entity selection operations.
"""

import logging
from typing import List, Callable, Any, TYPE_CHECKING

from mcp_tools.constants import (
    SS_COLOR_SELECT,
    SS_LAYER_SELECT,
    SS_TYPE_SELECT,
    SS_SELECTION_GET,
    SELECTION_SET_IMPLIED,
)

logger = logging.getLogger(__name__)


class SelectionMixin:
    """Mixin for selection operations."""

    if TYPE_CHECKING:
        # Tell type checker this mixin is used with CADAdapterProtocol
        def _validate_connection(self) -> None: ...
        def _get_document(self, operation: str = "operation") -> Any: ...
        def _get_application(self, operation: str = "operation") -> Any: ...
        def _delete_selection_set(self, document: Any, name: str) -> None: ...
        def _get_color_index(self, color_name: str) -> int: ...

    def _select_entities_generic(
        self,
        filter_func: Callable[[Any], bool],
        selection_set_name: str,
        description: str,
    ) -> List[str]:
        """Generic entity selection helper.

        Args:
            filter_func: Function that takes an entity and returns True if it matches criteria
            selection_set_name: Name for the selection set
            description: Description for logging

        Returns:
            List of entity handles that match criteria
        """
        try:
            self._validate_connection()
            document = self._get_document("select")
            app = self._get_application("select")

            selected_handles = []
            entities_to_select = []

            # Iterate through all entities in ModelSpace
            for entity in document.ModelSpace:
                try:
                    if filter_func(entity):
                        handle = str(entity.Handle)
                        selected_handles.append(handle)
                        entities_to_select.append(entity)
                        logger.debug(f"Found {description}: {handle}")
                except Exception as e:
                    logger.debug(f"Error processing entity: {e}")
                    continue

            # Create visible selection using SelectionSet
            if entities_to_select:
                try:
                    # Clear current selection
                    app.ActiveDocument.Select(-1)
                    self._delete_selection_set(document, selection_set_name)

                    ss = document.SelectionSets.Add(selection_set_name)
                    for entity in entities_to_select:
                        try:
                            ss.Select(SELECTION_SET_IMPLIED, None, entity)
                            logger.debug(
                                f"Added entity {entity.Handle} to selection set"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to add entity to selection set: {e}"
                            )
                except Exception as e:
                    logger.warning(f"Failed to create selection set: {e}")

            logger.info(f"Selected {len(selected_handles)} {description}")
            return selected_handles

        except Exception as e:
            logger.error(f"Failed to select {description}: {e}")
            return []

    def select_by_color(self, color: str | int) -> List[str]:
        """Select all entities of a specific color."""
        if isinstance(color, str):
            color = self._get_color_index(color)

        def color_filter(entity: Any) -> bool:
            return hasattr(entity, "Color") and entity.Color == color

        return self._select_entities_generic(
            color_filter, SS_COLOR_SELECT, f"entities with color {color}"
        )

    def select_by_layer(self, layer_name: str) -> List[str]:
        """Select all entities on a specific layer."""
        target_layer = layer_name.strip()

        def layer_filter(entity: Any) -> bool:
            try:
                # Get layer name - try multiple approaches
                entity_layer = None
                try:
                    entity_layer = str(entity.Layer).strip()
                except Exception:
                    try:
                        entity_layer = str(
                            entity.Properties.Item("Layer").Value
                        ).strip()
                    except Exception:
                        return False

                # Normalize and case-insensitive comparison
                return entity_layer.lower() == target_layer.lower()
            except Exception:
                return False

        return self._select_entities_generic(
            layer_filter, SS_LAYER_SELECT, f"entities on layer '{layer_name}'"
        )

    def select_by_type(self, entity_type: str) -> List[str]:
        """Select all entities of a specific type."""
        # Map user-friendly types to AutoCAD object names
        type_map = {
            "line": "AcDbLine",
            "circle": "AcDbCircle",
            "arc": "AcDbArc",
            "polyline": "AcDb2dPolyline",
            "text": "AcDbText",
            "point": "AcDbPoint",
        }

        object_name = type_map.get(entity_type.lower(), entity_type)
        logger.debug(f"Searching for entities of type: {object_name}")

        def type_filter(entity: Any) -> bool:
            try:
                current_object_name = entity.ObjectName
                return (
                    current_object_name == object_name
                    or entity_type.lower() in current_object_name.lower()
                )
            except Exception:
                return False

        return self._select_entities_generic(
            type_filter, SS_TYPE_SELECT, f"entities of type '{entity_type}'"
        )

    def get_selected_entities(self) -> List[str]:
        """Get list of currently selected entities."""
        try:
            self._validate_connection()
            app = self._get_application("get_selected_entities")
            selected = app.ActiveDocument.SelectionSets.Add(SS_SELECTION_GET)

            handles = []
            try:
                for entity in selected:
                    handles.append(str(entity.Handle))
            finally:
                selected.Delete()

            logger.debug(f"Got {len(handles)} selected entities")
            return handles
        except Exception as e:
            logger.error(f"Failed to get selected entities: {e}")
            return []

    def clear_selection(self) -> bool:
        """Clear current selection."""
        try:
            self._validate_connection()
            app = self._get_application("clear_selection")
            app.ActiveDocument.Select(-1)  # Select nothing
            logger.debug("Selection cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear selection: {e}")
            return False

    def has_selection(self) -> bool:
        """Check if any entities are currently selected.

        Returns:
            True if at least one entity is selected, False otherwise
        """
        try:
            self._validate_connection()
            doc = self._get_document("has_selection")

            # Use PickFirst selection set for reliable detection
            return doc.PickfirstSelectionSet.Count > 0

        except Exception as e:
            logger.debug(f"has_selection check failed: {e}")
            return False

    def get_selected_entity_handles(self) -> list[str]:
        """Get list of currently selected entity handles.

        Returns:
            List of entity handles (strings). Empty list if no selection.
        """
        try:
            self._validate_connection()
            doc = self._get_document("get_selected_entity_handles")

            handles = []

            # Use PickFirst selection set (most reliable)
            pickfirst = doc.PickfirstSelectionSet

            if pickfirst.Count > 0:
                for entity in pickfirst:
                    try:
                        handles.append(str(entity.Handle))
                    except Exception as e:
                        logger.debug(f"Failed to get handle for entity: {e}")
                        continue

                logger.info(f"Retrieved {len(handles)} selected entity handles")
                return handles

            logger.debug("No selected entities found")
            return []

        except Exception as e:
            logger.error(f"Failed to get selected entity handles: {e}")
            return []

    def get_selection_info(self) -> dict[str, Any]:
        """Get comprehensive information about current selection.

        Returns:
            Dictionary with:
            - count: Number of selected entities
            - handles: List of entity handles
            - types: List of entity ObjectNames
            - layers: Set of layers containing selected entities
        """
        try:
            self._validate_connection()
            doc = self._get_document("get_selection_info")

            info: dict[str, Any] = {
                "count": 0,
                "handles": [],
                "types": [],
                "layers": [],
            }

            pickfirst = doc.PickfirstSelectionSet
            info["count"] = pickfirst.Count

            if info["count"] > 0:
                layers_set: set[str] = set()

                for entity in pickfirst:
                    try:
                        info["handles"].append(str(entity.Handle))
                        info["types"].append(str(entity.ObjectName))
                        layers_set.add(str(entity.Layer))
                    except Exception as e:
                        logger.debug(f"Error extracting entity info: {e}")
                        continue

                info["layers"] = sorted(list(layers_set))

            return info

        except Exception as e:
            logger.error(f"Failed to get selection info: {e}")
            return {"count": 0, "handles": [], "types": [], "layers": []}
