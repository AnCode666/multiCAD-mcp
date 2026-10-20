"""
Unit tests for Advanced Architectural Hatch Patterns (PR #17).

Tests ANSI31, AR-CONC, GRAVEL, EARTH, SOLID, pattern scaling, angles,
and boundary handle associative hatching.
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.drawing import (
    register_drawing_tools,
    ARCHITECTURAL_HATCH_PATTERNS,
    HATCH_PATTERN_ALIASES,
)
from mcp_tools.shorthand import parse_drawing_input


class MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, name=None):
        def decorator(fn):
            tool_name = name or fn.__name__
            self.tools[tool_name] = fn
            return fn
        return decorator


class TestHatchEzdxf:
    """Test hatch pattern rendering in EzdxfAdapter."""

    def test_draw_hatch_solid(self):
        adapter = EzdxfAdapter()
        pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
        handle = adapter.draw_hatch(pts, pattern="SOLID", color="red")
        assert handle is not None
        hatch = adapter.doc.entitydb.get(handle)
        assert hatch.dxftype() == "HATCH"
        assert hatch.dxf.solid_fill == 1

    def test_draw_hatch_ansi31_scaled(self):
        adapter = EzdxfAdapter()
        pts = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
        handle = adapter.draw_hatch(pts, pattern="ANSI31", scale=2.5, angle=45.0, color="gray")
        assert handle is not None
        hatch = adapter.doc.entitydb.get(handle)
        assert hatch.dxftype() == "HATCH"
        assert hatch.dxf.pattern_name == "ANSI31"
        assert hatch.dxf.pattern_scale == 2.5
        assert hatch.dxf.pattern_angle == 45.0

    def test_draw_hatch_ar_conc(self):
        adapter = EzdxfAdapter()
        pts = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]
        handle = adapter.draw_hatch(pts, pattern="AR-CONC", scale=1.0)
        hatch = adapter.doc.entitydb.get(handle)
        assert hatch.dxf.pattern_name == "AR-CONC"


class TestDrawingToolHatch:
    """Test draw_entities dispatching for hatch patterns."""

    @pytest.fixture(autouse=True)
    def setup_tool(self):
        self.adapter = EzdxfAdapter()
        self.mcp = MockMCP()
        register_drawing_tools(self.mcp)
        self._patcher1 = patch("adapters.adapter_manager.get_adapter", return_value=self.adapter)
        self._patcher2 = patch("mcp_tools.tools.drawing.get_current_adapter", return_value=self.adapter)
        self._patcher1.start()
        self._patcher2.start()
        self.draw_entities = self.mcp.tools["draw_entities"]
        yield
        self._patcher1.stop()
        self._patcher2.stop()

    def test_draw_entities_hatch_shorthand(self):
        res_str = self.draw_entities(
            "hatch|0,0;10,0;10,10;0,10|ANSI31|1.5|45|red|A-PATT"
        )
        res = json.loads(res_str)
        assert res["created"] == 1
        h = res["results"][0]["handle"]
        hatch = self.adapter.doc.entitydb.get(h)
        assert hatch.dxf.pattern_name == "ANSI31"
        assert hatch.dxf.pattern_scale == 1.5
        assert hatch.dxf.pattern_angle == 45.0

    def test_draw_entities_hatch_spanish_alias(self):
        res_str = self.draw_entities(
            "sombreado|0,0;5,0;5,5;0,5|hormigon|2.0|0|gray|A-ESTR"
        )
        res = json.loads(res_str)
        assert res["created"] == 1
        h = res["results"][0]["handle"]
        hatch = self.adapter.doc.entitydb.get(h)
        assert hatch.dxf.pattern_name == "AR-CONC"

    def test_draw_entities_hatch_boundary_handle(self):
        # Draw a rectangle first
        rect_handle = self.adapter.draw_rectangle((0, 0), (8, 6))
        # Now hatch specifying boundary_handle in JSON spec
        spec = [{
            "type": "hatch",
            "boundary_handle": rect_handle,
            "pattern": "GRAVEL",
            "scale": 1.0,
            "color": "yellow",
            "layer": "A-SUELOS",
        }]
        res_str = self.draw_entities(json.dumps(spec))
        res = json.loads(res_str)
        assert res["created"] == 1
        h = res["results"][0]["handle"]
        hatch = self.adapter.doc.entitydb.get(h)
        assert hatch.dxf.pattern_name == "GRAVEL"

    def test_hatch_shorthand_parsing(self):
        parsed = parse_drawing_input("hatch|0,0;10,0;10,10;0,10|AR-SAND|0.5|30|yellow|A-AISL")
        assert len(parsed) == 1
        item = parsed[0]
        assert item["type"] == "hatch"
        assert item["pattern"] == "AR-SAND"
        assert item["scale"] == 0.5
        assert item["angle"] == 30.0
        assert item["color"] == "yellow"
        assert item["layer"] == "A-AISL"
