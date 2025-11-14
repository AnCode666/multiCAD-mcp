"""
Debug and diagnostic tools.

Provides tools for:
- Listing all entities in the drawing
- Testing entity selection methods
"""

import logging
import traceback
from typing import Optional

from mcp.server.fastmcp import Context

from core import CADOperationError
from mcp_tools.decorators import get_current_adapter

logger = logging.getLogger(__name__)


def register_debug_tools(mcp):
    """Register debug and diagnostic tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @mcp.tool()
    def debug_entities(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Debug tool to list all entities in the drawing with their properties.

        Args:
            cad_type: CAD application to use

        Returns:
            Detailed information about all entities in the drawing
        """
        try:
            document = get_current_adapter()._get_document("debug_entities")

            entities_info = []
            entity_count = 0
            layers_found = set()

            for entity in document.ModelSpace:
                try:
                    entity_count += 1
                    layer = entity.Layer
                    obj_name = entity.ObjectName
                    entity_type = "unknown"

                    if "Line" in obj_name:
                        entity_type = "line"
                    elif "Circle" in obj_name:
                        entity_type = "circle"
                    elif "Arc" in obj_name:
                        entity_type = "arc"
                    elif "Polyline" in obj_name:
                        entity_type = "polyline"
                    elif "Text" in obj_name:
                        entity_type = "text"

                    handle = str(entity.Handle)
                    layer_str = str(layer).strip()
                    layers_found.add(layer_str)

                    entities_info.append(
                        f"  {entity_count}. Handle: {handle}, Type: {entity_type}, "
                        f"Layer: '{layer_str}' (type: {type(layer).__name__}), ObjectName: {obj_name}"
                    )
                except Exception as e:
                    entities_info.append(f"  Error reading entity: {e}")

            if not entities_info:
                return "No entities found in drawing"

            summary = f"Total entities: {entity_count}\nLayers found: {', '.join(sorted(layers_found))}\n\nEntities in drawing:\n"
            return summary + "\n".join(entities_info)
        except Exception as e:
            raise CADOperationError("debug_entities", str(e))

    @mcp.tool()
    def test_select_by_layer(
        ctx: Context,
        layer_name: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Debug tool to test select_by_layer and show detailed comparison.

        Args:
            layer_name: Layer name to test selection for
            cad_type: CAD application to use

        Returns:
            Detailed debug information about entity selection
        """
        try:
            document = get_current_adapter()._get_document("test_select_by_layer")

            debug_info = [f"Testing select_by_layer for layer: '{layer_name}'"]
            debug_info.append(f"Target layer type: {type(layer_name).__name__}")
            debug_info.append(f"Target layer stripped: '{layer_name.strip()}'")
            debug_info.append(f"Target layer lower: '{layer_name.lower()}'")
            debug_info.append("")

            matching_entities = []
            all_entities = []

            debug_info.append("Scanning all entities:")
            for i, entity in enumerate(document.ModelSpace):
                try:
                    handle = str(entity.Handle)
                    entity_layer = entity.Layer
                    entity_layer_str = str(entity_layer).strip()

                    all_entities.append((handle, entity_layer_str))

                    debug_info.append(
                        f"  Entity {i+1}: Handle={handle}, Layer='{entity_layer_str}' (raw type: {type(entity_layer).__name__})"
                    )

                    exact_match = entity_layer_str == layer_name
                    case_insensitive_match = (
                        entity_layer_str.lower() == layer_name.lower()
                    )

                    if exact_match or case_insensitive_match:
                        debug_info.append(
                            f"    -> MATCH! (exact={exact_match}, case_insensitive={case_insensitive_match})"
                        )
                        matching_entities.append(handle)
                    else:
                        debug_info.append("    -> NO MATCH")
                        debug_info.append(
                            f"       exact_match: {entity_layer_str!r} == {layer_name!r} = {exact_match}"
                        )
                        debug_info.append(
                            f"       case_insensitive: {entity_layer_str.lower()!r} == {layer_name.lower()!r} = {case_insensitive_match}"
                        )

                except Exception as e:
                    debug_info.append(f"  Error reading entity {i}: {e}")

            debug_info.append("")
            debug_info.append("Summary:")
            debug_info.append(f"  Total entities scanned: {len(all_entities)}")
            debug_info.append(f"  Entities on target layer: {len(matching_entities)}")
            debug_info.append(f"  Matching handles: {matching_entities}")

            debug_info.append("")
            debug_info.append("Calling get_current_adapter().select_by_layer()...")
            selected = get_current_adapter().select_by_layer(layer_name)
            debug_info.append(f"  Result: {selected}")

            return "\n".join(debug_info)

        except Exception as e:
            return f"Error in test_select_by_layer: {e}\n\nStack trace: {traceback.format_exc()}"
