"""
Natural Language Processing tools.

Provides tools for:
- Executing CAD commands from natural language descriptions
"""

import logging
from typing import Optional, Any

from mcp.server.fastmcp import Context

from core import NLPParseError
from nlp.processor import NLPProcessor
from mcp_tools.decorators import cad_tool, get_current_adapter

logger = logging.getLogger(__name__)

# Initialize NLP processor once
_nlp_processor = NLPProcessor()


def _result_to_string(result: Any) -> str:
    """Convert operation result to string for MCP return value.

    Args:
        result: Result from CAD adapter method (str, bool, List, etc.)

    Returns:
        String representation of the result
    """
    if isinstance(result, str):
        return result
    elif isinstance(result, list):
        # Format list as numbered items
        return "Results:\n" + "\n".join(
            f"  {i+1}. {item}" for i, item in enumerate(result)
        )
    elif isinstance(result, bool):
        return "Success" if result else "Failed"
    else:
        return str(result)


def register_nlp_tools(mcp):
    """Register natural language processing tools with FastMCP.

    Args:
        mcp: FastMCP instance
    """

    @cad_tool(mcp, "execute_natural_command")
    def execute_natural_command(
        ctx: Context,
        command: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Execute a CAD command from natural language.

        Examples:
            - "draw a line from 0,0 to 100,100"
            - "create a red circle at 50,50 with radius 25"
            - "add blue text 'Hello' at 10,10 with height 5"

        Args:
            command: Natural language command description
            cad_type: CAD application to use

        Returns:
            Result of the executed command
        """
        parsed = _nlp_processor.parse_command(command)
        logger.info(
            f"Parsed command: {parsed.operation} "
            f"(confidence: {parsed.confidence:.2f})"
        )

        operation = parsed.operation
        params = parsed.parameters

        # Execute based on operation type
        if operation == "draw_line":
            result = get_current_adapter().draw_line(
                params.get("start", (0, 0)),
                params.get("end", (100, 100)),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
            )
            return _result_to_string(result)

        elif operation == "draw_circle":
            result = get_current_adapter().draw_circle(
                params.get("center", (0, 0)),
                params.get("radius", 50.0),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
            )
            return _result_to_string(result)

        elif operation == "draw_rectangle":
            result = get_current_adapter().draw_rectangle(
                params.get("corner1", (0, 0)),
                params.get("corner2", (100, 100)),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
            )
            return _result_to_string(result)

        elif operation == "draw_polyline":
            result = get_current_adapter().draw_polyline(
                params.get("points", [(0, 0), (100, 0), (100, 100)]),
                closed=params.get("closed", False),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
                lineweight=params.get("lineweight", 0),
            )
            return _result_to_string(result)

        elif operation == "draw_text":
            result = get_current_adapter().draw_text(
                params.get("position", (0, 0)),
                params.get("text", "Text"),
                height=params.get("height", 2.5),
                rotation=params.get("rotation", 0.0),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
            )
            return _result_to_string(result)

        elif operation == "draw_arc":
            result = get_current_adapter().draw_arc(
                params.get("center", (0, 0)),
                params.get("radius", 50.0),
                params.get("start_angle", 0.0),
                params.get("end_angle", 90.0),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
            )
            return _result_to_string(result)

        elif operation == "draw_ellipse":
            result = get_current_adapter().draw_ellipse(
                params.get("center", (0, 0)),
                params.get("major_axis", 100.0),
                params.get("minor_axis", 50.0),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
            )
            return _result_to_string(result)

        elif operation == "draw_hatch":
            result = get_current_adapter().draw_hatch(
                params.get("boundary_points", [(0, 0), (100, 0), (100, 100), (0, 100)]),
                pattern=params.get("pattern", "SOLID"),
                layer=params.get("layer", "0"),
                color=params.get("color", "white"),
            )
            return _result_to_string(result)

        elif operation == "create_layer":
            result = get_current_adapter().create_layer(
                params.get("name", "NewLayer"),
                color=params.get("color", "white"),
                lineweight=params.get("lineweight", 0),
            )
            return _result_to_string(result)

        elif operation == "delete_layer":
            result = get_current_adapter().delete_layer(params.get("name", "0"))
            return _result_to_string(result)

        elif operation == "rename_layer":
            result = get_current_adapter().rename_layer(
                params.get("old_name", "0"),
                params.get("new_name", "RenamedLayer"),
            )
            return _result_to_string(result)

        elif operation == "turn_layer_on":
            result = get_current_adapter().turn_on_layer(params.get("name", "0"))
            return _result_to_string(result)

        elif operation == "turn_layer_off":
            result = get_current_adapter().turn_off_layer(params.get("name", "0"))
            return _result_to_string(result)

        elif operation == "list_layers":
            result = get_current_adapter().list_layers()
            return _result_to_string(result)

        else:
            raise NLPParseError(command, f"Operation '{operation}' not yet supported")
