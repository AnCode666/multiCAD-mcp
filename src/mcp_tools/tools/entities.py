"""
Unified entity management tool.

Single manage_entities tool replaces 13 legacy entity tools with
a simple shorthand format for ~85% token reduction.

SHORTHAND FORMAT (one per line):
    select|by|value               → select|layer|walls
    move|handles|offset_x|offset_y → move|A1,B2|10|5
    rotate|handles|angle|cx|cy    → rotate|A1|45|0|0
    scale|handles|factor|cx|cy    → scale|A1|2.0|0|0
    set_color|handles|color       → set_color|A1,B2|red
    set_layer|handles|layer       → set_layer|A1|walls
    copy|handles                  → copy|A1,B2
    delete|handles                → delete|A1,B2
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple


from pydantic import ValidationError

from core.models import (
    MoveEntityRequest,
    RotateEntityRequest,
    ScaleEntityRequest,
)
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_handles
from mcp_tools.shorthand import parse_entity_ops_input

logger = logging.getLogger(__name__)


# ========== Action Handlers ==========


def _select(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Select entities by color, layer, or type criterion.

    Args:
        spec: Operation spec with keys: by (str), value (str).

    Returns:
        Dict with keys: success (bool), count (int), handles (list), detail (str).
    """
    adapter = get_current_adapter()
    by = spec["by"].lower()

    select_map = {
        "color": ("color", lambda v: adapter.select_by_color(v)),
        "layer": ("layer_name", lambda v: adapter.select_by_layer(v)),
        "type": ("entity_type", lambda v: adapter.select_by_type(v)),
    }

    entry = select_map.get(by)
    if not entry:
        return {
            "success": False,
            "error": f"Unknown selection criteria '{by}'. Supported: color, layer, type",
        }

    _, handler = entry
    value = spec["value"]
    handles = handler(value)

    if handles:
        return {
            "success": True,
            "count": len(handles),
            "handles": handles,
            "detail": f"Selected {len(handles)} entities by {by}='{value}'",
        }
    return {
        "success": True,
        "count": 0,
        "handles": [],
        "detail": f"No entities found with {by}='{value}'",
    }


def _move(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Move entities by a displacement offset.

    Args:
        spec: Operation spec with keys: handles (str), offset_x (float), offset_y (float).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handle_list = parse_handles(spec["handles"])
    validated = MoveEntityRequest(
        handles=handle_list,
        displacement=(spec["offset_x"], spec["offset_y"]),
    )
    success = get_current_adapter().move_entities(
        validated.handles, spec["offset_x"], spec["offset_y"]
    )
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Moved by ({spec['offset_x']}, {spec['offset_y']})",
    }


def _rotate(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Rotate entities around a center point.

    Args:
        spec: Operation spec with keys: handles (str), angle (float), center_x (float), center_y (float).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handle_list = parse_handles(spec["handles"])
    validated = RotateEntityRequest(
        handles=handle_list,
        base_point=(spec["center_x"], spec["center_y"]),
        angle=spec["angle"],
    )
    success = get_current_adapter().rotate_entities(
        validated.handles, spec["center_x"], spec["center_y"], validated.angle
    )
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Rotated {spec['angle']}° around ({spec['center_x']}, {spec['center_y']})",
    }


def _scale(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Scale entities around a center point.

    Args:
        spec: Operation spec with keys: handles (str), scale_factor (float), center_x (float), center_y (float).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handle_list = parse_handles(spec["handles"])
    validated = ScaleEntityRequest(
        handles=handle_list,
        base_point=(spec["center_x"], spec["center_y"]),
        scale_factor=spec["scale_factor"],
    )
    success = get_current_adapter().scale_entities(
        validated.handles,
        spec["center_x"],
        spec["center_y"],
        validated.scale_factor,
    )
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Scaled {spec['scale_factor']}x around ({spec['center_x']}, {spec['center_y']})",
    }


def _set_color(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Change the color of entities.

    Args:
        spec: Operation spec with keys: handles (str), color (str).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handle_list = parse_handles(spec["handles"])
    color = spec["color"]
    success = get_current_adapter().change_entity_color(handle_list, color)
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Color set to '{color}'",
    }


