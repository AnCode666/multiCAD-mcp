"""
Unit tests for PR #13: Offset, Fillet, Chamfer, Explode, and MatchProp operations.
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.shorthand import parse_entity_op_shorthand
from mcp_tools.tools.entities import register_entity_tools


class TestOffsetFilletShorthand:
    """Test shorthand parsing for PR #13 operations."""

    def test_offset_shorthand(self):
        res = parse_entity_op_shorthand("offset|1A4|0.30")
        assert res["action"] == "offset"
        assert res["handle"] == "1A4"
        assert res["distance"] == 0.30

    def test_fillet_shorthand(self):
        res = parse_entity_op_shorthand("fillet|1A,1B|0.5")
        assert res["action"] == "fillet"
        assert res["handles"] == "1A,1B"
        assert res["radius"] == 0.5

    def test_chamfer_shorthand(self):
        res = parse_entity_op_shorthand("chamfer|1A,1B|0.2|0.4")
        assert res["action"] == "chamfer"
        assert res["handles"] == "1A,1B"
        assert res["dist1"] == 0.2
        assert res["dist2"] == 0.4

    def test_explode_shorthand(self):
        res = parse_entity_op_shorthand("explode|1A,1B")
        assert res["action"] == "explode"
        assert res["handles"] == "1A,1B"

    def test_matchprop_shorthand(self):
        res = parse_entity_op_shorthand("matchprop|SRC1|TGT1,TGT2")
        assert res["action"] == "matchprop"
        assert res["source_handle"] == "SRC1"
        assert res["target_handles"] == "TGT1,TGT2"


class TestOffsetFilletExecution:
    """Test CAD geometry execution for offset, fillet, chamfer, explode, matchprop."""

    @pytest.fixture
    def adapter(self):
        return EzdxfAdapter()

    def test_offset_line(self, adapter):
        h = adapter.draw_line((0, 0), (10, 0), layer="A-WALL")
        # Offset by 2.0 (normal points +Y)
        new_handles = adapter.offset_entity(h, distance=2.0)
        assert len(new_handles) == 1
        new_h = new_handles[0]

        # Verify new entity coordinates
        new_e = next(e for e in adapter.msp if str(e.dxf.handle) == new_h)
        assert round(new_e.dxf.start[1], 1) == 2.0
        assert round(new_e.dxf.end[1], 1) == 2.0

    def test_offset_circle(self, adapter):
        h = adapter.draw_circle((5, 5), radius=3.0)
        new_handles = adapter.offset_entity(h, distance=1.5)
        assert len(new_handles) == 1
        new_e = next(e for e in adapter.msp if str(e.dxf.handle) == new_handles[0])
        assert round(new_e.dxf.radius, 1) == 4.5

    def test_fillet_sharp_corner(self, adapter):
        # Line 1: (0, 0) -> (9.5, 0)
        # Line 2: (10, 0.5) -> (10, 10)
        # They don't touch, intersection is at (10, 0)
        h1 = adapter.draw_line((0, 0), (9.5, 0))
        h2 = adapter.draw_line((10, 0.5), (10, 10))

        res = adapter.fillet_entities(h1, h2, radius=0.0)
        assert res == h1

        e1 = next(e for e in adapter.msp if str(e.dxf.handle) == h1)
        e2 = next(e for e in adapter.msp if str(e.dxf.handle) == h2)
        assert round(e1.dxf.end[0], 1) == 10.0
        assert round(e1.dxf.end[1], 1) == 0.0
        assert round(e2.dxf.start[0], 1) == 10.0
        assert round(e2.dxf.start[1], 1) == 0.0

    def test_chamfer_lines(self, adapter):
        h1 = adapter.draw_line((0, 0), (10, 0))
        h2 = adapter.draw_line((10, 0), (10, 10))
        connector = adapter.chamfer_entities(h1, h2, dist1=1.0, dist2=1.0)
        assert connector is not None

    def test_explode_polyline(self, adapter):
        h_poly = adapter.draw_rectangle((0, 0), (4, 4), layer="A-ROOM")
        new_lines = adapter.explode_entity(h_poly)
        assert len(new_lines) == 4
        # Verify original polyline removed and 4 lines created
        assert not any(str(e.dxf.handle) == h_poly for e in adapter.msp)
        assert all(any(str(e.dxf.handle) == lh for e in adapter.msp) for lh in new_lines)

    def test_match_properties(self, adapter):
        adapter.create_layer("A-TEMPLATE", color="red")
        adapter.create_layer("A-TARGET", color="blue")
        h_src = adapter.draw_line((0, 0), (1, 1), layer="A-TEMPLATE", color="red")
        h_tgt1 = adapter.draw_line((2, 2), (3, 3), layer="A-TARGET", color="blue")
        h_tgt2 = adapter.draw_line((4, 4), (5, 5), layer="A-TARGET", color="blue")

        success = adapter.match_properties(h_src, [h_tgt1, h_tgt2])
        assert success is True

        e_tgt1 = next(e for e in adapter.msp if str(e.dxf.handle) == h_tgt1)
        e_tgt2 = next(e for e in adapter.msp if str(e.dxf.handle) == h_tgt2)
        assert e_tgt1.dxf.layer == "A-TEMPLATE"
        assert e_tgt2.dxf.layer == "A-TEMPLATE"

    def test_manage_entities_tool_integration(self, adapter):
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

        h_line = adapter.draw_line((0, 0), (10, 0), layer="A-WALL")

        with patch("adapters.adapter_manager.get_adapter", return_value=adapter), \
             patch("mcp_tools.decorators.get_current_adapter", return_value=adapter):
            res_str = mcp.tools["manage_entities"](operations=f"offset|{h_line}|1.5")
            res = json.loads(res_str)

            assert res["succeeded"] == 1
            op_res = res["results"][0]
            assert op_res["action"] == "offset"
            assert op_res["count"] == 1
