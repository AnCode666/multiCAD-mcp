"""
Unit tests for Human-in-the-Loop Interaction tools (PR #7: prompt_user).
"""

import json
from unittest.mock import patch, MagicMock
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.interaction import (
    _prompt_point,
    _prompt_entity,
    _prompt_distance,
    _prompt_string,
    register_interaction_tools,
)


class TestHumanInTheLoopInteractions:
    """Test interactive prompts for point, entity, distance, and text."""

    def test_prompt_point_headless_fallback(self):
        adapter = EzdxfAdapter()
        res = _prompt_point(adapter, {"prompt": "Pick origin", "default_point": "10,25"})
        assert res["success"] is True
        assert res["point"] == (10.0, 25.0, 0.0)
        assert res["interactive"] is False

    def test_prompt_point_com_success(self):
        mock_adapter = MagicMock()
        mock_adapter.prompt_point.return_value = {
            "success": True,
            "point": (100.5, 200.0, 0.0),
            "interactive": True,
        }
        res = _prompt_point(mock_adapter, {"prompt": "Click door position"})
        assert res["success"] is True
        assert res["point"] == (100.5, 200.0, 0.0)
        assert res["interactive"] is True

    def test_prompt_point_user_cancellation(self):
        mock_adapter = MagicMock()
        mock_adapter.prompt_point.return_value = {
            "success": False,
            "cancelled": True,
            "detail": "User cancelled point selection",
        }
        res = _prompt_point(mock_adapter, {"prompt": "Click somewhere"})
        assert res["success"] is False
        assert res["cancelled"] is True

    def test_prompt_entity_headless(self):
        adapter = EzdxfAdapter()
        h = adapter.draw_line((0, 0), (10, 10))
        res = _prompt_entity(adapter, {"prompt": "Pick line"})
        assert res["success"] is True
        assert res["handle"] == h
        assert res["type"] == "LINE"

    def test_prompt_entity_com(self):
        mock_adapter = MagicMock()
        mock_adapter.prompt_entity.return_value = {
            "success": True,
            "handle": "4A1",
            "type": "AcDbPolyline",
            "layer": "A-WALL",
            "interactive": True,
        }
        res = _prompt_entity(mock_adapter, {"prompt": "Select wall"})
        assert res["success"] is True
        assert res["handle"] == "4A1"
        assert res["type"] == "AcDbPolyline"

    def test_prompt_distance_execution(self):
        adapter = EzdxfAdapter()
        res = _prompt_distance(adapter, {"prompt": "Measure span", "default_distance": 4.5})
        assert res["success"] is True
        assert res["distance"] == 4.5

    def test_prompt_string_execution(self):
        adapter = EzdxfAdapter()
        res = _prompt_string(adapter, {"prompt": "Room name", "default_string": "SALON"})
        assert res["success"] is True
        assert res["string"] == "SALON"


class TestPromptUserToolRegistration:
    """Test MCP tool wrapper for prompt_user."""

    def test_tool_invocation_shorthand(self):
        adapter = EzdxfAdapter()
        mcp_mock = MagicMock()
        registered_func = None

        def mock_tool():
            def decorator(fn):
                nonlocal registered_func
                registered_func = fn
                return fn
            return decorator

        mcp_mock.tool = mock_tool

        with patch("mcp_tools.tools.interaction.get_current_adapter", return_value=adapter):
            with patch("mcp_tools.decorators.cad_tool", lambda mcp, name: (lambda fn: fn)):
                from mcp_tools.tools.interaction import register_interaction_tools
                register_interaction_tools(mcp_mock)

                # Call the handler with shorthand
                from mcp_tools.tools.interaction import _prompt_point
                res = _prompt_point(adapter, {"prompt": "Pick start", "default_point": "5,5"})
                assert res["point"] == (5.0, 5.0, 0.0)
