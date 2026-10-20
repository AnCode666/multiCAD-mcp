"""
Shorthand parser for MCP tool inputs.

Converts compact pipe-separated format to structured dictionaries.
Supports ~85% token reduction compared to JSON format.

Format: type|param1|param2|param3|...
Multiple entries: one per line or separated by ;

Examples:
    line|0,0|10,10|red|walls
    circle|5,5|3|blue
    rect|0,0|20,15
"""

import json
from typing import Any, Dict, List, Tuple, Union

from mcp_tools.validator import autocorrect_spec


# Type alias for field definitions: (field_name, required, default_value)
FieldDef = Tuple[str, bool, Any]
FieldList = List[FieldDef]

# ========== Drawing Entity Parsers ==========

# Field definitions for each entity type
# Format: (field_name, required, default_value)
ENTITY_FIELDS: Dict[str, FieldList] = {
    "line": [
        ("start", True, None),
        ("end", True, None),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "circle": [
        ("center", True, None),
        ("radius", True, None),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "rect": [
        ("corner1", True, None),
        ("corner2", True, None),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "rectangle": [
        ("corner1", True, None),
        ("corner2", True, None),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "text": [
        ("position", True, None),
        ("text", True, None),
        ("height", False, 2.5),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "arc": [
        ("center", True, None),
        ("radius", True, None),
        ("start_angle", True, None),
        ("end_angle", True, None),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "polyline": [
        ("points", True, None),  # semicolon-separated
        ("closed", False, False),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "spline": [
        ("points", True, None),  # semicolon-separated
        ("closed", False, False),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "dimension": [
        ("start", True, None),
        ("end", True, None),
        ("color", False, "white"),
        ("layer", False, "0"),
        ("text", False, None),
        ("offset", False, 10.0),
    ],
    "leader": [
        ("points", True, None),  # semicolon-separated
        ("text", False, None),
        ("text_height", False, 2.5),
        ("color", False, "white"),
        ("layer", False, "0"),
        ("leader_type", False, "line_with_arrow"),
    ],
    "mleader": [
        ("base_point", True, None),
        ("leader_groups", True, None),  # double-tilde-separated groups
        ("text", False, None),
        ("text_height", False, 2.5),
        ("color", False, "white"),
        ("layer", False, "0"),
        ("arrow_style", False, "_ARROW"),
    ],
    "table": [
        ("insertion_point", True, None),
        ("num_rows", True, None),
        ("num_cols", True, None),
        ("row_height", False, 3.0),
        ("col_width", False, 15.0),
        ("title", False, None),
        ("headers", False, None),
        ("data", False, None),
        ("color", False, "white"),
        ("layer", False, "0"),
    ],
    "wall": [
        ("start", True, None),
        ("end", True, None),
        ("thickness", False, 0.15),
        ("color", False, "red"),
        ("layer", False, "A-MURO-ESTR"),
    ],
    "door": [
        ("hinge", True, None),
        ("width", False, 0.82),
        ("angle", False, 0.0),
        ("color", False, "green"),
        ("layer", False, "A-CARP-PUER"),
    ],
    "window": [
        ("start", True, None),
        ("end", True, None),
        ("thickness", False, 0.10),
        ("color", False, "cyan"),
        ("layer", False, "A-CARP-VENT"),
    ],
}

# Type aliases for entities
ENTITY_ALIASES = {
    "rect": "rectangle",
    "tab": "table",
    "muro": "wall",
    "puerta": "door",
    "ventana": "window",
}


def _parse_bool(value: str) -> bool:
    """Parse boolean from string."""
    return value.lower() in ("true", "1", "yes", "closed", "on")


def _try_number(value: str) -> Union[str, int, float]:
    """Try to convert string to number."""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _convert_points_format(points_str: str) -> str:
    """Convert semicolon-separated points to pipe-separated for adapter."""
    # Input: "0,0;10,10;20,0"
    # Output: "0,0|10,10|20,0"
    return points_str.replace(";", "|")


def parse_entity_shorthand(line: str) -> Dict[str, Any]:
    """
    Parse a single entity shorthand line.

    Args:
        line: Shorthand string like "line|0,0|10,10|red|walls"

    Returns:
        Dictionary with type and fields
    """
    parts = [p.strip() for p in line.split("|")]
    if not parts:
        return {"error": "Empty input"}

    entity_type = parts[0].lower()

    # Handle type aliases
    canonical_type = ENTITY_ALIASES.get(entity_type, entity_type)

    if canonical_type not in ENTITY_FIELDS:
        return {"type": entity_type, "error": f"Unknown type: {entity_type}"}

    fields = ENTITY_FIELDS[canonical_type]
    spec: Dict[str, Any] = {"type": canonical_type}

    # Map positional arguments to fields
    for i, (field_name, required, default) in enumerate(fields):
        value_index = i + 1  # +1 because index 0 is the type

        if value_index < len(parts) and parts[value_index]:
            value = parts[value_index]

            # Special handling for specific fields
            if field_name == "closed":
                spec[field_name] = _parse_bool(value)
            elif field_name == "points":
                # Convert semicolon to pipe for adapter
                spec[field_name] = _convert_points_format(value)
            elif field_name == "leader_groups":
                # Convert double-tilde separated groups, each with semicolon-separated points
                # Input: "0,0;10,10~~0,0;20,-5"
                # Output: "0,0|10,10~~0,0|20,-5" (for adapter)
                groups = []
                for group_str in value.split("~~"):
                    group_str = group_str.strip()
                    if group_str:
                        converted = _convert_points_format(group_str)
                        groups.append(converted)
                spec[field_name] = "~~".join(groups)
            elif field_name in (
                "radius",
                "height",
                "start_angle",
                "end_angle",
                "offset",
                "text_height",
                "row_height",
                "col_width",
                "num_rows",
                "num_cols",
                "thickness",
                "width",
                "angle",
            ):
                spec[field_name] = _try_number(value)
            else:
                spec[field_name] = value
        elif default is not None:
            spec[field_name] = default
        elif not required:
            pass  # Optional field with no default, skip

    return autocorrect_spec(spec, "entity")


# ========== Entity Operations Parser ==========

ENTITY_OP_FIELDS: Dict[str, FieldList] = {
    "select": [
        ("by", True, None),
        ("value", True, None),
    ],
    "move": [
        ("handles", True, None),
        ("offset_x", True, None),
        ("offset_y", True, None),
    ],
    "rotate": [
        ("handles", True, None),
        ("angle", True, None),
        ("center_x", False, 0),
        ("center_y", False, 0),
    ],
    "scale": [
        ("handles", True, None),
        ("scale_factor", True, None),
        ("center_x", False, 0),
        ("center_y", False, 0),
    ],
    "set_color": [
        ("handles", True, None),
        ("color", True, None),
    ],
    "set_layer": [
        ("handles", True, None),
        ("layer_name", True, None),
    ],
    "set_color_bylayer": [
        ("handles", True, None),
    ],
    "copy": [
        ("handles", True, None),
    ],
    "paste": [
        ("base_point", True, None),
    ],
    "delete": [
        ("handles", True, None),
    ],
    "area": [
        ("handles", False, "all"),
        ("layer", False, None),
    ],
    "area_table": [
        ("insertion_point", False, "0,0"),
        ("layer", False, "0"),
        ("title", False, "CUADRO DE SUPERFICIES ÚTILES"),
        ("row_height", False, 8.0),
        ("col_width", False, 40.0),
    ],
    "audit": [],
    "set_metadata": [
        ("handle", True, None),
        ("key", False, None),
        ("value", False, None),
    ],
    "get_metadata": [
        ("handle", True, None),
    ],
    "offset": [
        ("handle", True, None),
        ("distance", True, None),
        ("side_point", False, None),
    ],
    "fillet": [
        ("handles", True, None),
        ("radius", False, 0.0),
    ],
    "chamfer": [
        ("handles", True, None),
        ("dist1", False, 0.5),
        ("dist2", False, 0.5),
    ],
    "explode": [
        ("handles", True, None),
    ],
    "matchprop": [
        ("source_handle", True, None),
        ("target_handles", True, None),
    ],
}



def parse_entity_op_shorthand(line: str) -> Dict[str, Any]:
    """
    Parse an entity operation shorthand line.

    Args:
        line: Shorthand like "move|A1,B2|10|5", "area|A1,B2", or "area_table|0,0|A-ESTANCIAS"

    Returns:
        Dictionary with action and fields
    """
    parts = [p.strip() for p in line.split("|")]
    if not parts:
        return {"error": "Empty input"}

    action = parts[0].lower()

    if action not in ENTITY_OP_FIELDS:
        return {"action": action, "error": f"Unknown action: {action}"}

    # Special handling for area|layer|layer_name
    if action == "area" and len(parts) >= 3 and parts[1].lower() == "layer":
        return autocorrect_spec(
            {"action": "area", "handles": "", "layer": parts[2]}, "entity_op"
        )

    fields = ENTITY_OP_FIELDS[action]
    spec: Dict[str, Any] = {"action": action}

    for i, (field_name, required, default) in enumerate(fields):
        value_index = i + 1

        if value_index < len(parts) and parts[value_index]:
            value = parts[value_index]

            # Convert numeric fields
            if field_name in (
                "offset_x",
                "offset_y",
                "angle",
                "scale_factor",
                "center_x",
                "center_y",
                "row_height",
                "col_width",
                "distance",
                "radius",
                "dist1",
                "dist2",
            ):
                spec[field_name] = _try_number(value)
            else:
                spec[field_name] = value

        elif default is not None:
            spec[field_name] = default

    return autocorrect_spec(spec, "entity_op")


# ========== Layer Operations Parser ==========

LAYER_OP_FIELDS: Dict[str, FieldList] = {
    "create": [
        ("name", True, None),
        ("color", False, "white"),
        ("lineweight", False, 25),
    ],
    "delete": [
        ("name", True, None),
    ],
    "rename": [
        ("old_name", True, None),
        ("new_name", True, None),
    ],
    "on": [
        ("names", True, None),  # comma-separated
    ],
    "turn_on": [
        ("names", True, None),
    ],
    "off": [
        ("names", True, None),
    ],
    "turn_off": [
        ("names", True, None),
    ],
    "set_color": [
        ("name", True, None),
        ("color", True, None),
    ],
    "list": [],
    "info": [],
    "is_on": [
        ("name", True, None),
    ],
    "template": [
        ("name", False, "aeco"),
    ],
    "purge": [],
}

# Action aliases for layers
LAYER_ACTION_ALIASES = {
    "on": "turn_on",
    "off": "turn_off",
    "plantilla": "template",
    "purgar": "purge",
}


def parse_layer_op_shorthand(line: str) -> Dict[str, Any]:
    """
    Parse a layer operation shorthand line.

    Args:
        line: Shorthand like "create|walls|red|50"

    Returns:
        Dictionary with action and fields
    """
    parts = [p.strip() for p in line.split("|")]
    if not parts:
        return {"error": "Empty input"}

    action = parts[0].lower()

    # Handle action aliases
    canonical_action = LAYER_ACTION_ALIASES.get(action, action)

    if canonical_action not in LAYER_OP_FIELDS:
        return {"action": action, "error": f"Unknown action: {action}"}

    fields = LAYER_OP_FIELDS[canonical_action]
    spec: Dict[str, Any] = {"action": canonical_action}

    for i, (field_name, required, default) in enumerate(fields):
        value_index = i + 1

        if value_index < len(parts) and parts[value_index]:
            value = parts[value_index]

            # Convert numeric fields
            if field_name == "lineweight":
                spec[field_name] = _try_number(value)
            elif field_name == "names":
                # Keep as comma-separated string, convert to list
                spec[field_name] = [n.strip() for n in value.split(",")]
            else:
                spec[field_name] = value
        elif default is not None:
            spec[field_name] = default

    return autocorrect_spec(spec, "layer_op")


# ========== Block Operations Parser ==========

BLOCK_OP_FIELDS: Dict[str, FieldList] = {
    "list": [],
    "info": [
        ("block_name", True, None),
        ("include", False, "info"),
    ],
    "insert": [
        ("block_name", True, None),
        ("insertion_point", True, None),
        ("scale", False, 1.0),
        ("rotation", False, 0.0),
        ("layer", False, "0"),
        ("color", False, "white"),
    ],
    "create": [
        ("block_name", True, None),
        ("entity_handles", False, None),  # comma-separated
        ("insertion_point", False, "0,0"),
        ("description", False, ""),
    ],
    "get_attrs": [
        ("handle", True, None),
    ],
    "set_attrs": [
        ("handle", True, None),
        ("attributes", True, None),  # JSON string: {"TAG": "value"}
    ],
}


def parse_block_op_shorthand(line: str) -> Dict[str, Any]:
    """
    Parse a block operation shorthand line.

    Args:
        line: Shorthand like "insert|Door|10,20|1.5|90|walls"

    Returns:
        Dictionary with action and fields
    """
    parts = [p.strip() for p in line.split("|")]
    if not parts:
        return {"error": "Empty input"}

    action = parts[0].lower()

    if action not in BLOCK_OP_FIELDS:
        return {"action": action, "error": f"Unknown action: {action}"}

    fields = BLOCK_OP_FIELDS[action]
    spec: Dict[str, Any] = {"action": action}

    for i, (field_name, required, default) in enumerate(fields):
        value_index = i + 1

        if value_index < len(parts) and parts[value_index]:
            value = parts[value_index]

            # Convert numeric fields
            if field_name in ("scale", "rotation"):
                spec[field_name] = _try_number(value)
            elif field_name == "entity_handles":
                # Keep as list
                spec[field_name] = [h.strip() for h in value.split(",")]
            else:
                spec[field_name] = value
        elif default is not None:
            spec[field_name] = default

    return autocorrect_spec(spec, "block_op")


# ========== File Operations Parser ==========

FILE_OP_FIELDS: Dict[str, FieldList] = {
    "save": [
        ("filepath", False, None),
        ("filename", False, None),
        ("format", False, "dwg"),
    ],
    "new": [],
    "close": [
        ("save_changes", False, False),
    ],
    "list": [],
    "switch": [
        ("drawing_name", True, None),
    ],
}


def parse_file_op_shorthand(line: str) -> Dict[str, Any]:
    """
    Parse a file operation shorthand line.

    Args:
        line: Shorthand like "save|/path/to/file.dwg" or "switch|floor_plan.dwg"

    Returns:
        Dictionary with action and fields
    """
    parts = [p.strip() for p in line.split("|")]
    if not parts:
        return {"error": "Empty input"}

    action = parts[0].lower()

    if action not in FILE_OP_FIELDS:
        return {"action": action, "error": f"Unknown action: {action}"}

    fields = FILE_OP_FIELDS[action]
    spec: Dict[str, Any] = {"action": action}

    # Special handling for save - detect if path or filename
    if action == "save" and len(parts) > 1:
        path_value = parts[1]
        if "/" in path_value or "\\" in path_value:
            spec["filepath"] = path_value
        else:
            spec["filename"] = path_value
        # Format from third part if present
        if len(parts) > 2:
            spec["format"] = parts[2]
        return autocorrect_spec(spec, "file_op")

    for i, (field_name, required, default) in enumerate(fields):
        value_index = i + 1

        if value_index < len(parts) and parts[value_index]:
            value = parts[value_index]

            if field_name == "save_changes":
                spec[field_name] = _parse_bool(value)
            else:
                spec[field_name] = value
        elif default is not None:
            spec[field_name] = default

    return autocorrect_spec(spec, "file_op")


# ========== Main Parser Functions ==========


def _split_entries(input_str: str) -> List[str]:
    """
    Split input into individual entries.

    Handles:
    - Newline-separated entries
    - Semicolon-separated entries (on same line)
    - Mixed formats
    """
    # First split by newlines
    lines = input_str.strip().split("\n")

    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line contains semicolons outside of coordinates
        # Coordinates use format "x,y" or "x;y" for points in polylines
        # We need to distinguish "line|0,0|10,10;circle|5,5|3" from "polyline|0,0;10,10;20,0"

        # Simple heuristic: if the part after semicolon starts with a known type/action, split
        # Otherwise, keep as single entry
        if ";" in line:
            # Check if it looks like multiple entries
            test_parts = line.split(";")
            is_multi_entry = False

            for part in test_parts[1:]:
                first_word = part.strip().split("|")[0].lower() if "|" in part else ""
                if first_word in ENTITY_FIELDS or first_word in ENTITY_OP_FIELDS:
                    is_multi_entry = True
                    break

            if is_multi_entry:
                entries.extend([p.strip() for p in test_parts if p.strip()])
            else:
                entries.append(line)
        else:
            entries.append(line)

    return entries


def parse_drawing_input(
    input_data: Union[str, List[Any], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Parse drawing entities from shorthand, JSON string, or structured objects.

    Args:
        input_data: Shorthand string, JSON string, dict, or list of entities

    Returns:
        List of entity specifications
    """
    if isinstance(input_data, dict):
        return [autocorrect_spec(input_data, "entity")]
    if isinstance(input_data, list):
        res = []
        for item in input_data:
            if isinstance(item, dict):
                res.append(autocorrect_spec(item, "entity"))
            elif isinstance(item, str):
                res.append(parse_entity_shorthand(item.strip()))
        return res

    input_str = str(input_data).strip()

    # Detect JSON
    if input_str.startswith("[") or input_str.startswith("{"):
        try:
            data = json.loads(input_str)
            if isinstance(data, dict):
                return [autocorrect_spec(data, "entity")]
            return [autocorrect_spec(item, "entity") for item in data]
        except json.JSONDecodeError:
            pass  # Fall through to shorthand parsing

    # Parse as shorthand
    entries = _split_entries(input_str)
    return [parse_entity_shorthand(entry) for entry in entries]


def parse_entity_ops_input(
    input_data: Union[str, List[Any], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Parse entity operations from shorthand, JSON string, or structured objects.

    Args:
        input_data: Shorthand string, JSON string, dict, or list of operations

    Returns:
        List of operation specifications
    """
    if isinstance(input_data, dict):
        return [autocorrect_spec(input_data, "entity_op")]
    if isinstance(input_data, list):
        res = []
        for item in input_data:
            if isinstance(item, dict):
                res.append(autocorrect_spec(item, "entity_op"))
            elif isinstance(item, str):
                res.append(parse_entity_op_shorthand(item.strip()))
        return res

    input_str = str(input_data).strip()

    # Detect JSON
    if input_str.startswith("[") or input_str.startswith("{"):
        try:
            data = json.loads(input_str)
            if isinstance(data, dict):
                return [autocorrect_spec(data, "entity_op")]
            return [autocorrect_spec(item, "entity_op") for item in data]
        except json.JSONDecodeError:
            pass

    entries = _split_entries(input_str)
    return [parse_entity_op_shorthand(entry) for entry in entries]


def parse_layer_ops_input(
    input_data: Union[str, List[Any], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Parse layer operations from shorthand, JSON string, or structured objects.

    Args:
        input_data: Shorthand string, JSON string, dict, or list of operations

    Returns:
        List of operation specifications
    """
    if isinstance(input_data, dict):
        return [autocorrect_spec(input_data, "layer_op")]
    if isinstance(input_data, list):
        res = []
        for item in input_data:
            if isinstance(item, dict):
                res.append(autocorrect_spec(item, "layer_op"))
            elif isinstance(item, str):
                res.append(parse_layer_op_shorthand(item.strip()))
        return res

    input_str = str(input_data).strip()

    # Detect JSON
    if input_str.startswith("[") or input_str.startswith("{"):
        try:
            data = json.loads(input_str)
            if isinstance(data, dict):
                return [autocorrect_spec(data, "layer_op")]
            return [autocorrect_spec(item, "layer_op") for item in data]
        except json.JSONDecodeError:
            pass

    entries = _split_entries(input_str)
    return [parse_layer_op_shorthand(entry) for entry in entries]


def parse_block_ops_input(
    input_data: Union[str, List[Any], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Parse block operations from shorthand, JSON string, or structured objects.

    Args:
        input_data: Shorthand string, JSON string, dict, or list of operations

    Returns:
        List of operation specifications
    """
    if isinstance(input_data, dict):
        return [autocorrect_spec(input_data, "block_op")]
    if isinstance(input_data, list):
        res = []
        for item in input_data:
            if isinstance(item, dict):
                res.append(autocorrect_spec(item, "block_op"))
            elif isinstance(item, str):
                res.append(parse_block_op_shorthand(item.strip()))
        return res

    input_str = str(input_data).strip()

    # Detect JSON
    if input_str.startswith("[") or input_str.startswith("{"):
        try:
            data = json.loads(input_str)
            if isinstance(data, dict):
                return [autocorrect_spec(data, "block_op")]
            return [autocorrect_spec(item, "block_op") for item in data]
        except json.JSONDecodeError:
            pass

    entries = _split_entries(input_str)
    return [parse_block_op_shorthand(entry) for entry in entries]


def parse_file_ops_input(
    input_data: Union[str, List[Any], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Parse file operations from shorthand, JSON string, or structured objects.

    Args:
        input_data: Shorthand string, JSON string, dict, or list of operations

    Returns:
        List of operation specifications
    """
    if isinstance(input_data, dict):
        return [autocorrect_spec(input_data, "file_op")]
    if isinstance(input_data, list):
        res = []
        for item in input_data:
            if isinstance(item, dict):
                res.append(autocorrect_spec(item, "file_op"))
            elif isinstance(item, str):
                res.append(parse_file_op_shorthand(item.strip()))
        return res

    input_str = str(input_data).strip()

    # Detect JSON
    if input_str.startswith("[") or input_str.startswith("{"):
        try:
            data = json.loads(input_str)
            if isinstance(data, dict):
                return [autocorrect_spec(data, "file_op")]
            return [autocorrect_spec(item, "file_op") for item in data]
        except json.JSONDecodeError:
            pass

    entries = _split_entries(input_str)
    return [parse_file_op_shorthand(entry) for entry in entries]


# ========== Session Operations Parser ==========

SESSION_OP_FIELDS: Dict[str, FieldList] = {
    "zoom_extents": [],
    "zoom_window": [
        ("corner1", True, None),
        ("corner2", True, None),
    ],
    "zoom_center": [
        ("center", True, None),
        ("magnification", False, 1.0),
    ],
    "set_view_preset": [
        ("preset", True, None),
    ],
    "set_visual_style": [
        ("style", True, None),
    ],
    "undo": [
        ("count", False, 1),
    ],
    "redo": [
        ("count", False, 1),
    ],
    "screenshot": [],
    "export_view": [],
    "connect": [],
    "disconnect": [],
    "status": [],
    "list_supported": [],
    "check_running": [],
    "open_dashboard": [
        ("host", False, None),
        ("port", False, None),
    ],
}

SESSION_ALIASES = {
    "ze": "zoom_extents",
    "zw": "zoom_window",
    "zc": "zoom_center",
    "preset": "set_view_preset",
    "view": "set_view_preset",
    "style": "set_visual_style",
    "preview": "export_view",
}


def parse_session_op_shorthand(line: str) -> Dict[str, Any]:
    """Parse a session or view operation shorthand line.

    Examples:
        - "ze" -> {"action": "zoom_extents"}
        - "zw|0,0|100,100" -> {"action": "zoom_window", "corner1": "0,0", "corner2": "100,100"}
        - "preset|top" -> {"action": "set_view_preset", "preset": "top"}
        - "style|conceptual" -> {"action": "set_visual_style", "style": "conceptual"}
        - "undo|2" -> {"action": "undo", "count": 2}
    """
    parts = [p.strip() for p in line.split("|")]
    if not parts:
        return {"error": "Empty input"}

    raw_action = parts[0].lower()
    action = SESSION_ALIASES.get(raw_action, raw_action)

    if action not in SESSION_OP_FIELDS:
        return {"action": action, "error": f"Unknown action: {action}"}

    fields = SESSION_OP_FIELDS[action]
    spec: Dict[str, Any] = {"action": action}

    for i, (field_name, required, default) in enumerate(fields):
        value_index = i + 1
        if value_index < len(parts) and parts[value_index]:
            val = parts[value_index]
            if field_name in ("count", "magnification", "port"):
                spec[field_name] = _try_number(val)
            else:
                spec[field_name] = val
        elif default is not None:
            spec[field_name] = default

    return spec


def parse_session_input(
    input_data: Union[str, List[Any], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Parse session/view operations from shorthand, JSON string, or structured objects."""
    if isinstance(input_data, dict):
        return [input_data]
    if isinstance(input_data, list):
        res = []
        for item in input_data:
            if isinstance(item, dict):
                res.append(item)
            elif isinstance(item, str):
                res.append(parse_session_op_shorthand(item.strip()))
        return res

    input_str = str(input_data).strip()
    if input_str.startswith("[") or input_str.startswith("{"):
        try:
            data = json.loads(input_str)
            if isinstance(data, dict):
                return [data]
            return list(data)
        except json.JSONDecodeError:
            pass

    entries = _split_entries(input_str)
    return [parse_session_op_shorthand(entry) for entry in entries]

