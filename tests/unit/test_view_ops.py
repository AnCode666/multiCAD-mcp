"""
Unit tests for View & Camera Operations (PR #6: manage_view).
"""

import json
from unittest.mock import patch
import pytest

from mcp_tools.shorthand import parse_session_input, parse_session_op_shorthand
from mcp_tools.tools.session import (
    _zoom_extents,
    _zoom_window,
    _zoom_center,
    _set_view_preset,
    _set_visual_style,
    _undo,
    _redo,
)
from adapters.ezdxf_adapter import EzdxfAdapter


class TestSessionShorthandParsing:
    """Test shorthand parsing for camera, view, and session operations."""

    def test_zoom_extents_aliases(self):
        res1 = parse_session_op_shorthand("ze")
        res2 = parse_session_op_shorthand("zoom_extents")
        assert res1["action"] == "zoom_extents"
        assert res2["action"] == "zoom_extents"

    def test_zoom_window_shorthand(self):
        res = parse_session_op_shorthand("zw|0,0|150,200")
        assert res["action"] == "zoom_window"
        assert res["corner1"] == "0,0"
        assert res["corner2"] == "150,200"

    def test_zoom_center_shorthand(self):
        res = parse_session_op_shorthand("zc|25,30|2.5")
        assert res["action"] == "zoom_center"
        assert res["center"] == "25,30"
        assert res["magnification"] == 2.5

    def test_view_preset_shorthand(self):
        res_preset = parse_session_op_shorthand("preset|iso_se")
        res_view = parse_session_op_shorthand("view|top")
        assert res_preset["action"] == "set_view_preset"
        assert res_preset["preset"] == "iso_se"
        assert res_view["action"] == "set_view_preset"
        assert res_view["preset"] == "top"

    def test_visual_style_shorthand(self):
        res = parse_session_op_shorthand("style|realistic")
        assert res["action"] == "set_visual_style"
        assert res["style"] == "realistic"

    def test_undo_redo_shorthand(self):
        res_undo = parse_session_op_shorthand("undo|3")
        res_redo = parse_session_op_shorthand("redo|2")
        assert res_undo["action"] == "undo"
        assert res_undo["count"] == 3
        assert res_redo["action"] == "redo"
        assert res_redo["count"] == 2

    def test_multiline_shorthand_input(self):
        text = "ze\nzw|0,0|100,50\npreset|iso_sw"
        ops = parse_session_input(text)
        assert len(ops) == 3
        assert ops[0]["action"] == "zoom_extents"
        assert ops[1]["action"] == "zoom_window"
        assert ops[2]["action"] == "set_view_preset"

    def test_dict_and_json_passthrough(self):
        raw_dict = {"action": "zoom_extents"}
        ops1 = parse_session_input(raw_dict)
        ops2 = parse_session_input('[{"action": "set_visual_style", "style": "conceptual"}]')
        assert ops1 == [raw_dict]
        assert ops2[0]["action"] == "set_visual_style"


class TestCameraOperationsExecution:
    """Test camera operations executed against CAD adapter."""

    def test_zoom_extents_execution(self):
        adapter = EzdxfAdapter()
        with patch("mcp_tools.tools.session.get_adapter", return_value=adapter):
            res = _zoom_extents({})
            assert res["success"] is True

    def test_zoom_window_execution(self):
        adapter = EzdxfAdapter()
        with patch("mcp_tools.tools.session.get_adapter", return_value=adapter):
            res = _zoom_window({"corner1": "10,20", "corner2": "50,80"})
            assert res["success"] is True
            assert adapter._view_bbox == (10.0, 20.0, 50.0, 80.0)

    def test_zoom_center_execution(self):
        adapter = EzdxfAdapter()
        with patch("mcp_tools.tools.session.get_adapter", return_value=adapter):
            res = _zoom_center({"center": "100,200", "magnification": 1.5})
            assert res["success"] is True
            assert adapter._view_center == (100.0, 200.0)
            assert adapter._view_mag == 1.5

    def test_set_view_preset_execution(self):
        adapter = EzdxfAdapter()
        with patch("mcp_tools.tools.session.get_adapter", return_value=adapter):
            res = _set_view_preset({"preset": "iso_se"})
            assert res["success"] is True
            assert adapter._view_preset == "iso_se"

    def test_set_visual_style_execution(self):
        adapter = EzdxfAdapter()
        with patch("mcp_tools.tools.session.get_adapter", return_value=adapter):
            res = _set_visual_style({"style": "conceptual"})
            assert res["success"] is True
            assert adapter._visual_style == "conceptual"

    def test_undo_redo_execution(self):
        adapter = EzdxfAdapter()
        with patch("mcp_tools.tools.session.get_adapter", return_value=adapter):
            res_u = _undo({"count": 2})
            res_r = _redo({"count": 1})
            assert res_u["success"] is True
            assert res_r["success"] is True
