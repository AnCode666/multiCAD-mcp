"""
Unit tests for Standalone Vector PDF Plotting (PR #8: export_data format='pdf').
"""

import json
import os
from unittest.mock import patch
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter
from mcp_tools.tools.export import _export_pdf


class TestVectorPdfPlotting:
    """Test generating standalone vector PDF 1.4 drawings."""

    def test_plot_to_pdf_generates_valid_pdf_file(self, tmp_path):
        adapter = EzdxfAdapter()
        adapter.create_layer("A-WALL", color="red")
        adapter.draw_line((0, 0), (10, 0), layer="A-WALL")
        adapter.draw_line((10, 0), (10, 8), layer="A-WALL")
        adapter.draw_circle((5, 4), 2.0, layer="A-WALL")
        adapter.draw_text((5, 4), "SALA REUNIONES", height=0.5)

        pdf_path = os.path.join(tmp_path, "plano_ensayo.pdf")
        res = adapter.plot_to_pdf(pdf_path, paper_size="A3")

        assert res["success"] is True
        assert res["paper_size"] == "A3"
        assert res["entities_plotted"] >= 4
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0

        # Validate PDF binary header and structure
        with open(pdf_path, "rb") as f:
            header = f.read(8)
            assert header.startswith(b"%PDF-1.4")
            f.seek(0)
            content = f.read()
            assert b"/Type /Catalog" in content
            assert b"/Type /Page" in content
            assert b"%%EOF" in content

    def test_export_pdf_via_tool(self, tmp_path):
        adapter = EzdxfAdapter()
        adapter.draw_rectangle((0, 0), (20, 15))

        with patch("mcp_tools.tools.export.get_current_adapter", return_value=adapter):
            with patch("core.config.get_config") as mock_cfg:
                mock_cfg.return_value.output.directory = str(tmp_path)
                res_raw = _export_pdf(adapter, "plano_distribucion.pdf", paper_size="A4")
                res = json.loads(res_raw)

                assert res["success"] is True
                assert res["paper_size"] == "A4"
                assert os.path.exists(res["path"])
                assert res["path"].endswith(".pdf")
