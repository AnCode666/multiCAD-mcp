"""
Entity mixin for AutoCAD adapter.

Handles entity property operations.
"""

import logging
import math
from typing import Dict, Any, TYPE_CHECKING, Optional, List

logger = logging.getLogger(__name__)


class EntityMixin:
    """Mixin for entity property operations."""

    if TYPE_CHECKING:

        def _get_document(self, operation: str = "operation") -> Any: ...
        def _get_color_index(self, color_name: str) -> int: ...
        def validate_lineweight(self, weight: int) -> int: ...

    def delete_entity(self, handle: str) -> bool:
        """Delete a drawing entity identified by its COM handle.

        Args:
            handle: The entity handle string as returned by AutoCAD COM.

        Returns:
            True if deleted successfully, False otherwise.
        """
        try:
            document = self._get_document("delete_entity")

            entity = document.HandleToObject(handle)
            entity.Delete()
            logger.debug(f"Deleted entity {handle}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            return False

    def get_entity_properties(self, handle: str) -> Dict[str, Any]:
        """Retrieve common properties of a drawing entity via COM.

        Args:
            handle: The entity handle string as returned by AutoCAD COM.

        Returns:
            Dictionary with keys: handle, object_name, layer, color, lineweight.
            Returns an empty dict if the entity cannot be accessed.
        """
        try:
            document = self._get_document("get_entity_properties")

            entity = document.HandleToObject(handle)
            return {
                "handle": entity.Handle,
                "object_name": entity.ObjectName,
                "layer": entity.Layer,
                "color": entity.Color,
                "lineweight": entity.LineWeight,
            }
        except Exception as e:
            logger.error(f"Failed to get entity properties: {e}")
            return {}

    def set_entity_properties(self, handle: str, properties: Dict[str, Any]) -> bool:
        """Modify one or more properties of a drawing entity via COM.

        Supported keys in ``properties``: ``layer`` (str), ``color`` (str or int ACI
        index), ``lineweight`` (int).

        Args:
            handle: The entity handle string as returned by AutoCAD COM.
            properties: Dictionary of property names to new values.

        Returns:
            True if the update succeeded, False otherwise.
        """
        try:
            document = self._get_document("set_entity_properties")

            entity = document.HandleToObject(handle)

            if "layer" in properties:
                entity.Layer = properties["layer"]
            if "color" in properties:
                color = properties["color"]
                if isinstance(color, str):
                    color = self._get_color_index(color)
                entity.Color = color
            if "lineweight" in properties:
                entity.LineWeight = self.validate_lineweight(properties["lineweight"])

            logger.debug(f"Updated properties for entity {handle}")
            return True
        except Exception as e:
            logger.error(f"Failed to set entity properties: {e}")
            return False

    def get_entity_area(self, handle: str) -> Dict[str, Any]:
        """Calculate or retrieve the area and perimeter of an entity.

        Supports native COM properties (Area, Length) as well as geometric
        Shoelace computation on polyline vertices when native properties are missing.

        Args:
            handle: The entity handle string.

        Returns:
            Dictionary with keys: handle, object_name, layer, area, perimeter.
        """
        try:
            document = self._get_document("get_entity_area")
            entity = document.HandleToObject(handle)
            object_name = getattr(entity, "ObjectName", "Entity")
            layer = getattr(entity, "Layer", "0")

            area = 0.0
            perimeter = 0.0

            # 1. Native COM properties
            try:
                area = float(getattr(entity, "Area", 0.0))
            except Exception:
                area = 0.0

            try:
                perimeter = float(
                    getattr(entity, "Length", getattr(entity, "Perimeter", 0.0))
                )
            except Exception:
                perimeter = 0.0

            # 2. Geometric fallback for polylines using Coordinates
            if area == 0.0 and hasattr(entity, "Coordinates"):
                try:
                    coords = list(entity.Coordinates)
                    is_3d = "Polyline" in object_name and "Light" not in object_name
                    step = 3 if is_3d else 2
                    pts = [
                        (coords[i], coords[i + 1])
                        for i in range(0, len(coords) - step + 1, step)
                    ]
                    n = len(pts)
                    if n >= 3:
                        a = 0.0
                        p = 0.0
                        for i in range(n):
                            j = (i + 1) % n
                            a += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
                            p += math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
                        area = abs(a) / 2.0
                        if perimeter == 0.0:
                            perimeter = p
                except Exception as ce:
                    logger.debug(f"Coordinates area calculation fallback failed: {ce}")

            return {
                "handle": handle,
                "object_name": object_name,
                "layer": layer,
                "area": round(area, 4),
                "perimeter": round(perimeter, 4),
            }
        except Exception as e:
            logger.error(f"Failed to calculate area for entity {handle}: {e}")
            return {"handle": handle, "error": str(e), "area": 0.0, "perimeter": 0.0}

    def find_text_entities(
        self,
        search_pattern: str,
        layer: Optional[str] = None,
        case_sensitive: bool = False,
        use_regex: bool = False,
        handles: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find text entities in AutoCAD drawing."""
        import re
        flags = 0 if case_sensitive else re.IGNORECASE
        pat = re.compile(search_pattern if use_regex else re.escape(search_pattern), flags)

        results = []
        try:
            document = self._get_document("find_text_entities")
            target_handles = set(handles) if handles else None

            for obj in document.ModelSpace:
                h = getattr(obj, "Handle", "")
                if target_handles and h not in target_handles:
                    continue
                obj_layer = getattr(obj, "Layer", "")
                if layer and obj_layer.lower() != layer.lower():
                    continue

                obj_name = getattr(obj, "ObjectName", "")
                if obj_name in ("AcDbText", "AcDbMText"):
                    txt = getattr(obj, "TextString", "")
                    if pat.search(txt):
                        results.append({"handle": h, "type": obj_name, "text": txt, "layer": obj_layer})
                elif obj_name == "AcDbBlockReference" and getattr(obj, "HasAttributes", False):
                    for att in obj.GetAttributes():
                        txt = getattr(att, "TextString", "")
                        if pat.search(txt):
                            results.append({
                                "handle": h,
                                "attrib_tag": getattr(att, "TagString", ""),
                                "type": "AcDbAttribute",
                                "text": txt,
                                "layer": getattr(att, "Layer", obj_layer),
                            })
        except Exception as e:
            logger.error(f"Error finding text entities: {e}")
        return results

    def replace_text_entities(
        self,
        search_pattern: str,
        replacement: str,
        layer: Optional[str] = None,
        case_sensitive: bool = False,
        use_regex: bool = False,
        handles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Batch find and replace text across drawing entities in AutoCAD."""
        import re
        flags = 0 if case_sensitive else re.IGNORECASE
        pat = re.compile(search_pattern if use_regex else re.escape(search_pattern), flags)

        replacements = []
        try:
            document = self._get_document("replace_text_entities")
            target_handles = set(handles) if handles else None

            for obj in document.ModelSpace:
                h = getattr(obj, "Handle", "")
                if target_handles and h not in target_handles:
                    continue
                obj_layer = getattr(obj, "Layer", "")
                if layer and obj_layer.lower() != layer.lower():
                    continue

                obj_name = getattr(obj, "ObjectName", "")
                if obj_name in ("AcDbText", "AcDbMText"):
                    old_txt = getattr(obj, "TextString", "")
                    if pat.search(old_txt):
                        new_txt = pat.sub(replacement, old_txt)
                        if new_txt != old_txt:
                            obj.TextString = new_txt
                            obj.Update()
                            replacements.append({
                                "handle": h,
                                "type": obj_name,
                                "old_text": old_txt,
                                "new_text": new_txt,
                                "layer": obj_layer,
                            })
                elif obj_name == "AcDbBlockReference" and getattr(obj, "HasAttributes", False):
                    for att in obj.GetAttributes():
                        old_txt = getattr(att, "TextString", "")
                        if pat.search(old_txt):
                            new_txt = pat.sub(replacement, old_txt)
                            if new_txt != old_txt:
                                att.TextString = new_txt
                                att.Update()
                                replacements.append({
                                    "handle": h,
                                    "attrib_tag": getattr(att, "TagString", ""),
                                    "type": "AcDbAttribute",
                                    "old_text": old_txt,
                                    "new_text": new_txt,
                                    "layer": getattr(att, "Layer", obj_layer),
                                })
        except Exception as e:
            logger.error(f"Error replacing text entities: {e}")
            return {"success": False, "error": str(e), "count": len(replacements), "replacements": replacements}

        return {"success": True, "count": len(replacements), "replacements": replacements}
