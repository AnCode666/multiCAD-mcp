"""
Unit tests for PR #15: Snapping and Geometric Intersection detection.
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.inspection import _line_segment_intersection, register_inspection_tools


class TestGeometricIntersections:
    """Test line segment intersection calculations."""

    def test_perpendicular_crossing_segments(self):
        p1, p2 = (0.0, 5.0), (10.0, 5.0)
        p3, p4 = (5.0, 0.0), (5.0, 10.0)
        ix = _line_segment_intersection(p1, p2, p3, p4)
        assert ix == (5.0, 5.0)

    def test_parallel_segments_no_intersection(self):
        p1, p2 = (0.0, 0.0), (10.0, 0.0)
        p3, p4 = (0.0, 2.0), (10.0, 2.0)
        ix = _line_segment_intersection(p1, p2, p3, p4)
        assert ix is None

    def test_non_touching_segments(self):
        # Lines would cross if infinite, but segments do not overlap
        p1, p2 = (0.0, 0.0), (2.0, 0.0)
        p3, p4 = (5.0, -2.0), (5.0, 2.0)
        ix = _line_segment_intersection(p1, p2, p3, p4)
        assert ix is None


class TestSnappingAndIntersectionsTool:
    """Test inspect_drawing with mode='intersections' and mode='snap'."""

    @pytest.fixture
    def adapter(self):
        ad = EzdxfAdapter()
        # Draw crossed lines
        h1 = ad.draw_line((0, 5), (10, 5), layer="A-WALL")
        h2 = ad.draw_line((5, 0), (5, 10), layer="A-WALL")
        # Draw circle
        ad.draw_circle((20, 20), radius=5.0, layer="A-COLS")
        return ad

    def test_inspect_drawing_intersections_mode(self, adapter):
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
        register_inspection_tools(mcp)

        with patch("adapters.adapter_manager.get_adapter", return_value=adapter), \
             patch("mcp_tools.tools.inspection.get_current_adapter", return_value=adapter):

            res_str = mcp.tools["inspect_drawing"](mode="intersections")
            res = json.loads(res_str)

            assert res["success"] is True
            assert res["count"] >= 1
            pts = [ix["point"] for ix in res["intersections"]]
            assert [5.0, 5.0] in pts

    def test_inspect_drawing_snap_endpoint(self, adapter):
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
        register_inspection_tools(mcp)

        with patch("adapters.adapter_manager.get_adapter", return_value=adapter), \
             patch("mcp_tools.tools.inspection.get_current_adapter", return_value=adapter):

            # Probe near origin (0.1, 5.05) - close to endpoint (0, 5)
            res1 = json.loads(mcp.tools["inspect_drawing"](mode="snap", point="0.1, 5.05", tolerance=1.0))
            assert res1["success"] is True
            assert res1["snapped"] is True
            assert res1["best_snap"]["snap_type"] == "endpoint"
            assert res1["best_snap"]["point"] == [0.0, 5.0]

            # Probe near midpoint (5.05, 5.05) - close to midpoint of (0,5)->(10,5) which is (5,5)
            res2 = json.loads(mcp.tools["inspect_drawing"](mode="snap", point="5.05, 5.05", snap_types="midpoint"))
            assert res2["success"] is True
            assert res2["snapped"] is True
            assert res2["best_snap"]["snap_type"] == "midpoint"
            assert res2["best_snap"]["point"] == [5.0, 5.0]

            # Probe near circle center (20.1, 19.9) - close to center (20, 20)
            res3 = json.loads(mcp.tools["inspect_drawing"](mode="snap", point="20.1, 19.9", snap_types="center"))
            assert res3["success"] is True
            assert res3["snapped"] is True
            assert res3["best_snap"]["snap_type"] == "center"
            assert res3["best_snap"]["point"] == [20.0, 20.0]
