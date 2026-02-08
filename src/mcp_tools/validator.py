"""
Auto-correction and validation for MCP tool inputs.

Provides:
- Fuzzy color name matching
- Type coercion (string to number)
- Case normalization
- Default value application
- Coordinate format normalization
"""

import difflib
from typing import Any, Dict, List, Optional, Union


# ========== Color Constants ==========

VALID_COLORS = [
    "black",
    "red",
    "yellow",
    "green",
    "cyan",
    "blue",
    "magenta",
    "white",
    "gray",
    "light_gray",
    "dark_gray",
    "orange",
    "bylayer",
]

# Common typos and aliases
COLOR_ALIASES = {
    "grey": "gray",
    "light_grey": "light_gray",
    "dark_grey": "dark_gray",
    "lightgray": "light_gray",
    "darkgray": "dark_gray",
    "lightgrey": "light_gray",
    "darkgrey": "dark_gray",
    "purple": "magenta",
    "violet": "magenta",
    "aqua": "cyan",
    "teal": "cyan",
}


def fuzzy_match_color(color_input: str, threshold: float = 0.6) -> str:
    """
    Match a possibly misspelled color to a valid color name.

    Args:
        color_input: User-provided color string
        threshold: Minimum similarity ratio (0.0-1.0)

    Returns:
        Corrected color name, or original if no match found
    """
    if not isinstance(color_input, str):
        return str(color_input)

    color_lower = color_input.lower().strip()

    # Direct match
    if color_lower in VALID_COLORS:
        return color_lower

    # Alias match
    if color_lower in COLOR_ALIASES:
        return COLOR_ALIASES[color_lower]

    # Numeric color (ACI index)
    try:
        int(color_lower)
        return color_lower  # Pass through numeric colors
    except ValueError:
        pass

    # Fuzzy match
    matches = difflib.get_close_matches(
        color_lower, VALID_COLORS, n=1, cutoff=threshold
    )

    if matches:
        return matches[0]

    # Check aliases with fuzzy matching
    alias_matches = difflib.get_close_matches(
        color_lower, list(COLOR_ALIASES.keys()), n=1, cutoff=threshold
    )

    if alias_matches:
        return COLOR_ALIASES[alias_matches[0]]

    # No match - return original (will be handled by adapter)
    return color_input


# ========== Type Coercion ==========


def coerce_number(value: Any, field_name: str = "") -> Union[int, float, Any]:
    """
    Convert string numbers to actual numbers.

    Args:
        value: Value to convert
        field_name: Field name for context (optional)

    Returns:
        Converted number or original value
    """
    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        value = value.strip()

        # Handle quoted numbers
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

    return value


def coerce_bool(value: Any) -> bool:
    """
    Convert various boolean representations to bool.

    Args:
        value: Value to convert

    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on", "closed")

    if isinstance(value, (int, float)):
        return bool(value)

    return False


# ========== Coordinate Normalization ==========


def normalize_coordinate(coord: Any) -> str:
    """
    Normalize coordinate formats.

    Handles:
    - "x,y" and "x;y" -> "x,y"
    - "x, y" (with spaces) -> "x,y"
    - (x, y) tuples -> "x,y"
    - [x, y] lists -> "x,y"

    Args:
        coord: Coordinate in various formats

    Returns:
        Normalized "x,y" or "x,y,z" string
    """
    if isinstance(coord, str):
        # Replace semicolons with commas
        coord = coord.replace(";", ",")
        # Remove spaces around separators
        parts = [p.strip() for p in coord.split(",")]
        return ",".join(parts)

    if isinstance(coord, (list, tuple)):
        return ",".join(str(c) for c in coord)

    return str(coord)


# ========== Spec Auto-Correction ==========

# Fields that should be numbers
NUMERIC_FIELDS = {
    "radius",
    "height",
    "start_angle",
    "end_angle",
    "offset",
    "lineweight",
    "rotation",
    "scale",
    "scale_factor",
    "offset_x",
    "offset_y",
    "center_x",
    "center_y",
    "angle",
}

# Fields that should be colors
COLOR_FIELDS = {"color"}

# Fields that should be booleans
BOOL_FIELDS = {"closed", "save_changes"}

# Fields that are coordinates
COORDINATE_FIELDS = {
    "start",
    "end",
    "center",
    "corner1",
    "corner2",
    "position",
    "insertion_point",
    "base_point",
}


def autocorrect_spec(spec: Dict[str, Any], context: str = "") -> Dict[str, Any]:
    """
    Apply auto-corrections to a specification dictionary.

    Args:
        spec: Input specification
        context: Context hint ("entity", "entity_op", "layer_op", etc.)

    Returns:
        Corrected specification
    """
    if not isinstance(spec, dict):
        return spec

    corrected = {}

    for key, value in spec.items():
        # Normalize key to lowercase
        key_lower = key.lower()

        # Apply type-specific corrections
        if key_lower in NUMERIC_FIELDS:
            corrected[key_lower] = coerce_number(value, key_lower)

        elif key_lower in COLOR_FIELDS:
            corrected[key_lower] = fuzzy_match_color(value)

        elif key_lower in BOOL_FIELDS:
            corrected[key_lower] = coerce_bool(value)

        elif key_lower in COORDINATE_FIELDS:
            corrected[key_lower] = normalize_coordinate(value)

        else:
            # Pass through other fields with lowercase key
            corrected[key_lower] = value

    return corrected


# ========== Validation Helpers ==========


def validate_color(color: str) -> Optional[str]:
    """
    Validate a color value.

    Args:
        color: Color to validate

    Returns:
        Error message if invalid, None if valid
    """
    if not isinstance(color, str):
        return None  # Let adapter handle numeric colors

    color_lower = color.lower()

    # Check if it's a valid color or can be fuzzy-matched
    corrected = fuzzy_match_color(color_lower)

    if corrected != color_lower and corrected not in VALID_COLORS:
        return f"Unknown color '{color}'. Valid colors: {', '.join(VALID_COLORS)}"

    return None


def validate_required_fields(
    spec: Dict[str, Any], required: List[str], context: str = ""
) -> Optional[str]:
    """
    Validate that required fields are present.

    Args:
        spec: Specification to validate
        required: List of required field names
        context: Context for error message

    Returns:
        Error message if validation fails, None if valid
    """
    missing = [f for f in required if f not in spec or spec[f] is None]

    if missing:
        ctx_str = f" for {context}" if context else ""
        return f"Missing required fields{ctx_str}: {', '.join(missing)}"

    return None
