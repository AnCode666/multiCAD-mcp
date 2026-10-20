"""
Unit tests for Spatial Intelligence & Interactive Drawing Viewer.
"""

import json
import os
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.inspection import (
    _point_in_polygon,
    _get_drawing_entities_data,
    _generate_ascii_minimap,
    register_inspection_tools,
)


class TestSpatialMath:
    """Test point-in-polygon raycasting algorithm."""

    def test_point_inside_rectangle(self):
        rect = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]
        assert _point_in_polygon(5.0, 4.0, rect) is True

    def test_point_outside_rectangle(self):
        rect = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]
        assert _point_in_polygon(12.0, 4.0, rect) is False
        assert _point_in_polygon(-1.0, 2.0, rect) is False

    def test_point_inside_irregular_polygon(self):
        # L-shaped polygon
        poly = [
            (0.0, 0.0), (10.0, 0.0), (10.0, 5.0),
            (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)
        ]
        assert _point_in_polygon(2.0, 2.0, poly) is True
        assert _point_in_polygon(2.0, 8.0, poly) is True
        assert _point_in_polygon(8.0, 8.0, poly) is False  # In cutout of L


class TestDrawingInspection:
    """Test inspect_drawing tool modes and reporting."""

    @pytest.fixture
    def populated_adapter(self):
        adapter = EzdxfAdapter()
        adapter.create_layer("A-WALL", color="white")
        adapter.create_layer("A-ROOMS", color="blue")

        # Outer walls
        adapter.draw_line((0, 0), (10, 0), layer="A-WALL")
        adapter.draw_line((10, 0), (10, 6), layer="A-WALL")
        adapter.draw_line((10, 6), (0, 6), layer="A-WALL")
        adapter.draw_line((0, 6), (0, 0), layer="A-WALL")

        # Two rooms
        h1 = adapter.draw_rectangle((0, 0), (5, 6), layer="A-ROOMS")
        h2 = adapter.draw_rectangle((5, 0), (10, 6), layer="A-ROOMS")

        adapter.set_entity_metadata(h1, {"nombre": "Salon", "tipo": "estancia"})
        adapter.set_entity_metadata(h2, {"nombre": "Cocina", "tipo": "servicio"})

        return adapter

    def test_data_extraction_and_bbox(self, populated_adapter):
        data = _get_drawing_entities_data(populated_adapter)
        assert data["bbox"]["width"] == 10.0
        assert data["bbox"]["length"] == 6.0
        assert data["bbox"]["area_bounding_m2"] == 60.0
        assert len(data["spaces"]) == 2
        assert len(data["layers"]) >= 2

    def test_ascii_minimap(self, populated_adapter):
        data = _get_drawing_entities_data(populated_adapter)
        minimap = _generate_ascii_minimap(data["spaces"], data["bbox"])
        assert "ESQUEMA DE DISTRIBUCIÓN CAD" in minimap
        assert "Salon" in minimap
        assert "Cocina" in minimap

    def test_inspect_drawing_summary_mode(self, populated_adapter):
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

        with patch("adapters.adapter_manager.get_adapter", return_value=populated_adapter), \
             patch("mcp_tools.tools.inspection.get_current_adapter", return_value=populated_adapter):
            res_str = mcp.tools["inspect_drawing"](mode="summary")
            res = json.loads(res_str)

            assert res["success"] is True
            assert res["spaces_count"] == 2
            assert res["total_usable_area_m2"] == 60.0
            assert "ascii_minimap" in res

    def test_inspect_drawing_point_mode_inside_and_outside(self, populated_adapter):
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

        with patch("adapters.adapter_manager.get_adapter", return_value=populated_adapter), \
             patch("mcp_tools.tools.inspection.get_current_adapter", return_value=populated_adapter):
            # Point inside Salon (2.5, 3.0)
            res1 = json.loads(mcp.tools["inspect_drawing"](mode="point", point="2.5, 3.0"))
            assert res1["success"] is True
            assert res1["found"] is True
            assert "INSIDE" in res1["description"]

            # Point inside Cocina (7.5, 3.0)
            res2 = json.loads(mcp.tools["inspect_drawing"](mode="point", point="7.5, 3.0"))
            assert res2["success"] is True
            assert res2["found"] is True

            # Point outside building (15.0, 15.0)
            res3 = json.loads(mcp.tools["inspect_drawing"](mode="point", point="15.0, 15.0"))
            assert res3["success"] is True
            assert res3["found"] is False
            assert "outside" in res3["description"]

    def test_show_drawing_viewer_generates_valid_html(self, populated_adapter, tmp_path):
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

        class MockConfig:
            class Output:
                directory = str(tmp_path)
            output = Output()

        with patch("adapters.adapter_manager.get_adapter", return_value=populated_adapter), \
             patch("mcp_tools.tools.inspection.get_current_adapter", return_value=populated_adapter), \
             patch("mcp_tools.tools.inspection.get_config", return_value=MockConfig()):

            res_str = mcp.tools["show_drawing_viewer"](filename="test_plan.html", open_browser=False)
            res = json.loads(res_str)

            assert res["success"] is True
            assert res["opened_in_browser"] is False
            html_file = res["viewer_path"]
            assert os.path.exists(html_file)

            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()

            assert "<!DOCTYPE html>" in content
            assert "cadCanvas" in content
            assert "multiCAD AECO Viewer" in content
            assert "Salon" in content
