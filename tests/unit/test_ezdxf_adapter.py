"""
Unit tests for EzdxfAdapter (Headless DXF engine).
"""

import math
import os
import tempfile
import pytest

from adapters.ezdxf_adapter import EzdxfAdapter


@pytest.fixture
def adapter():
    """Create a clean EzdxfAdapter instance for testing."""
    ad = EzdxfAdapter()
    ad.connect()
    return ad


class TestEzdxfAdapterConnection:
    """Test connection and lifecycle."""

    def test_connect_disconnect(self, adapter):
        assert adapter.is_connected() is True
        assert adapter.disconnect() is True
        assert adapter.is_connected() is False
        assert adapter.connect() is True
        assert adapter.is_connected() is True

    def test_cad_type(self, adapter):
        assert adapter.cad_type == "dxf"


class TestEzdxfAdapterLayers:
    """Test layer management in headless DXF."""

    def test_create_and_list_layer(self, adapter):
        assert adapter.create_layer("WALLS", color="red", lineweight=50) is True
        layers = adapter.list_layers()
        assert "WALLS" in layers

    def test_layer_visibility(self, adapter):
        adapter.create_layer("DOORS", color="green")
        assert adapter.is_layer_on("DOORS") is True
        assert adapter.turn_layer_off("DOORS") is True
        assert adapter.is_layer_on("DOORS") is False
        assert adapter.turn_layer_on("DOORS") is True
        assert adapter.is_layer_on("DOORS") is True

    def test_rename_and_delete_layer(self, adapter):
        adapter.create_layer("TEMP_LAYER", color="yellow")
        assert adapter.rename_layer("TEMP_LAYER", "RENAMED_LAYER") is True
        assert "RENAMED_LAYER" in adapter.list_layers()
        assert "TEMP_LAYER" not in adapter.list_layers()

        assert adapter.delete_layer("RENAMED_LAYER") is True
        assert "RENAMED_LAYER" not in adapter.list_layers()

    def test_protected_layers(self, adapter):
        assert adapter.delete_layer("0") is False
        assert adapter.rename_layer("0", "NEW_0") is False


class TestEzdxfAdapterDrawing:
    """Test drawing primitives in headless DXF."""

    def test_draw_line(self, adapter):
        h = adapter.draw_line((0, 0), (10, 10), layer="0", color="red")
        assert h is not None
        props = adapter.get_entity_properties(h)
        assert props["object_name"] == "LINE"

    def test_draw_circle(self, adapter):
        h = adapter.draw_circle((5, 5), radius=3.5, layer="0", color="cyan")
        assert h is not None
        props = adapter.get_entity_properties(h)
        assert props["object_name"] == "CIRCLE"

    def test_draw_arc(self, adapter):
        h = adapter.draw_arc((0, 0), radius=5.0, start_angle=0, end_angle=90)
        assert h is not None
        props = adapter.get_entity_properties(h)
        assert props["object_name"] == "ARC"

    def test_draw_rectangle_and_polyline(self, adapter):
        h_rect = adapter.draw_rectangle((0, 0), (10, 5), layer="0")
        assert h_rect is not None

        h_poly = adapter.draw_polyline([(0, 0), (5, 2), (10, 0)], closed=False)
        assert h_poly is not None

    def test_draw_text(self, adapter):
        h = adapter.draw_text((2, 3), "Living Room", height=3.0, rotation=0.0)
        assert h is not None
        props = adapter.get_entity_properties(h)
        assert props["object_name"] == "TEXT"

    def test_draw_table(self, adapter):
        h = adapter.draw_table(
            insertion_point=(0, 0),
            num_rows=3,
            num_cols=2,
            row_height=5.0,
            col_width=20.0,
            title="AREA TABLE",
            headers=["Space", "Area"],
            data=[["Room 1", "25.0"], ["Room 2", "18.5"]],
        )
        assert h is not None


class TestEzdxfAdapterTransformations:
    """Test entity transformations in headless DXF."""

    def test_move_entities(self, adapter):
        h = adapter.draw_line((0, 0), (10, 0))
        assert adapter.move_entities([h], offset_x=5.0, offset_y=3.0) is True

    def test_rotate_entities(self, adapter):
        h = adapter.draw_line((0, 0), (10, 0))
        assert adapter.rotate_entities([h], angle=90.0, center_x=0.0, center_y=0.0) is True

    def test_scale_entities(self, adapter):
        h = adapter.draw_line((0, 0), (10, 0))
        assert adapter.scale_entities([h], factor=2.0) is True

    def test_delete_entity(self, adapter):
        h = adapter.draw_circle((0, 0), 5.0)
        assert adapter.delete_entity(h) is True
        assert adapter.get_entity_properties(h) == {}


class TestEzdxfAdapterAreaCalculations:
    """Test area and perimeter computations (AECO)."""

    def test_rectangle_area(self, adapter):
        h = adapter.draw_rectangle((0, 0), (10, 5))
        area_info = adapter.get_entity_area(h)
        assert area_info["area"] == pytest.approx(50.0, 0.01)
        assert area_info["perimeter"] == pytest.approx(30.0, 0.01)

    def test_circle_area(self, adapter):
        r = 4.0
        h = adapter.draw_circle((0, 0), radius=r)
        area_info = adapter.get_entity_area(h)
        expected_area = math.pi * r * r
        expected_perim = 2.0 * math.pi * r
        assert area_info["area"] == pytest.approx(expected_area, 0.01)
        assert area_info["perimeter"] == pytest.approx(expected_perim, 0.01)

    def test_file_save_and_reload(self, adapter):
        adapter.create_layer("TEST_SAVE", color="blue")
        adapter.draw_line((0, 0), (50, 50), layer="TEST_SAVE")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test_output.dxf")
            assert adapter.save_drawing(out_file) is True
            assert os.path.exists(out_file)

            # Reload
            new_ad = EzdxfAdapter(out_file)
            assert "TEST_SAVE" in new_ad.list_layers()
