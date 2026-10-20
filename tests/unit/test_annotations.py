"""
Unit tests for Smart Architectural Annotations & Dimensioning tools.
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.annotations import register_annotation_tools


class TestAnnotations:
    """Test manage_annotations tool."""

    @pytest.fixture
    def adapter_with_rooms(self):
        adapter = EzdxfAdapter()
        adapter.create_layer("A-ROOMS", color="blue")

        # Two rooms: Dormitorio (4x5 = 20 m²) and Baño (2x5 = 10 m²)
        h1 = adapter.draw_rectangle((0, 0), (4, 5), layer="A-ROOMS")
        h2 = adapter.draw_rectangle((4, 0), (6, 5), layer="A-ROOMS")

        adapter.set_entity_metadata(h1, {"nombre": "Dormitorio Principal"})
        adapter.set_entity_metadata(h2, {"nombre": "Baño En Suite"})

        return adapter

    def test_label_spaces(self, adapter_with_rooms):
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
        register_annotation_tools(mcp)

        with patch("adapters.adapter_manager.get_adapter", return_value=adapter_with_rooms), \
             patch("mcp_tools.tools.annotations.get_current_adapter", return_value=adapter_with_rooms):
            res_str = mcp.tools["manage_annotations"](action="label_spaces", prefix="Superficie: ")
            res = json.loads(res_str)

            assert res["success"] is True
            assert res["action"] == "label_spaces"
            assert res["count"] == 2

            labels = res["labels"]
            assert any("Dormitorio Principal" in l["text"] and "20.00 m²" in l["text"] for l in labels)
            assert any("Baño En Suite" in l["text"] and "10.00 m²" in l["text"] for l in labels)

    def test_auto_dimension_overall(self, adapter_with_rooms):
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
        register_annotation_tools(mcp)

        with patch("adapters.adapter_manager.get_adapter", return_value=adapter_with_rooms), \
             patch("mcp_tools.tools.annotations.get_current_adapter", return_value=adapter_with_rooms):
            res_str = mcp.tools["manage_annotations"](action="auto_dimension", style="overall", offset=1.2)
            res = json.loads(res_str)

            assert res["success"] is True
            assert res["action"] == "auto_dimension"
            assert res["style"] == "overall"
            assert res["count"] == 2

            dims = res["dimensions"]
            h_dim = next(d for d in dims if d["subtype"] == "horizontal_overall")
            v_dim = next(d for d in dims if d["subtype"] == "vertical_overall")
            assert h_dim["length"] == 6.0
            assert v_dim["length"] == 5.0

    def test_auto_dimension_segments(self, adapter_with_rooms):
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
        register_annotation_tools(mcp)

        with patch("adapters.adapter_manager.get_adapter", return_value=adapter_with_rooms), \
             patch("mcp_tools.tools.annotations.get_current_adapter", return_value=adapter_with_rooms):
            res_str = mcp.tools["manage_annotations"](action="auto_dimension", style="segments")
            res = json.loads(res_str)

            assert res["success"] is True
            assert res["count"] > 0
            assert all(d["subtype"] == "segment" for d in res["dimensions"])
