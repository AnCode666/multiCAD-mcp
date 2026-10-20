"""
Unit tests for External References & Raster Images (PR #10: manage_xrefs).
"""

import json
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.xrefs import (
    _attach_xref,
    _attach_raster,
    _list_xrefs,
    _reload_xref,
    _detach_xref,
)


class TestXrefManagement:
    """Test managing DWG XREFs and Raster images."""

    def test_attach_dwg_xref(self):
        adapter = EzdxfAdapter()
        res = _attach_xref(
            adapter,
            {
                "path": "c:/projects/topografia.dwg",
                "insertion_point": "100,50",
                "scale": 1.0,
            },
        )
        assert res["success"] is True
        assert res["name"] == "topografia"
        assert res["insertion_point"] == (100.0, 50.0)

        # Verify listed
        xrefs = adapter.list_xrefs()
        assert len(xrefs) == 1
        assert xrefs[0]["name"] == "topografia"
        assert xrefs[0]["type"] == "dwg"

    def test_attach_raster_orthophoto(self):
        adapter = EzdxfAdapter()
        res = _attach_raster(
            adapter,
            {
                "path": "c:/catastro/ortofoto_pnoa.jpg",
                "insertion_point": "500,200",
                "scale": 2.5,
            },
        )
        assert res["success"] is True
        assert res["name"] == "ortofoto_pnoa"

        xrefs = adapter.list_xrefs()
        assert len(xrefs) == 1
        assert xrefs[0]["type"] == "raster"

    def test_reload_and_detach_xref(self):
        adapter = EzdxfAdapter()
        _attach_xref(adapter, {"path": "c:/cad/estructura.dwg"})
        assert len(adapter.list_xrefs()) == 1

        # Reload
        res_reload = _reload_xref(adapter, {"name": "estructura"})
        assert res_reload["success"] is True

        # Detach
        res_detach = _detach_xref(adapter, {"name": "estructura"})
        assert res_detach["success"] is True
        assert len(adapter.list_xrefs()) == 0
