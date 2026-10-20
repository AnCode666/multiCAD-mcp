"""
Unit tests for batch text search and replace (PR #18).

Tests finding and replacing text across TEXT, MTEXT, and block attributes (ATTRIB),
case sensitivity, regex support, and layer filtering.
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.entities import register_entity_tools
from mcp_tools.shorthand import parse_entity_op_shorthand


class MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, name=None):
        def decorator(fn):
            tool_name = name or fn.__name__
            self.tools[tool_name] = fn
            return fn
        return decorator


class TestTextSearchAndReplaceEzdxf:
    """Test find_text_entities and replace_text_entities directly on EzdxfAdapter."""

    def test_find_text_basic(self):
        adapter = EzdxfAdapter()
        adapter.draw_text((0, 0), "Dormitorio 1", height=2.5, layer="A-ROTL")
        adapter.draw_text((10, 0), "Dormitorio 2", height=2.5, layer="A-ROTL")
        adapter.draw_text((20, 0), "Cocina", height=2.5, layer="A-ROTL")

        matches = adapter.find_text_entities("dormitorio", case_sensitive=False)
        assert len(matches) == 2
        texts = [m["text"] for m in matches]
        assert "Dormitorio 1" in texts
        assert "Dormitorio 2" in texts

    def test_find_text_layer_filter(self):
        adapter = EzdxfAdapter()
        adapter.create_layer("A-ROTL", color="white")
        adapter.create_layer("A-OBS", color="yellow")
        adapter.draw_text((0, 0), "Nota técnica", layer="A-ROTL")
        adapter.draw_text((10, 0), "Nota temporal", layer="A-OBS")

        matches_rotl = adapter.find_text_entities("Nota", layer="A-ROTL")
        assert len(matches_rotl) == 1
        assert matches_rotl[0]["text"] == "Nota técnica"

    def test_find_and_replace_block_attributes(self):
        adapter = EzdxfAdapter()
        blk = adapter.doc.blocks.new("ROOM_TAG")
        blk.add_attdef("ROOM_NAME", (0, 0))
        ins = adapter.msp.add_blockref("ROOM_TAG", (0, 0))
        ins.add_attrib("ROOM_NAME", "Dormitorio Secundario")

        res = adapter.replace_text_entities("Secundario", "Invitados")
        assert res["success"] is True
        assert res["count"] == 1
        assert res["replacements"][0]["new_text"] == "Dormitorio Invitados"

    def test_replace_text_regex(self):
        adapter = EzdxfAdapter()
        adapter.draw_text((0, 0), "PUERTA P-01")
        adapter.draw_text((5, 0), "PUERTA P-02")
        adapter.draw_text((10, 0), "VENTANA V-01")

        res = adapter.replace_text_entities(
            search_pattern=r"P-(\d+)",
            replacement=r"TIPO-\1",
            use_regex=True,
        )
        assert res["success"] is True
        assert res["count"] == 2
        replaced_texts = [r["new_text"] for r in res["replacements"]]
        assert "PUERTA TIPO-01" in replaced_texts
        assert "PUERTA TIPO-02" in replaced_texts


class TestManageEntitiesTextTool:
    """Test manage_entities text tools endpoint."""

    @pytest.fixture(autouse=True)
    def setup_tool(self):
        self.adapter = EzdxfAdapter()
        self.mcp = MockMCP()
        register_entity_tools(self.mcp)
        self._patcher1 = patch("adapters.adapter_manager.get_adapter", return_value=self.adapter)
        self._patcher2 = patch("mcp_tools.tools.entities.get_current_adapter", return_value=self.adapter)
        self._patcher1.start()
        self._patcher2.start()
        self.manage_entities = self.mcp.tools["manage_entities"]
        yield
        self._patcher1.stop()
        self._patcher2.stop()

    def test_manage_entities_find_text_shorthand(self):
        self.adapter.draw_text((0, 0), "Salon Principal", layer="A-ROTL")
        res_str = self.manage_entities("find_text|Salon|A-ROTL")
        res = json.loads(res_str)
        assert res["succeeded"] == 1
        item = res["results"][0]
        assert item["count"] == 1
        assert "Salon Principal" in item["matches"][0]["text"]

    def test_manage_entities_replace_text_shorthand(self):
        self.adapter.draw_text((0, 0), "Salon Principal", layer="A-ROTL")
        res_str = self.manage_entities("replace_text|Salon|Salón Comedor|A-ROTL")
        res = json.loads(res_str)
        assert res["succeeded"] == 1
        item = res["results"][0]
        assert item["count"] == 1
        assert item["replacements"][0]["new_text"] == "Salón Comedor Principal"

    def test_shorthand_parsing(self):
        parsed = parse_entity_op_shorthand("replace_text|Old|New|A-TEXT|true")
        assert parsed["action"] == "replace_text"
        assert parsed["find"] == "Old"
        assert parsed["replace"] == "New"
        assert parsed["layer"] == "A-TEXT"
