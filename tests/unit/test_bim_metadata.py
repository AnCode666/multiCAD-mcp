"""
Unit tests for BIM Semantic Metadata & XDATA (PR #9: set_metadata / get_metadata).
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.entities import _set_metadata, _get_metadata


class TestBimSemanticMetadata:
    """Test attaching and retrieving BIM / XDATA properties on CAD entities."""

    def test_attach_and_retrieve_metadata_adapter(self):
        adapter = EzdxfAdapter()
        h = adapter.draw_line((0, 0), (10, 0))

        # Set key-value
        ok = adapter.set_entity_metadata(h, {"resistencia_fuego": "EI-120", "u_value": 0.28})
        assert ok is True

        # Retrieve
        data = adapter.get_entity_metadata(h)
        assert data["resistencia_fuego"] == "EI-120"
        assert data["u_value"] == 0.28

    def test_metadata_via_entities_tool_handlers(self):
        adapter = EzdxfAdapter()
        h = adapter.draw_rectangle((0, 0), (6, 4))

        with patch("mcp_tools.tools.entities.get_current_adapter", return_value=adapter):
            # Set via tool
            res_set = _set_metadata({
                "handle": h,
                "metadata": {"tipo": "Muro Fachada SATE", "espesor": 0.30, "codigo_coste": "01.02.04"}
            })
            assert res_set["success"] is True

            # Get via tool
            res_get = _get_metadata({"handle": h})
            assert res_get["success"] is True
            assert res_get["metadata"]["tipo"] == "Muro Fachada SATE"
            assert res_get["metadata"]["codigo_coste"] == "01.02.04"

    def test_empty_metadata_for_unassigned_entity(self):
        adapter = EzdxfAdapter()
        h = adapter.draw_circle((0, 0), 5.0)

        with patch("mcp_tools.tools.entities.get_current_adapter", return_value=adapter):
            res = _get_metadata({"handle": h})
            assert res["success"] is True
            assert res["metadata"] == {}
