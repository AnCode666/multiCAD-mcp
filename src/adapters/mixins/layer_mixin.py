"""
Layer mixin for AutoCAD adapter.

Handles all layer management operations.
"""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from core import LayerError, ColorError
from mcp_tools.constants import COLOR_MAP

logger = logging.getLogger(__name__)


class LayerMixin:
    """Mixin for layer management operations."""

    if TYPE_CHECKING:
        _drawing_state: dict

        def _validate_connection(self) -> None: ...

        def _get_document(self, operation: str = "operation") -> Any: ...

        def _get_application(self, operation: str = "operation") -> Any: ...

        def _get_color_index(self, color_name: str) -> int: ...

        def validate_lineweight(self, weight: int) -> int: ...

        def _fast_get_property(
            self, obj: Any, property_name: str, default: Any = None
        ) -> Any: ...

        def _safe_get_property(
            self, obj: Any, property_name: str, default: Any = None
        ) -> Any: ...

    def create_layer(
        self,
        name: str,
        color: str | int = "white",
        lineweight: int = 0,
    ) -> bool:
        """Create a new layer."""
        try:
            document = self._get_document("create_layer")

            layer_obj = document.Layers.Add(name)

            if isinstance(color, str):
                color = self._get_color_index(color)
            layer_obj.Color = color

            if self.validate_lineweight(lineweight) == lineweight:
                layer_obj.LineWeight = lineweight

            logger.info(f"Created layer '{name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create layer '{name}': {e}")
            return False

    def set_current_layer(self, name: str) -> bool:
        """Set active layer."""
        try:
            document = self._get_document("set_current_layer")

            document.ActiveLayer = document.Layers.Item(name)
            self._drawing_state["current_layer"] = name
            logger.debug(f"Set current layer to '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to set current layer: {e}")
            return False

    def get_current_layer(self) -> str:
        """Get current active layer."""
        try:
            document = self._get_document("get_current_layer")
            return str(document.ActiveLayer.Name)
        except Exception:
            current_layer = self._drawing_state["current_layer"]
            return str(current_layer) if current_layer else "0"

    def list_layers(self) -> List[str]:
        """Get list of all layers."""
        try:
            document = self._get_document("list_layers")
            layers: List[str] = []
            for layer in document.Layers:
                layers.append(layer.Name)
            return layers
        except Exception as e:
            logger.error(f"Failed to list layers: {e}")
            return []

    def get_layers_info(
        self, entity_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed information about all layers.

        Optimized to count entities per layer in a single pass using direct iteration,
        or from pre-extracted entity data to avoid re-iterating ModelSpace.

        Args:
            entity_data: Optional pre-extracted entity data. If provided, layer counts
                        will be computed from this data instead of iterating ModelSpace.

        Returns:
            List of dictionaries with layer information:
            - Name: Layer name
            - ObjectCount: Number of objects on the layer
            - Color: Layer color
            - Linetype: Layer linetype
            - Lineweight: Layer lineweight
            - IsLocked: Whether layer is locked
            - IsVisible: Whether layer is visible
        """
        try:
            document = self._get_document("get_layers_info")
            layers_info = []

            # OPTIMIZATION: Use pre-extracted data if available to avoid re-iteration
            layer_counts: Dict[str, int] = {}

            if entity_data is not None:
                # Count from pre-extracted data (MUCH faster - no COM calls)
                logger.debug(
                    f"Computing layer counts from {len(entity_data)} pre-extracted entities"
                )
                for entity in entity_data:
                    layer_name = entity.get("Layer", "0")
                    layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
            else:
                # Fallback: iterate ModelSpace (slower - requires COM calls)
                logger.debug("Iterating ModelSpace to count entities by layer")
                model_space = document.ModelSpace

                try:
                    # Direct iteration (faster than Item(i))
                    for entity in model_space:
                        try:
                            layer_name = self._fast_get_property(entity, "Layer", "0")
                            layer_counts[layer_name] = (
                                layer_counts.get(layer_name, 0) + 1
                            )
                        except Exception:
                            pass
                except Exception:
                    # Fallback to indexed iteration if direct iteration fails
                    try:
                        entity_count = model_space.Count
                        for i in range(entity_count):
                            try:
                                entity = model_space.Item(i)
                                layer_name = self._fast_get_property(
                                    entity, "Layer", "0"
                                )
                                layer_counts[layer_name] = (
                                    layer_counts.get(layer_name, 0) + 1
                                )
                            except Exception:
                                pass
                    except Exception as e:
                        logger.debug(f"Failed to count entities by layer: {e}")

            # Build layer information
            for layer in document.Layers:
                try:
                    # Get layer properties
                    layer_color = self._safe_get_property(layer, "Color", 256)
                    color_map_reverse = {v: k for k, v in COLOR_MAP.items()}
                    color_name = color_map_reverse.get(layer_color, str(layer_color))

                    layer_info = {
                        "Name": str(layer.Name),
                        "ObjectCount": layer_counts.get(str(layer.Name), 0),
                        "Color": color_name,
                        "Linetype": str(
                            self._safe_get_property(layer, "Linetype", "Continuous")
                        ),
                        "Lineweight": str(
                            self._safe_get_property(layer, "Lineweight", "Default")
                        ),
                        "IsLocked": bool(self._safe_get_property(layer, "Lock", False)),
                        "IsVisible": not bool(
                            self._safe_get_property(layer, "Frozen", False)
                        ),
                    }
                    layers_info.append(layer_info)
                except Exception as e:
                    logger.debug(f"Failed to get info for layer {layer.Name}: {e}")
                    continue

            return layers_info
        except Exception as e:
            logger.error(f"Failed to get layers info: {e}")
            return []

    def rename_layer(self, old_name: str, new_name: str) -> bool:
        """Rename an existing layer."""
        try:
            self._validate_connection()
            document = self._get_document("rename_layer")

            if old_name == "0":
                logger.error("Cannot rename layer '0' (standard layer)")
                return False

            layer = document.Layers.Item(old_name)
            layer.Name = new_name
            logger.info(f"Renamed layer '{old_name}' to '{new_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to rename layer '{old_name}' to '{new_name}': {e}")
            return False

    def delete_layer(self, name: str) -> bool:
        """Delete a layer from the drawing."""
        try:
            self._validate_connection()
            document = self._get_document("delete_layer")

            if name == "0":
                logger.error("Cannot delete layer '0' (standard layer)")
                return False

            layer = document.Layers.Item(name)
            layer.Delete()
            logger.info(f"Deleted layer '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete layer '{name}': {e}")
            return False

    def turn_layer_on(self, name: str) -> bool:
        """Turn on (make visible) a layer."""
        try:
            self._validate_connection()
            document = self._get_document("turn_layer_on")

            layer = document.Layers.Item(name)
            layer.Freeze = False
            logger.info(f"Turned on layer '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to turn on layer '{name}': {e}")
            return False

    def turn_layer_off(self, name: str) -> bool:
        """Turn off (hide) a layer."""
        try:
            self._validate_connection()
            document = self._get_document("turn_layer_off")

            layer = document.Layers.Item(name)
            layer.Freeze = True
            logger.info(f"Turned off layer '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to turn off layer '{name}': {e}")
            return False

    def is_layer_on(self, name: str) -> bool:
        """Check if a layer is visible (turned on)."""
        try:
            self._validate_connection()
            document = self._get_document("is_layer_on")

            layer = document.Layers.Item(name)
            return not layer.Freeze
        except Exception as e:
            logger.error(f"Failed to check layer '{name}' visibility: {e}")
            return False

    def set_layer_color(self, layer_name: str, color: str | int) -> bool:
        """Set the color of a layer.

        Args:
            layer_name: Name of the layer to modify
            color: Color name (from COLOR_MAP) or ACI index (1-255)

        Returns:
            bool: True if successful, False otherwise

        Note:
            - Uses the modern TrueColor property (recommended by Autodesk)
            - Accepts color names: "red", "blue", "green", etc.
            - Accepts ACI index: 1-255
            - Color value 256 (bylayer) is not valid for layers
        """
        try:
            self._validate_connection()
            document = self._get_document("set_layer_color")
            app = self._get_application("set_layer_color")

            # Get the layer
            try:
                layer = document.Layers.Item(layer_name)
            except Exception:
                raise LayerError(layer_name, "Layer does not exist")

            # Convert color name to ACI index
            if isinstance(color, str):
                color_index = self._get_color_index(color)
            else:
                color_index = color

            # Validate color index (1-255 for layers, 256 is not valid)
            if color_index == 256:
                raise ColorError(
                    str(color_index),
                    "Color 'bylayer' (256) is not valid for layers. Use a specific ACI color (1-255).",
                )
            if not (0 <= color_index <= 255):
                raise ColorError(
                    str(color_index), "Invalid color index. Must be 0-255."
                )

            # Create AcCmColor object (modern method)
            color_obj = app.GetInterfaceObject("AutoCAD.AcCmColor.20")
            color_obj.ColorIndex = color_index

            # Apply to layer using TrueColor property
            layer.TrueColor = color_obj

            logger.info(f"Set layer '{layer_name}' color to ACI {color_index}")
            return True

        except (LayerError, ColorError):
            raise
        except Exception as e:
            logger.error(f"Failed to set layer '{layer_name}' color: {e}")
            return False

    def set_entities_color_bylayer(self, handles: List[str]) -> Dict[str, Any]:
        """Set entities to use their layer's color (ByLayer).

        Args:
            handles: List of entity handles to modify

        Returns:
            dict: Result summary with counts and details:
                - total: Total entities processed
                - changed: Number successfully changed to ByLayer
                - failed: Number that failed
                - results: List of per-entity results

        Note:
            - Assigns color value 256 (acByLayer) to entities
            - Entities will inherit their layer's color
            - Uses TrueColor property (modern method)
        """
        try:
            self._validate_connection()
            document = self._get_document("set_entities_color_bylayer")
            app = self._get_application("set_entities_color_bylayer")
            model_space = document.ModelSpace

            results = []
            changed_count = 0
            failed_count = 0

            # Create AcCmColor object for ByLayer (256)
            color_obj = app.GetInterfaceObject("AutoCAD.AcCmColor.20")
            color_obj.ColorIndex = 256  # acByLayer

            for handle in handles:
                try:
                    # Get entity by handle
                    try:
                        entity = model_space.Item(model_space.Count - 1)
                        for i in range(model_space.Count):
                            entity = model_space.Item(i)
                            if str(entity.Handle) == str(handle):
                                break
                        else:
                            results.append(
                                {
                                    "handle": handle,
                                    "success": False,
                                    "error": "Entity not found",
                                }
                            )
                            failed_count += 1
                            continue
                    except Exception as e:
                        results.append(
                            {
                                "handle": handle,
                                "success": False,
                                "error": f"Failed to find entity: {e}",
                            }
                        )
                        failed_count += 1
                        continue

                    # Set color to ByLayer using TrueColor
                    entity.TrueColor = color_obj

                    results.append({"handle": handle, "success": True})
                    changed_count += 1

                except Exception as e:
                    results.append(
                        {"handle": handle, "success": False, "error": str(e)}
                    )
                    failed_count += 1

            logger.info(f"Set {changed_count}/{len(handles)} entities to ByLayer color")

            return {
                "total": len(handles),
                "changed": changed_count,
                "failed": failed_count,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Failed to set entities to ByLayer: {e}")
            return {
                "total": len(handles),
                "changed": 0,
                "failed": len(handles),
                "error": str(e),
                "results": [],
            }
