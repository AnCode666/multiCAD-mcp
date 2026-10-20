"""
Unit tests for layout and paperspace management (PR #16).

Tests layout sheet creation, viewports (MVIEW), architectural scaling,
standard ISO paper sizes, and standardized AECO title blocks.
"""

import json
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from core import CADOperationError
from mcp_tools import set_current_adapter
from mcp_tools.tools.layouts import register_layout_tools
from mcp_tools.shorthand import parse_layout_op_shorthand


class DummyMCP:
    """Mock FastMCP server for tool registration."""
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator


class TestLayoutManagementEzdxf:
    """Test layout operations directly on EzdxfAdapter."""

    def test_list_layouts_initial(self):
        adapter = EzdxfAdapter()
        layouts = adapter.list_layouts()
        names = [l["name"] for l in layouts]
        assert "Model" in names
        assert any(l["is_modelspace"] for l in layouts)

    def test_create_layout_a3_landscape(self):
        adapter = EzdxfAdapter()
        res = adapter.create_layout("Plano_Arquitectura", paper_size="A3", orientation="landscape")
        assert res["success"] is True
        assert res["name"] == "Plano_Arquitectura"
        assert res["width_mm"] == 420.0
        assert res["height_mm"] == 297.0
        assert "Plano_Arquitectura" in adapter.doc.layouts

    def test_create_layout_a4_portrait(self):
        adapter = EzdxfAdapter()
        res = adapter.create_layout("Ficha_Tecnica", paper_size="A4", orientation="portrait")
        assert res["success"] is True
        assert res["width_mm"] == 210.0
        assert res["height_mm"] == 297.0

    def test_create_layout_duplicate_raises(self):
        adapter = EzdxfAdapter()
        adapter.create_layout("Plano_01", paper_size="A3")
        with pytest.raises(CADOperationError):
            adapter.create_layout("Plano_01", paper_size="A3")

    def test_activate_and_delete_layout(self):
        adapter = EzdxfAdapter()
        adapter.create_layout("Plano_Temp", paper_size="A3")
        assert adapter.activate_layout("Plano_Temp") is True
        assert adapter.delete_layout("Plano_Temp") is True
        assert "Plano_Temp" not in adapter.doc.layouts

        # Attempt to delete modelspace must fail
        with pytest.raises(CADOperationError):
            adapter.delete_layout("Model")

    def test_add_viewport_with_scale(self):
        adapter = EzdxfAdapter()
        adapter.create_layout("Plano_Detalle", paper_size="A3")
        vh_handle = adapter.add_viewport(
            layout_name="Plano_Detalle",
            center=(200.0, 150.0),
            width=300.0,
            height=200.0,
            view_center=(10.0, 10.0),
            scale="1:50",
            unit="m",
        )
        assert vh_handle is not None
        vp = adapter.doc.entitydb.get(vh_handle)
        assert vp is not None
        # At scale 1:50, 1mm paper = 0.05m model. Height 200mm = 10m view_height
        assert pytest.approx(vp.dxf.view_height, 0.01) == 10.0

    def test_add_titleblock(self):
        adapter = EzdxfAdapter()
        adapter.create_layout("Plano_ConTech", paper_size="A3")
        tb = adapter.add_titleblock(
            layout_name="Plano_ConTech",
            title="REHABILITACIÓN ENERGÉTICA",
            author="Jose Manuel Caamaño",
            date="2026-10-20",
            scale="1:50",
            sheet_number="PE-01",
        )
        assert tb["success"] is True
        assert tb["title"] == "REHABILITACIÓN ENERGÉTICA"
        assert tb["author"] == "Jose Manuel Caamaño"
        assert tb["scale"] == "1:50"


class TestManageLayoutsTool:
    """Test manage_layouts tool endpoint."""

    @pytest.fixture(autouse=True)
    def setup_tool(self):
        from unittest.mock import patch
        self.adapter = EzdxfAdapter()
        class MockMCP:
            def __init__(self):
                self.tools = {}
            def tool(self, name=None):
                def decorator(fn):
                    tool_name = name or fn.__name__
                    self.tools[tool_name] = fn
                    return fn
                return decorator

        self.mcp = MockMCP()
        register_layout_tools(self.mcp)
        self._patcher1 = patch("adapters.adapter_manager.get_adapter", return_value=self.adapter)
        self._patcher2 = patch("mcp_tools.tools.layouts.get_current_adapter", return_value=self.adapter)
        self._patcher1.start()
        self._patcher2.start()
        self.manage_layouts = self.mcp.tools["manage_layouts"]
        yield
        self._patcher1.stop()
        self._patcher2.stop()

    def test_tool_list_layouts(self):
        res = json.loads(self.manage_layouts(action="list"))
        assert res["success"] is True
        assert res["count"] >= 1

    def test_tool_create_layout_complete(self):
        res = json.loads(self.manage_layouts(
            action="create",
            name="Plano_General",
            paper_size="A2",
            orientation="landscape",
            scale="1:100",
            title="PLANTA GENERAL DE CONJUNTO",
            author="JMCG",
            sheet_number="01/05",
        ))
        assert res["success"] is True
        assert res["layout"]["name"] == "Plano_General"
        assert res["viewport_handle"] is not None
        assert res["titleblock"] is not None

    def test_tool_activate_and_delete(self):
        self.manage_layouts(action="create", name="Plano_Borrador")
        act_res = json.loads(self.manage_layouts(action="activate", name="Plano_Borrador"))
        assert act_res["success"] is True

        del_res = json.loads(self.manage_layouts(action="delete", name="Plano_Borrador"))
        assert del_res["success"] is True

    def test_layout_shorthand_parsing(self):
        parsed = parse_layout_op_shorthand("create|Plano_01|A3|landscape|1:50|PLANTA BAJA")
        assert parsed["action"] == "create"
        assert parsed["name"] == "Plano_01"
        assert parsed["paper_size"] == "A3"
        assert parsed["scale"] == "1:50"
        assert parsed["title"] == "PLANTA BAJA"

        parsed_list = parse_layout_op_shorthand("list")
        assert parsed_list["action"] == "list"
