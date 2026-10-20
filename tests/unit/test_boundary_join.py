"""
Unit tests for PR #14: Boundary detection, Join, Trim, and Extend operations.
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.shorthand import parse_entity_op_shorthand
from mcp_tools.tools.entities import register_entity_tools


class TestBoundaryJoinShorthand:
    """Test shorthand parsing for boundary, join, trim, and extend."""

    def test_boundary_shorthand(self):
        res = parse_entity_op_shorthand("boundary|4.5,3.2|A-ROOMS")
        assert res["action"] == "boundary"
        assert res["point"] == "4.5,3.2"
        assert res["layer"] == "A-ROOMS"

    def test_join_shorthand(self):
        res = parse_entity_op_shorthand("join|1A,1B,1C|0.02")
        assert res["action"] == "join"
        assert res["handles"] == "1A,1B,1C"

    def test_trim_shorthand(self):
        res = parse_entity_op_shorthand("trim|1A|2B")
        assert res["action"] == "trim"
        assert res["handle"] == "1A"
        assert res["boundary"] == "2B"

    def test_extend_shorthand(self):
        res = parse_entity_op_shorthand("extend|1A|2B")
        assert res["action"] == "extend"
        assert res["handle"] == "1A"
        assert res["boundary"] == "2B"


class TestBoundaryJoinExecution:
    """Test CAD geometry execution for boundary, join, trim, and extend."""

    @pytest.fixture
    def adapter(self):
        return EzdxfAdapter()

    def test_create_boundary_around_point(self, adapter):
        # 4 walls forming a 10m x 8m room
        adapter.draw_line((0, 0), (10, 0), layer="A-WALL")
        adapter.draw_line((10, 0), (10, 8), layer="A-WALL")
        adapter.draw_line((10, 8), (0, 8), layer="A-WALL")
        adapter.draw_line((0, 8), (0, 0), layer="A-WALL")

        # Internal point at (5, 4)
        bound_h = adapter.create_boundary((5, 4), layer="A-HABITACION")
        assert bound_h is not None

        # Verify area of created boundary
        area_info = adapter.get_entity_area(bound_h)
        assert round(area_info["area"], 1) == 80.0
        assert round(area_info["perimeter"], 1) == 36.0

    def test_join_loose_lines_into_polyline(self, adapter):
        h1 = adapter.draw_line((0, 0), (5, 0), layer="A-WALL")
        h2 = adapter.draw_line((5, 0), (5, 5), layer="A-WALL")
        h3 = adapter.draw_line((5, 5), (0, 5), layer="A-WALL")

        poly_h = adapter.join_entities([h1, h2, h3], tolerance=0.01)
        assert poly_h is not None

        # Original loose lines removed
        assert not any(str(e.dxf.handle) in (h1, h2, h3) for e in adapter.msp)

        # New polyline exists with 4 vertices
        new_poly = next(e for e in adapter.msp if str(e.dxf.handle) == poly_h)
        assert new_poly.dxftype() in ("LWPOLYLINE", "POLYLINE")
        assert len(new_poly.get_points()) == 4

    def test_trim_line_against_boundary(self, adapter):
        # Horizontal line (0,0) -> (10,0)
        h_line = adapter.draw_line((0, 0), (10, 0))
        # Cutting boundary vertical line at X=4: (4, -5) -> (4, 5)
        h_bound = adapter.draw_line((4, -5), (4, 5))

        success = adapter.trim_extend_entity(h_line, h_bound, mode="trim")
        assert success is True

        trimmed = next(e for e in adapter.msp if str(e.dxf.handle) == h_line)
        # Line trimmed to X=4
        assert round(trimmed.dxf.end[0], 1) == 4.0

    def test_extend_line_against_boundary(self, adapter):
        # Short horizontal line (0,0) -> (2,0)
        h_line = adapter.draw_line((0, 0), (2, 0))
        # Boundary vertical line at X=6: (6, -5) -> (6, 5)
        h_bound = adapter.draw_line((6, -5), (6, 5))

        success = adapter.trim_extend_entity(h_line, h_bound, mode="extend")
        assert success is True

        extended = next(e for e in adapter.msp if str(e.dxf.handle) == h_line)
        # Line extended to X=6
        assert round(extended.dxf.end[0], 1) == 6.0

    def test_manage_entities_boundary_and_join_tool(self, adapter):
        class MockMCP:
            def __init__(self):
                self.tools = {}
            def tool(self, name=None):
                def decorator(fn):
                    tool_name = name or fn.__name__
                    self.tools[tool_name] = fn
                    return fn
                return decorator

        mcp = MockMCP()
        register_entity_tools(mcp)

        adapter.draw_line((0, 0), (5, 0))
        adapter.draw_line((5, 0), (5, 4))
        adapter.draw_line((5, 4), (0, 4))
        adapter.draw_line((0, 4), (0, 0))

        with patch("adapters.adapter_manager.get_adapter", return_value=adapter), \
             patch("mcp_tools.decorators.get_current_adapter", return_value=adapter):

            res_str = mcp.tools["manage_entities"](operations="boundary|2,2|A-BOUND")
            res = json.loads(res_str)

            assert res["succeeded"] == 1
            assert res["results"][0]["action"] == "boundary"
            assert res["results"][0]["success"] is True
