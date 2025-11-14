"""
NLP Processor for multiCAD-MCP.

Parses natural language commands and extracts parameters for CAD operations.
Supports shape drawing, layer management, and entity manipulation.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    """Result of parsing a natural language command."""

    operation: str  # draw_line, draw_circle, etc.
    parameters: Dict[str, Any]  # Extracted parameters
    confidence: float  # Confidence level (0.0-1.0)
    raw_text: str  # Original text


class NLPProcessor:
    """Process natural language commands for CAD operations."""

    # Command type keywords
    COMMAND_KEYWORDS = {
        "draw": ["draw", "create", "make", "add"],
        "erase": ["erase", "delete", "remove", "clear"],
        "move": ["move", "translate", "shift"],
        "rotate": ["rotate", "turn", "spin"],
        "scale": ["scale", "resize", "enlarge", "shrink"],
        "dimension": ["dimension", "annotate", "measure"],
        "layer": ["layer"],
        "rename": ["rename", "change name"],
        "turn_on": ["turn on", "show", "unhide", "enable"],
        "turn_off": ["turn off", "hide", "disable"],
    }

    # Shape type keywords
    SHAPE_KEYWORDS = {
        "line": ["line", "segment"],
        "circle": ["circle", "round"],
        "arc": ["arc", "curve"],
        "rectangle": ["rectangle", "rect", "square"],
        "polyline": ["polyline", "polygon", "path"],
        "ellipse": ["ellipse", "oval"],
        "text": ["text", "label", "note"],
        "hatch": ["hatch", "fill", "pattern"],
    }

    # Color mapping
    COLOR_NAMES = {
        "black": "black",
        "red": "red",
        "green": "green",
        "blue": "blue",
        "yellow": "yellow",
        "magenta": "magenta",
        "cyan": "cyan",
        "white": "white",
        "gray": "gray",
        "grey": "gray",
        "orange": "orange",
    }

    # Pattern for extracting numbers: supports decimals, scientific notation
    # Examples: 1, -1.23, 1e3, 1.23E-4
    NUMBER_PATTERN = r"[+-]?(?:\d+\.?\d*|\d*\.\d+)(?:[eE][+-]?\d+)?"

    # Pattern for extracting coordinates: (x, y) or (x, y, z)
    # Supports various formats: (10,20), 10,20, x=10 y=20, etc.
    # Note: comma/semicolon required between x,y but optional before z
    COORD_PATTERN = rf"\(?[\s]*(?:x\s*=\s*)?({NUMBER_PATTERN})\s*[,;]\s*(?:y\s*=\s*)?({NUMBER_PATTERN})(?:\s*[,;]\s*(?:z\s*=\s*)?({NUMBER_PATTERN}))?\s*\)?"

    def __init__(self, strict_mode: bool = False):
        """
        Initialize NLP processor.

        Args:
            strict_mode: If True, require all parameters explicitly.
                        If False, use reasonable defaults.
        """
        self.strict_mode = strict_mode
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        self.coord_regex = re.compile(self.COORD_PATTERN)
        self.number_regex = re.compile(self.NUMBER_PATTERN)

    def _keyword_in_text(self, text: str, keyword: str) -> bool:
        """Check if keyword exists in text with word boundaries to avoid false positives."""
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None

    def parse_command(self, text: str) -> ParsedCommand:
        """
        Parse natural language command.

        Args:
            text: User's natural language command

        Returns:
            ParsedCommand with operation, parameters, and confidence

        Raises:
            ValueError: If command cannot be parsed and strict_mode=True
        """
        text_lower = text.lower()

        # Identify command type
        command_type = self._identify_command_type(text_lower)

        # If no command type but we can identify a shape, assume it's a draw command
        if not command_type:
            shape_type = self._identify_shape_type(text_lower)
            if shape_type:
                command_type = "draw"
            else:
                raise ValueError(f"Cannot identify command type in: '{text}'")

        # Handle layer commands
        if command_type in ["layer", "rename", "turn_on", "turn_off"]:
            return self._parse_layer_command(command_type, text_lower, text)

        # Handle draw commands
        if command_type == "draw":
            # Identify shape type
            shape_type = self._identify_shape_type(text_lower)
            if not shape_type:
                raise ValueError(f"Cannot identify shape type in: '{text}'")

            operation = f"draw_{shape_type}"

            # Extract parameters based on shape type
            parameters = self._extract_parameters(shape_type, text_lower, text)

            # Calculate confidence
            confidence = self._calculate_confidence(text_lower, shape_type, parameters)

            return ParsedCommand(
                operation=operation,
                parameters=parameters,
                confidence=confidence,
                raw_text=text,
            )

        # Other commands not yet supported
        raise ValueError(f"Command type '{command_type}' not yet supported")

    def _identify_command_type(self, text_lower: str) -> Optional[str]:
        """Identify the type of command (draw, erase, move, etc.)."""
        # Check for specific layer commands first (highest priority)
        # Pattern: "create/make/add [a] [color] layer <name>"
        if re.search(r"\b(create|make|add)\s+.*?\blayer\b", text_lower):
            return "layer"

        if "layer" in text_lower or "layers" in text_lower:
            # Check if it's a layer management command
            if "rename" in text_lower or "change name" in text_lower:
                return "rename"
            elif re.search(r"\bturn\s+on\s+layer\b", text_lower):
                return "turn_on"
            elif re.search(r"\bturn\s+off\s+layer\b", text_lower):
                return "turn_off"
            elif re.search(r"\b(show|unhide)\s+layer\b", text_lower):
                return "turn_on"
            elif re.search(r"\b(hide|disable)\s+layer\b", text_lower):
                return "turn_off"
            elif re.search(r"\b(delete|remove|erase)\s+layer\b", text_lower):
                return "layer"
            elif re.search(r"\b(list|show)\s+(all\s+)?layers?\b", text_lower):
                return "layer"
            # If it's "on layer" or similar, it's a modifier, not a layer command
            # Continue to check for draw commands

        # Check for draw/create/make commands (only if not a layer command)
        for command_type in ["draw"]:
            keywords = self.COMMAND_KEYWORDS.get(command_type, [])
            if any(keyword in text_lower for keyword in keywords):
                return command_type

        # Then check other command types
        for command_type, keywords in self.COMMAND_KEYWORDS.items():
            if command_type not in ["layer", "rename", "turn_on", "turn_off", "draw"]:
                if any(keyword in text_lower for keyword in keywords):
                    return command_type
        return None

    def _identify_shape_type(self, text_lower: str) -> Optional[str]:
        """Identify the shape type to draw using word boundaries."""
        # Sort by keyword length (longest first) to match "polyline" before "line"
        sorted_shapes = sorted(
            self.SHAPE_KEYWORDS.items(),
            key=lambda x: max(len(kw) for kw in x[1]),
            reverse=True,
        )
        for shape_type, keywords in sorted_shapes:
            if any(self._keyword_in_text(text_lower, keyword) for keyword in keywords):
                return shape_type
        return None

    def _extract_parameters(
        self, shape_type: str, text_lower: str, original_text: str
    ) -> Dict[str, Any]:
        """Extract parameters based on shape type."""
        params: Dict[str, Any] = {}

        # Common parameters for all shapes
        params["color"] = self._extract_color(text_lower)
        params["layer"] = self._extract_layer(
            original_text
        )  # Use original to preserve case
        params["lineweight"] = self._extract_lineweight(text_lower)

        # Shape-specific parameters
        if shape_type == "line":
            params["start"], params["end"] = self._extract_line_points(text_lower)
        elif shape_type == "circle":
            params["center"] = self._extract_single_point(text_lower)
            params["radius"] = self._extract_radius(text_lower)
        elif shape_type == "arc":
            params["center"] = self._extract_single_point(text_lower)
            params["radius"] = self._extract_radius(text_lower)
            params["start_angle"] = self._extract_angle(text_lower, "start")
            params["end_angle"] = self._extract_angle(text_lower, "end")
        elif shape_type == "rectangle":
            params["corner1"], params["corner2"] = self._extract_rectangle_corners(
                text_lower
            )
        elif shape_type == "ellipse":
            params["center"] = self._extract_single_point(text_lower)
            params["major_axis"] = self._extract_vector(text_lower)
            params["minor_ratio"] = self._extract_minor_ratio(text_lower)
        elif shape_type == "polyline":
            params["points"] = self._extract_multiple_points(text_lower)
            params["closed"] = "closed" in text_lower
        elif shape_type == "text":
            params["position"] = self._extract_single_point(text_lower)
            params["text"] = self._extract_text_content(
                original_text
            )  # Use original to preserve case
            params["height"] = self._extract_text_height(text_lower)
            params["rotation"] = self._extract_angle(text_lower, "rotation")
        elif shape_type == "hatch":
            params["boundary_points"] = self._extract_multiple_points(text_lower)
            params["pattern"] = self._extract_hatch_pattern(text_lower)

        return params

    def _extract_color(self, text: str) -> str:
        """Extract color specification from text."""
        for color_name in self.COLOR_NAMES.keys():
            if color_name in text:
                return self.COLOR_NAMES[color_name]
        return "white"  # Default

    def _extract_layer(self, text: str) -> str:
        """Extract layer name from text (case-sensitive for layer name)."""
        # Try to match quoted layer name first
        match = re.search(r'(?:layer|on)\s+["\']([^"\']+)["\']', text, re.IGNORECASE)
        if match:
            return match.group(1)
        # Then try unquoted layer name
        match = re.search(r"(?:layer|on)\s+([a-zA-Z0-9_]+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return "0"  # Default layer

    def _extract_lineweight(self, text: str) -> int:
        """Extract line weight specification."""
        match = re.search(r"(?:weight|thickness|lineweight)\s+(\d+)", text)
        if match:
            return int(match.group(1))
        if not self.strict_mode:
            logger.debug("No lineweight found, using default 0")
        return 0  # Default

    def _extract_single_point(self, text: str) -> Tuple[float, float]:
        """Extract a single point (center, position, etc.)."""
        match = self.coord_regex.search(text)
        if match:
            x = float(match.group(1))
            y = float(match.group(2))
            return (x, y)

        if not self.strict_mode:
            logger.warning("No coordinates found, using default (0, 0)")
            return (0.0, 0.0)

        raise ValueError("Cannot extract coordinate")

    def _extract_line_points(
        self, text: str
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Extract start and end points for a line."""
        matches = list(self.coord_regex.finditer(text))

        if len(matches) >= 2:
            start = (float(matches[0].group(1)), float(matches[0].group(2)))
            end = (float(matches[1].group(1)), float(matches[1].group(2)))
            return start, end

        if not self.strict_mode:
            logger.warning(
                "No two points found for line, using default (0,0) to (100,100)"
            )
            return (0.0, 0.0), (100.0, 100.0)

        raise ValueError("Cannot extract two points for line")

    def _extract_rectangle_corners(
        self, text: str
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Extract two opposite corners for rectangle."""
        return self._extract_line_points(text)

    def _extract_multiple_points(self, text: str) -> List[Tuple[float, float]]:
        """Extract multiple points for polyline."""
        matches = self.coord_regex.finditer(text)
        points = [(float(m.group(1)), float(m.group(2))) for m in matches]

        if points:
            return points

        if not self.strict_mode:
            logger.warning("No points found for polyline, using default square")
            return [(0, 0), (100, 0), (100, 100), (0, 100)]

        raise ValueError("Cannot extract points for polyline")

    def _extract_radius(self, text: str) -> float:
        """Extract radius specification."""
        match = re.search(r"(?:radius|r)\s*(?:=|of|:)?\s*(\d+\.?\d*)", text)
        if match:
            return float(match.group(1))

        if not self.strict_mode:
            logger.warning("No radius found, using default 50.0")
            return 50.0

        raise ValueError("Cannot extract radius")

    def _extract_vector(self, text: str) -> Tuple[float, float]:
        """Extract a vector for major axis."""
        match = self.coord_regex.search(text)
        if match:
            x = float(match.group(1))
            y = float(match.group(2))
            return (x, y)

        if not self.strict_mode:
            return (50.0, 0.0)

        raise ValueError("Cannot extract vector")

    def _extract_minor_ratio(self, text: str) -> float:
        """Extract minor axis ratio for ellipse."""
        match = re.search(r"(?:ratio|minor)\s*(?:=|of|:)?\s*(\d+\.?\d*)", text)
        if match:
            ratio = float(match.group(1))
            return min(max(ratio, 0.0), 1.0)  # Clamp to 0-1

        if not self.strict_mode:
            return 0.5  # Default 50%

        raise ValueError("Cannot extract minor ratio")

    def _extract_text_content(self, text: str) -> str:
        """Extract text content to add."""
        match = re.search(r'(?:text|label|content)\s*["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)

        if not self.strict_mode:
            return "Text"  # Default

        raise ValueError("Cannot extract text content")

    def _extract_text_height(self, text: str) -> float:
        """Extract text height."""
        match = re.search(r"(?:height|size)\s*(?:=|of|:)?\s*(\d+\.?\d*)", text)
        if match:
            return float(match.group(1))

        if not self.strict_mode:
            return 2.5  # Default

        raise ValueError("Cannot extract text height")

    def _extract_angle(self, text: str, angle_type: str = "start") -> float:
        """Extract angle in degrees."""
        # Try to match specific angle type first (start angle, end angle, rotation)
        pattern = (
            rf"(?:{angle_type}[_\s]?angle|{angle_type})\s*(?:=|of|:)?\s*(\d+\.?\d*)"
        )
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))

        # If no specific match and angle_type is "start", try generic angle patterns
        if angle_type == "start":
            # Try patterns like "angle 180", "start angle 45", "end angle 90"
            generic_pattern = (
                r"(?:start\s+angle|end\s+angle|angle)\s*(?:=|of|:)?\s*(\d+\.?\d*)"
            )
            match = re.search(generic_pattern, text)
            if match:
                return float(match.group(1))

        if not self.strict_mode:
            return 0.0  # Default start angle

        raise ValueError(f"Cannot extract {angle_type} angle")

    def _extract_hatch_pattern(self, text: str) -> str:
        """Extract hatch pattern name."""
        patterns = ["solid", "angle", "cross", "hatch", "brick"]
        for pattern in patterns:
            if pattern in text:
                return pattern.upper()

        if not self.strict_mode:
            return "SOLID"

        raise ValueError("Cannot extract hatch pattern")

    def _calculate_confidence(
        self, text: str, shape_type: str, parameters: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for the parsing using weighted features.
        Returns a score between 0.0 and 1.0.
        """
        features = {
            "has_draw_keyword": self._keyword_in_text(text.lower(), "draw")
            or self._keyword_in_text(text.lower(), "create"),
            "shape_explicit": self._keyword_in_text(text.lower(), shape_type),
            "has_coordinates": any(
                k in parameters
                for k in ["start", "end", "center", "position", "points", "corner1"]
            ),
            "has_measurements": any(
                k in parameters for k in ["radius", "height", "width"]
            ),
            "has_color": parameters.get("color") and parameters.get("color") != "white",
            "has_layer": parameters.get("layer") and parameters.get("layer") != "0",
        }

        # Weighted scoring
        weights = {
            "has_draw_keyword": 0.15,
            "shape_explicit": 0.30,
            "has_coordinates": 0.35,
            "has_measurements": 0.10,
            "has_color": 0.05,
            "has_layer": 0.05,
        }

        score = 0.0
        for feature, present in features.items():
            if present:
                score += weights.get(feature, 0.0)

        return min(1.0, max(0.0, score))

    def extract_parameters_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract parameters from text without full parsing.
        Used for filling in missing parameters.
        """
        return {
            "color": self._extract_color(text),
            "layer": self._extract_layer(text),
            "lineweight": self._extract_lineweight(text),
        }

    def _parse_layer_command(
        self, command_type: str, text_lower: str, original_text: str
    ) -> ParsedCommand:
        """
        Parse layer management commands.

        Supports:
        - "create layer MyLayer" or "create a layer named MyLayer"
        - "rename layer OldName to NewName"
        - "delete layer MyLayer"
        - "turn on layer MyLayer" or "show layer MyLayer"
        - "turn off layer MyLayer" or "hide layer MyLayer"
        """
        parameters: Dict[str, Any] = {}

        # Extract layer name(s)
        if command_type == "rename":
            # Format: "rename layer OldName to NewName"
            old_name, new_name = self._extract_rename_layers(text_lower)
            if old_name and new_name:
                parameters["old_name"] = old_name
                parameters["new_name"] = new_name
                operation = "rename_layer"
                confidence = 0.9 if old_name and new_name else 0.5
            else:
                raise ValueError("Cannot extract old and new layer names")

        elif command_type == "turn_on":
            # Format: "turn on layer MyLayer" or "show layer MyLayer"
            layer_name = self._extract_single_layer_name(text_lower, original_text)
            if layer_name:
                parameters["name"] = layer_name
                operation = "turn_layer_on"
                confidence = 0.9
            else:
                raise ValueError("Cannot extract layer name")

        elif command_type == "turn_off":
            # Format: "turn off layer MyLayer" or "hide layer MyLayer"
            layer_name = self._extract_single_layer_name(text_lower, original_text)
            if layer_name:
                parameters["name"] = layer_name
                operation = "turn_layer_off"
                confidence = 0.9
            else:
                raise ValueError("Cannot extract layer name")

        elif command_type == "layer":
            # Format: "create layer MyLayer" or "delete layer MyLayer"
            if any(keyword in text_lower for keyword in ["create", "make", "add"]):
                layer_name = self._extract_single_layer_name(text_lower, original_text)
                if layer_name:
                    parameters["name"] = layer_name
                    parameters["color"] = self._extract_color(text_lower)
                    parameters["lineweight"] = self._extract_lineweight(text_lower)
                    operation = "create_layer"
                    confidence = 0.9
                else:
                    raise ValueError("Cannot extract layer name")

            elif any(
                keyword in text_lower for keyword in ["delete", "remove", "erase"]
            ):
                layer_name = self._extract_single_layer_name(text_lower, original_text)
                if layer_name:
                    parameters["name"] = layer_name
                    operation = "delete_layer"
                    confidence = 0.9
                else:
                    raise ValueError("Cannot extract layer name")

            elif any(keyword in text_lower for keyword in ["list", "show", "all"]):
                operation = "list_layers"
                confidence = 0.95

            else:
                raise ValueError("Cannot determine layer operation")
        else:
            raise ValueError(f"Unknown layer command type: {command_type}")

        return ParsedCommand(
            operation=operation,
            parameters=parameters,
            confidence=confidence,
            raw_text=original_text,
        )

    def _extract_single_layer_name(
        self, text_lower: str, original_text: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract a single layer name from text, preserving case from original text.
        Looks for: "layer <name>" or "named <name>" or quoted names
        """
        # Use original text if provided, otherwise fall back to text_lower
        text_to_search = original_text if original_text else text_lower

        # Try to find quoted names first: "MyLayer" or 'MyLayer' (preserves case)
        quoted_match = re.search(r'["\']([^"\']+)["\']', text_to_search)
        if quoted_match:
            return quoted_match.group(1)

        # Try to find pattern: "layer <name>" (case-insensitive search, case-sensitive capture)
        layer_match = re.search(
            r"layer\s+([a-zA-Z0-9_\-]+)", text_to_search, re.IGNORECASE
        )
        if layer_match:
            return layer_match.group(1)

        # Try to find pattern: "named <name>"
        named_match = re.search(
            r"named\s+([a-zA-Z0-9_\-]+)", text_to_search, re.IGNORECASE
        )
        if named_match:
            return named_match.group(1)

        # Try last word if it looks like a layer name
        words = text_to_search.split()
        if words:
            last_word = words[-1].strip(".,;:!?")
            if re.match(r"^[a-zA-Z0-9_\-]+$", last_word) and last_word.lower() not in [
                "layer",
                "on",
                "off",
            ]:
                return last_word

        return None

    def _extract_rename_layers(
        self, text_lower: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract old and new layer names from rename command.
        Formats:
        - "rename layer OldName to NewName"
        - "rename 'OldName' to 'NewName'"
        """
        # Try quoted format first
        quoted_match = re.findall(r'["\']([^"\']+)["\']', text_lower)
        if len(quoted_match) >= 2:
            return quoted_match[0], quoted_match[1]

        # Try pattern: "layer <old> to <new>"
        to_match = re.search(
            r"layer\s+([a-zA-Z0-9_\-]+)\s+to\s+([a-zA-Z0-9_\-]+)", text_lower
        )
        if to_match:
            return to_match.group(1), to_match.group(2)

        # Try pattern: "<old> to <new>" (last resort)
        to_match = re.search(r"([a-zA-Z0-9_\-]+)\s+to\s+([a-zA-Z0-9_\-]+)", text_lower)
        if to_match:
            return to_match.group(1), to_match.group(2)

        return None, None