def _set_layer(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Move entities to a different layer.

    Args:
        spec: Operation spec with keys: handles (str), layer_name (str).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handle_list = parse_handles(spec["handles"])
    layer_name = spec["layer_name"]
    success = get_current_adapter().change_entity_layer(handle_list, layer_name)
    return {
        "success": success,
        "count": len(handle_list),
        "detail": f"Moved to layer '{layer_name}'",
    }


def _set_color_bylayer(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Reset entity colors to ByLayer.

    Args:
        spec: Operation spec with keys: handles (str or list).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handles_raw = spec["handles"]
    try:
        if isinstance(handles_raw, str):
            if handles_raw.startswith("["):
                handles_list = json.loads(handles_raw)
            else:
                handles_list = parse_handles(handles_raw)
        else:
            handles_list = handles_raw
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse handles in set_color_bylayer: {e}")
        return {"success": False, "error": f"Invalid handles format: {e}"}

    try:
        result = get_current_adapter().set_entities_color_bylayer(handles_list)
        return {
            "success": result.get("changed", 0) > 0,
            "count": result.get("total", len(handles_list)),
            "detail": f"Set {result.get('changed', 0)} entities to ByLayer color",
        }
    except Exception as e:
        logger.error(f"set_color_bylayer failed: {e}")
        return {"success": False, "error": str(e)}


def _copy(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Copy entities to the clipboard.

    Args:
        spec: Operation spec with keys: handles (str).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handle_list = parse_handles(spec["handles"])
    success = get_current_adapter().copy_entities(handle_list)
    return {
        "success": success,
        "count": len(handle_list),
        "detail": (
            f"Copied {len(handle_list)} entities to clipboard"
            if success
            else "Failed to copy entities"
        ),
    }


def _paste(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Paste entities at a base point.

    Args:
        spec: Operation spec with keys: base_point (str, format 'x,y').

    Returns:
        Dict with keys: success (bool), detail (str).
    """
    base_point = spec["base_point"]
    parts = str(base_point).split(",")
    if len(parts) < 2:
        return {"success": False, "error": "base_point must be 'x,y' format"}
    try:
        bx, by = float(parts[0].strip()), float(parts[1].strip())
    except (ValueError, IndexError) as e:
        return {"success": False, "error": f"Invalid base_point coordinates: {e}"}

    try:
        get_current_adapter().paste_entities(bx, by)
        return {"success": True, "detail": f"Pasted entities at ({bx}, {by})"}
    except Exception as e:
        logger.error(f"Paste failed: {e}")
        return {"success": False, "error": str(e)}


def _delete(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Delete entities by handle.

    Args:
        spec: Operation spec with keys: handles (str).

    Returns:
        Dict with keys: success (bool), count (int), detail (str).
    """
    handle_list = parse_handles(spec["handles"])
    adapter = get_current_adapter()
    deleted_count = 0
    for handle in handle_list:
        if adapter.delete_entity(handle):
            deleted_count += 1
    return {
        "success": deleted_count > 0,
        "count": len(handle_list),
        "detail": f"Deleted {deleted_count} entities",
    }


def _area(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate area and perimeter for entities.

    Args:
        spec: Operation spec with optional keys: handles (str or list), layer (str).

    Returns:
        Dict with keys: success (bool), count (int), total_area (float), total_perimeter (float), items (list), detail (str).
    """
    adapter = get_current_adapter()
    handles_to_check: List[str] = []

    layer_filter = spec.get("layer")
    if layer_filter:
        handles_to_check = adapter.select_by_layer(str(layer_filter).strip())
    else:
        handles_raw = spec.get("handles", "")
        if handles_raw and handles_raw != "all":
            if isinstance(handles_raw, list):
                handles_to_check = [str(h).strip() for h in handles_raw if str(h).strip()]
            else:
                handles_to_check = parse_handles(str(handles_raw))
        else:
            selected = adapter.get_selected_entities()
            if selected:
                handles_to_check = selected
            else:
                handles_to_check = (
                    adapter.select_by_type("LWPOLYLINE")
                    + adapter.select_by_type("POLYLINE")
                    + adapter.select_by_type("CIRCLE")
                )

    if not handles_to_check:
        return {
            "success": True,
            "count": 0,
            "total_area": 0.0,
            "total_perimeter": 0.0,
            "items": [],
            "detail": "No entities found to calculate area",
        }

    items = []
    total_area = 0.0
    total_perimeter = 0.0

    for h in handles_to_check:
        if hasattr(adapter, "get_entity_area"):
            info = adapter.get_entity_area(h)
        else:
            info = {"handle": h, "area": 0.0, "perimeter": 0.0, "layer": "0"}
        area_val = float(info.get("area", 0.0))
        perim_val = float(info.get("perimeter", 0.0))
        if area_val > 0.0 or perim_val > 0.0:
            total_area += area_val
            total_perimeter += perim_val
            items.append({
                "handle": h,
                "layer": info.get("layer", "0"),
                "type": info.get("object_name", "Entity"),
                "area": round(area_val, 2),
                "perimeter": round(perim_val, 2),
            })

    return {
        "success": True,
        "count": len(items),
        "total_area": round(total_area, 2),
        "total_perimeter": round(total_perimeter, 2),
        "unit": "m²",
        "items": items,
        "detail": (
            f"Calculated areas for {len(items)} entities. "
            f"Total Area: {total_area:.2f} m², Total Perimeter: {total_perimeter:.2f} m"
        ),
    }


def _area_table(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a CAD Area Schedule Table (Cuadro de Superficies) from closed entities.

    Args:
        spec: Operation spec with keys:
            - insertion_point (str or tuple, default "0,0")
            - layer (str, default "0")
            - title (str, default "CUADRO DE SUPERFICIES ÚTILES")
            - row_height (float, default 8.0)
            - col_width (float, default 40.0)

    Returns:
        Dict with keys: success (bool), table_handle (str), spaces_count (int), total_area (float), total_perimeter (float), detail (str).
    """
    adapter = get_current_adapter()
    target_layer = str(spec.get("layer", "0")).strip()

    if target_layer and target_layer != "0":
        handles = adapter.select_by_layer(target_layer)
    else:
        handles = (
            adapter.select_by_type("LWPOLYLINE")
            + adapter.select_by_type("POLYLINE")
            + adapter.select_by_type("CIRCLE")
        )

    if not handles:
        return {
            "success": False,
            "error": f"No measurable entities found on layer '{target_layer}'",
        }

    items = []
    total_area = 0.0
    total_perimeter = 0.0

    for h in handles:
        if hasattr(adapter, "get_entity_area"):
            info = adapter.get_entity_area(h)
        else:
            info = {"handle": h, "area": 0.0, "perimeter": 0.0, "layer": target_layer}
        a = float(info.get("area", 0.0))
        p = float(info.get("perimeter", 0.0))
        if a > 0.0:
            total_area += a
            total_perimeter += p
            items.append({
                "handle": h,
                "layer": info.get("layer", target_layer),
                "area": a,
                "perimeter": p,
            })

    if not items:
        return {
            "success": False,
            "error": "No closed spaces with area > 0 found",
        }

    title = str(spec.get("title", "CUADRO DE SUPERFICIES ÚTILES")).strip()
    headers = ["Nº", "Recinto / Capa", "Perímetro (m)", "Superficie (m²)", "% Total"]

    data_rows: List[List[str]] = []
    for idx, item in enumerate(items, 1):
        pct = (item["area"] / total_area * 100.0) if total_area > 0 else 0.0
        data_rows.append([
            str(idx),
            str(item["layer"]),
            f"{item['perimeter']:.2f}",
            f"{item['area']:.2f}",
            f"{pct:.1f}%",
        ])

    # Summary row
    data_rows.append([
        "TOTAL",
        "-",
        f"{total_perimeter:.2f}",
        f"{total_area:.2f}",
        "100.0%",
    ])

    raw_ins = spec.get("insertion_point", "0,0")
    if isinstance(raw_ins, (list, tuple)):
        ins_pt = (float(raw_ins[0]), float(raw_ins[1]))
    else:
        parts = str(raw_ins).split(",")
        ins_pt = (
            float(parts[0].strip()) if len(parts) > 0 else 0.0,
            float(parts[1].strip()) if len(parts) > 1 else 0.0,
        )

    row_h = float(spec.get("row_height", 8.0))
    col_w = float(spec.get("col_width", 40.0))

    try:
        table_handle = adapter.draw_table(
            insertion_point=ins_pt,
            num_rows=len(data_rows) + 2,  # +1 title, +1 headers
            num_cols=5,
            row_height=row_h,
            col_width=col_w,
            data=data_rows,
            title=title,
            headers=headers,
            layer="A-ANNO-TABL",
            color="white",
        )
        return {
            "success": True,
            "table_handle": table_handle,
            "spaces_count": len(items),
            "total_area": round(total_area, 2),
            "total_perimeter": round(total_perimeter, 2),
            "detail": (
                f"Generated CAD table '{title}' at {ins_pt} with {len(items)} spaces. "
                f"Total Area: {total_area:.2f} m²"
            ),
        }
    except Exception as e:
        logger.error(f"Failed to draw area schedule table: {e}")
        return {"success": False, "error": str(e)}


def _audit(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Audit drawing entities for CAD Quality Assurance (QA).

    Checks:
    - Entities drawn on layer '0'
    - Identifies basic drawing structure health

    Returns:
        Dict with keys: success (bool), qa_score (int), issues_count (int), issues (list), detail (str).
    """
    adapter = get_current_adapter()
    entities_layer_0 = adapter.select_by_layer("0")

    issues = []
    if entities_layer_0:
        issues.append({
            "type": "layer_0_entities",
            "severity": "warning",
            "count": len(entities_layer_0),
            "detail": (
                f"{len(entities_layer_0)} entities found on layer '0'. "
                "Best practice is to assign specific semantic layers."
            ),
            "handles": entities_layer_0[:10],
        })

    deductions = len(entities_layer_0) * 2
    score = max(0, 100 - min(deductions, 100))

    return {
        "success": True,
        "qa_score": score,
        "issues_count": len(issues),
        "issues": issues,
        "detail": (
            f"CAD QA Audit complete. Quality Score: {score}/100. "
            f"Issues detected: {len(issues)}."
        ),
    }


def _set_metadata(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Attach BIM / semantic metadata to entity handle."""
    adapter = get_current_adapter()
    handle = str(spec.get("handle") or spec.get("handles", "")).strip()
    if not handle:
        return {"success": False, "error": "Missing 'handle'"}

    key = spec.get("key")
    val = spec.get("value")
    metadata = spec.get("metadata")

    data = {}
    if metadata:
        if isinstance(metadata, str):
            try:
                data = json.loads(metadata)
            except Exception:
                data = {"data": metadata}
        elif isinstance(metadata, dict):
            data = metadata
    elif key is not None:
        data = {str(key): val}

    if hasattr(adapter, "set_entity_metadata"):
        adapter.set_entity_metadata(handle, data)
        return {
            "success": True,
            "handle": handle,
            "metadata": data,
            "detail": f"Attached metadata to entity #{handle}",
        }
    return {"success": False, "error": "Adapter does not support metadata attachment"}


def _get_metadata(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve BIM / semantic metadata from entity handle."""
    adapter = get_current_adapter()
    handle = str(spec.get("handle") or spec.get("handles", "")).strip()
    if not handle:
        return {"success": False, "error": "Missing 'handle'"}

    if hasattr(adapter, "get_entity_metadata"):
        data = adapter.get_entity_metadata(handle)
        return {"success": True, "handle": handle, "metadata": data}
    return {"success": False, "error": "Adapter does not support metadata retrieval"}


def _offset(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Offset an entity parallel to itself by distance."""
    adapter = get_current_adapter()
    handle = str(spec.get("handle") or spec.get("handles", "")).strip()
    distance = float(spec.get("distance", 1.0))
    side_point = spec.get("side_point")

    if not hasattr(adapter, "offset_entity"):
        return {"success": False, "error": "Adapter does not support offset operation"}

    new_handles = adapter.offset_entity(handle, distance, side_point=side_point)
    return {
        "success": bool(new_handles),
        "source_handle": handle,
        "distance": distance,
        "new_handles": new_handles,
        "count": len(new_handles),
    }


def _fillet(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Fillet two entities with radius (0.0 for sharp corner join)."""
    adapter = get_current_adapter()
    handles_raw = spec.get("handles") or spec.get("handle", "")
    if isinstance(handles_raw, list):
        handle_list = [str(h).strip() for h in handles_raw]
    else:
        handle_list = [h.strip() for h in str(handles_raw).split(",") if h.strip()]

    if len(handle_list) < 2:
        return {"success": False, "error": "'fillet' requires two entity handles (e.g. 'A1,B2')"}

    radius = float(spec.get("radius", 0.0))
    if not hasattr(adapter, "fillet_entities"):
        return {"success": False, "error": "Adapter does not support fillet operation"}

    res = adapter.fillet_entities(handle_list[0], handle_list[1], radius=radius)
    return {
        "success": bool(res),
        "handle1": handle_list[0],
        "handle2": handle_list[1],
        "radius": radius,
        "result": res,
    }


def _chamfer(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Chamfer two intersecting entities with setback distances."""
    adapter = get_current_adapter()
    handles_raw = spec.get("handles") or spec.get("handle", "")
    if isinstance(handles_raw, list):
        handle_list = [str(h).strip() for h in handles_raw]
    else:
        handle_list = [h.strip() for h in str(handles_raw).split(",") if h.strip()]

    if len(handle_list) < 2:
        return {"success": False, "error": "'chamfer' requires two entity handles (e.g. 'A1,B2')"}

    dist1 = float(spec.get("dist1") or spec.get("distance1", 0.5))
    dist2 = float(spec.get("dist2") or spec.get("distance2", dist1))

    if not hasattr(adapter, "chamfer_entities"):
        return {"success": False, "error": "Adapter does not support chamfer operation"}

    res = adapter.chamfer_entities(handle_list[0], handle_list[1], dist1=dist1, dist2=dist2)
    return {
        "success": bool(res),
        "handle1": handle_list[0],
        "handle2": handle_list[1],
        "dist1": dist1,
        "dist2": dist2,
        "result": res,
    }


def _explode(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Explode polyline or block reference into component primitives."""
    adapter = get_current_adapter()
    handles_raw = spec.get("handles") or spec.get("handle", "")
    if isinstance(handles_raw, list):
        handle_list = [str(h).strip() for h in handles_raw]
    else:
        handle_list = [h.strip() for h in str(handles_raw).split(",") if h.strip()]

    if not handle_list:
        return {"success": False, "error": "Missing entity handles to explode"}

    if not hasattr(adapter, "explode_entity"):
        return {"success": False, "error": "Adapter does not support explode operation"}

    all_new = []
    for h in handle_list:
        res = adapter.explode_entity(h)
        all_new.extend(res)

    return {
        "success": bool(all_new),
        "exploded_handles": handle_list,
        "new_handles": all_new,
        "count": len(all_new),
    }


def _matchprop(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Match properties from source entity to target entities."""
    adapter = get_current_adapter()
    src = str(spec.get("source_handle") or spec.get("source", "")).strip()
    targets_raw = spec.get("target_handles") or spec.get("targets") or spec.get("handles", "")
    if isinstance(targets_raw, list):
        target_list = [str(h).strip() for h in targets_raw]
    else:
        target_list = [h.strip() for h in str(targets_raw).split(",") if h.strip()]

    if not src or not target_list:
        return {"success": False, "error": "'matchprop' requires 'source_handle' and 'target_handles'"}

    if not hasattr(adapter, "match_properties"):
        return {"success": False, "error": "Adapter does not support match_properties operation"}

    success = adapter.match_properties(src, target_list)
    return {
        "success": success,
        "source_handle": src,
        "target_count": len(target_list),
    }


def _boundary(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Create a boundary polyline around an internal coordinate."""
    adapter = get_current_adapter()
    point_raw = spec.get("point") or spec.get("internal_point") or spec.get("coords") or "0,0"
    from mcp_tools.helpers import parse_coordinate
    pt = parse_coordinate(point_raw)
    layer = spec.get("layer", "A-BOUND")

    if not hasattr(adapter, "create_boundary"):
        return {"success": False, "error": "Adapter does not support boundary creation"}

    handle = adapter.create_boundary(pt, layer=layer)
    return {
        "success": bool(handle),
        "handle": handle,
        "probe_point": pt,
        "layer": layer,
    }


def _join(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Join loose connected lines/arcs into a continuous polyline."""
    adapter = get_current_adapter()
    handles_raw = spec.get("handles") or spec.get("handle", "")
    if isinstance(handles_raw, list):
        handle_list = [str(h).strip() for h in handles_raw]
    else:
        handle_list = [h.strip() for h in str(handles_raw).split(",") if h.strip()]

    if len(handle_list) < 2:
        return {"success": False, "error": "'join' requires at least two entity handles (e.g. 'A1,B2')"}

    tolerance = float(spec.get("tolerance", 0.05))
    if not hasattr(adapter, "join_entities"):
        return {"success": False, "error": "Adapter does not support join operation"}

    res = adapter.join_entities(handle_list, tolerance=tolerance)
    return {
        "success": bool(res),
        "handle": res,
        "joined_count": len(handle_list),
        "tolerance": tolerance,
    }


def _trim(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Trim a line against a boundary cutting edge."""
    adapter = get_current_adapter()
    handle = str(spec.get("handle") or spec.get("target", "")).strip()
    boundary = str(spec.get("boundary") or spec.get("cutting_edge") or spec.get("boundary_handle", "")).strip()

    if not handle or not boundary:
        return {"success": False, "error": "'trim' requires 'handle' and 'boundary'"}

    if not hasattr(adapter, "trim_extend_entity"):
        return {"success": False, "error": "Adapter does not support trim operation"}

    success = adapter.trim_extend_entity(handle, boundary, mode="trim")
    return {"success": success, "handle": handle, "boundary": boundary, "mode": "trim"}


def _extend(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Extend a line to touch a boundary edge."""
    adapter = get_current_adapter()
    handle = str(spec.get("handle") or spec.get("target", "")).strip()
    boundary = str(spec.get("boundary") or spec.get("boundary_handle", "")).strip()

    if not handle or not boundary:
        return {"success": False, "error": "'extend' requires 'handle' and 'boundary'"}

    if not hasattr(adapter, "trim_extend_entity"):
        return {"success": False, "error": "Adapter does not support extend operation"}

    success = adapter.trim_extend_entity(handle, boundary, mode="extend")
    return {"success": success, "handle": handle, "boundary": boundary, "mode": "extend"}


# Dispatch table: action -> (handler, required_fields)
ENTITY_DISPATCH: Dict[str, Tuple[Callable, List[str]]] = {
    "select": (_select, ["by", "value"]),
    "move": (_move, ["handles", "offset_x", "offset_y"]),
    "rotate": (_rotate, ["handles", "center_x", "center_y", "angle"]),
    "scale": (_scale, ["handles", "center_x", "center_y", "scale_factor"]),
    "set_color": (_set_color, ["handles", "color"]),
    "set_layer": (_set_layer, ["handles", "layer_name"]),
    "set_color_bylayer": (_set_color_bylayer, ["handles"]),
    "copy": (_copy, ["handles"]),
    "paste": (_paste, ["base_point"]),
    "delete": (_delete, ["handles"]),
    "area": (_area, []),
    "area_table": (_area_table, []),
    "audit": (_audit, []),
    "set_metadata": (_set_metadata, []),
    "get_metadata": (_get_metadata, []),
    "offset": (_offset, []),
    "fillet": (_fillet, []),
    "chamfer": (_chamfer, []),
    "explode": (_explode, []),
    "matchprop": (_matchprop, []),
    "boundary": (_boundary, []),
    "join": (_join, []),
    "trim": (_trim, []),
    "extend": (_extend, []),
}




def _validate_required_fields(
    spec: Dict[str, Any], required: List[str], action: str
) -> Optional[str]:
    """Validate that required fields are present in spec.

    Args:
        spec: Operation spec dict to validate.
        required: List of field names that must be present.
        action: Action name used in the error message.

    Returns:
        Error message string if any fields are missing, otherwise None.
    """
    missing = [f for f in required if f not in spec]
    if missing:
        return f"'{action}' requires fields: {', '.join(missing)}"
    return None


# ========== Tool Registration ==========


def register_entity_tools(mcp):
    """Register unified entity management tool with FastMCP."""

    @cad_tool(mcp, "manage_entities")
    def manage_entities(
        operations: str,
    ) -> str:
        """
        Manage entities: select, transform, restyle, copy/paste.

        Args:
            operations: Operations in SHORTHAND format (one per line):

                select|by|value               → select|layer|walls
                move|handles|offset_x|offset_y → move|A1,B2|10|5
                rotate|handles|angle|cx|cy    → rotate|A1|45|0|0
                scale|handles|factor|cx|cy    → scale|A1|2.0|0|0
                set_color|handles|color       → set_color|A1,B2|red
                set_layer|handles|layer       → set_layer|A1|walls
                set_color_bylayer|handles     → set_color_bylayer|A1,B2
                copy|handles                  → copy|A1,B2
                paste|base_point              → paste|100,200
                delete|handles                → delete|A1,B2
                area|handles                  → area|A1,B2 (or area|layer|A-ROOMS)
                area_table|ins_x,ins_y|layer  → area_table|0,0|A-ROOMS|Cuadro Áreas

                "handles" = comma-separated entity handles (e.g. "A1B2,C3D4")
                "by" = "color", "layer", or "type"

                Example:
                    select|layer|walls
                    move|A1B2,C3D4|10|5
                    area|layer|A-ESTANCIAS
                    area_table|100,100|A-ESTANCIAS|Cuadro de Superficies
                    set_color|A1B2,C3D4|red

                JSON format also supported for backwards compatibility.



        Returns:
            JSON result with per-operation status
        """
        try:
            ops_data = parse_entity_ops_input(operations)
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid input: {str(e)}",
                    "total": 0,
                    "succeeded": 0,
                    "results": [],
                },
                indent=2,
            )

        results = []

        for i, spec in enumerate(ops_data):
            action = spec.get("action")

            if not action:
                results.append(
                    {
                        "index": i,
                        "success": False,
                        "error": "Missing 'action' field. Supported: "
                        + ", ".join(ENTITY_DISPATCH.keys()),
                    }
                )
                continue

            action_lower = action.lower()
            dispatch_entry = ENTITY_DISPATCH.get(action_lower)

            if not dispatch_entry:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": f"Unknown action '{action}'. Supported: "
                        + ", ".join(ENTITY_DISPATCH.keys()),
                    }
                )
                continue

            handler, required_fields = dispatch_entry

            field_error = _validate_required_fields(spec, required_fields, action_lower)
            if field_error:
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": field_error,
                    }
                )
                continue

            try:
                result = handler(spec)
                results.append({"index": i, "action": action_lower, **result})
            except ValidationError as e:
                error_msg = f"Validation error: {e.errors()[0]['msg']}"
                logger.error(
                    f"Validation error in entity op {i} ({action_lower}): {error_msg}"
                )
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": error_msg,
                    }
                )
            except Exception as e:
                logger.error(f"Error in entity op {i} ({action_lower}): {e}")
                results.append(
                    {
                        "index": i,
                        "action": action_lower,
                        "success": False,
                        "error": str(e),
                    }
                )

        return json.dumps(
            {
                "total": len(ops_data),
                "succeeded": sum(1 for r in results if r.get("success")),
                "results": results,
            },
            indent=2,
        )
