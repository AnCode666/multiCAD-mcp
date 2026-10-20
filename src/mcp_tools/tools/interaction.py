"""
Interactive Human-in-the-Loop tool.

Enables bidirectional collaboration between LLM and human user:
- prompt_point: Ask user to pick a coordinate with AutoCAD crosshair
- prompt_entity: Ask user to click an entity on screen to select it
- prompt_distance: Ask user to measure or specify a distance
- prompt_string: Ask user for text input via CAD command line
"""

import json
import logging
from typing import Dict, Any, Union, List, Optional

from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate

logger = logging.getLogger(__name__)


def _prompt_point(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Ask user to pick a point in the CAD viewport."""
    prompt = spec.get("prompt", "Click on the drawing to pick a point:")
    base_point = None
    if "base_point" in spec and spec["base_point"]:
        try:
            base_point = parse_coordinate(spec["base_point"])
        except Exception:
            pass

    default_point = None
    if "default_point" in spec and spec["default_point"]:
        try:
            default_point = parse_coordinate(spec["default_point"])
        except Exception:
            pass

    if hasattr(adapter, "prompt_point"):
        # Pass default_point if supported
        try:
            return adapter.prompt_point(prompt=prompt, base_point=base_point, default_point=default_point)
        except TypeError:
            return adapter.prompt_point(prompt=prompt, base_point=base_point)
    return {"success": False, "error": "Adapter does not support interactive point prompt"}


def _prompt_entity(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Ask user to click an entity on screen."""
    prompt = spec.get("prompt", "Select an entity on screen:")
    default_handle = spec.get("default_handle")

    if hasattr(adapter, "prompt_entity"):
        try:
            return adapter.prompt_entity(prompt=prompt, default_handle=default_handle)
        except TypeError:
            return adapter.prompt_entity(prompt=prompt)
    return {"success": False, "error": "Adapter does not support interactive entity selection"}


def _prompt_distance(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Ask user to measure or specify a distance."""
    prompt = spec.get("prompt", "Specify distance:")
    base_point = None
    if "base_point" in spec and spec["base_point"]:
        try:
            base_point = parse_coordinate(spec["base_point"])
        except Exception:
            pass
    default_dist = float(spec.get("default_distance", 1.0))

    if hasattr(adapter, "prompt_distance"):
        try:
            return adapter.prompt_distance(prompt=prompt, base_point=base_point, default_distance=default_dist)
        except TypeError:
            return adapter.prompt_distance(prompt=prompt, base_point=base_point)
    return {"success": False, "error": "Adapter does not support interactive distance measurement"}


def _prompt_string(adapter, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Ask user for text input in CAD."""
    prompt = spec.get("prompt", "Enter text:")
    has_spaces = bool(spec.get("has_spaces", True))
    default_string = spec.get("default_string", "")

    if hasattr(adapter, "prompt_string"):
        try:
            return adapter.prompt_string(prompt=prompt, has_spaces=has_spaces, default_string=default_string)
        except TypeError:
            return adapter.prompt_string(prompt=prompt, has_spaces=has_spaces)
    return {"success": False, "error": "Adapter does not support interactive string input"}


INTERACTION_DISPATCH = {
    "point": _prompt_point,
    "pick_point": _prompt_point,
    "entity": _prompt_entity,
    "pick_entity": _prompt_entity,
    "distance": _prompt_distance,
    "pick_distance": _prompt_distance,
    "string": _prompt_string,
    "prompt_string": _prompt_string,
}


def register_interaction_tools(mcp):
    """Register interactive Human-in-the-Loop tools with FastMCP."""

    @cad_tool(mcp, "prompt_user")
    def prompt_user(
        input: Union[str, List[Any], Dict[str, Any]],
    ) -> str:
        """
        Request interactive input from human user inside CAD application.

        Actions:
        - point|message|[base_x,base_y]: Prompts user to click a point in CAD viewport
        - entity|message: Prompts user to click an entity on screen (returns handle, type, layer)
        - distance|message|[base_point]: Prompts user to measure or specify distance
        - string|message: Prompts user to enter text in CAD command line

        Example:
            "point|Click where you want to place the door hinge"
            "entity|Click the boundary wall to inspect"
        """
        adapter = get_current_adapter()

        # Parse input
        if isinstance(input, dict):
            spec = input
        elif isinstance(input, list) and len(input) > 0 and isinstance(input[0], dict):
            spec = input[0]
        else:
            line = str(input).strip()
            parts = [p.strip() for p in line.split("|")]
            action_raw = parts[0].lower() if parts else "point"
            prompt_text = parts[1] if len(parts) > 1 else ""
            base_pt = parts[2] if len(parts) > 2 else None
            spec = {"action": action_raw, "prompt": prompt_text, "base_point": base_pt}

        action = spec.get("action", "point").lower()
        handler = INTERACTION_DISPATCH.get(action)
        if not handler:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Unknown interaction action '{action}'. Supported: "
                    + ", ".join(INTERACTION_DISPATCH.keys()),
                },
                indent=2,
            )

        result = handler(adapter, spec)
        return json.dumps(result, indent=2)
