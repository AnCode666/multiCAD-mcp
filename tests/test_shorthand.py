"""
Tests for shorthand parser module.

Tests all shorthand parsing scenarios including:
- Drawing entities (line, circle, rect, text, arc, polyline, spline)
- Entity operations (select, move, rotate, scale, etc.)
- Layer operations (create, delete, on, off, etc.)
- Block operations (list, info, insert, create)
- File operations (save, new, close, list, switch)
- JSON fallback compatibility
- Multi-line and semicolon-separated inputs
"""

import pytest

from mcp_tools.shorthand import (
    parse_drawing_input,
    parse_entity_ops_input,
    parse_layer_ops_input,
    parse_block_ops_input,
    parse_file_ops_input,
    parse_entity_shorthand,
    parse_entity_op_shorthand,
    parse_layer_op_shorthand,
    parse_block_op_shorthand,
    parse_file_op_shorthand,
)


# ========== Drawing Entity Tests ==========


class TestDrawingShorthand:
    """Tests for draw_entities shorthand parsing."""

    def test_line_basic(self):
        """Test basic line parsing."""
        result = parse_entity_shorthand("line|0,0|10,10")
        assert result["type"] == "line"
        assert result["start"] == "0,0"
        assert result["end"] == "10,10"
        assert result["color"] == "white"  # default
        assert result["layer"] == "0"  # default

    def test_line_with_color_and_layer(self):
        """Test line with color and layer."""
        result = parse_entity_shorthand("line|0,0|10,10|red|walls")
        assert result["type"] == "line"
        assert result["start"] == "0,0"
        assert result["end"] == "10,10"
        assert result["color"] == "red"
        assert result["layer"] == "walls"

    def test_circle_basic(self):
        """Test basic circle parsing."""
        result = parse_entity_shorthand("circle|5,5|3")
        assert result["type"] == "circle"
        assert result["center"] == "5,5"
        assert result["radius"] == 3
        assert result["color"] == "white"

    def test_circle_with_color(self):
        """Test circle with color."""
        result = parse_entity_shorthand("circle|5,5|3.5|blue")
        assert result["type"] == "circle"
        assert result["radius"] == 3.5
        assert result["color"] == "blue"

    def test_rect_alias(self):
        """Test rect alias for rectangle."""
        result = parse_entity_shorthand("rect|0,0|20,15")
        assert result["type"] == "rectangle"
        assert result["corner1"] == "0,0"
        assert result["corner2"] == "20,15"

    def test_rectangle_full(self):
        """Test full rectangle."""
        result = parse_entity_shorthand("rectangle|0,0|20,15|green|boxes")
        assert result["type"] == "rectangle"
        assert result["color"] == "green"
        assert result["layer"] == "boxes"

    def test_text_basic(self):
        """Test basic text parsing."""
        result = parse_entity_shorthand("text|5,5|Hello World")
        assert result["type"] == "text"
        assert result["position"] == "5,5"
        assert result["text"] == "Hello World"
        assert result["height"] == 2.5  # default

    def test_text_with_height(self):
        """Test text with height."""
        result = parse_entity_shorthand("text|5,5|Hello|3.0|red")
        assert result["type"] == "text"
        assert result["text"] == "Hello"
        assert result["height"] == 3.0
        assert result["color"] == "red"

    def test_arc_basic(self):
        """Test basic arc parsing."""
        result = parse_entity_shorthand("arc|0,0|5|0|90")
        assert result["type"] == "arc"
        assert result["center"] == "0,0"
        assert result["radius"] == 5
        assert result["start_angle"] == 0
        assert result["end_angle"] == 90

    def test_arc_with_color(self):
        """Test arc with color."""
        result = parse_entity_shorthand("arc|10,10|5|45|180|cyan")
        assert result["type"] == "arc"
        assert result["color"] == "cyan"

    def test_polyline_basic(self):
        """Test basic polyline with semicolon points."""
        result = parse_entity_shorthand("polyline|0,0;10,10;20,0")
        assert result["type"] == "polyline"
        # Points converted from semicolon to pipe for adapter
        assert result["points"] == "0,0|10,10|20,0"
        assert result["closed"] is False

    def test_polyline_closed(self):
        """Test closed polyline."""
        result = parse_entity_shorthand("polyline|0,0;10,10;20,0|closed")
        assert result["type"] == "polyline"
        assert result["closed"] is True

    def test_polyline_with_color(self):
        """Test polyline with color."""
        result = parse_entity_shorthand("polyline|0,0;10,10;20,0|closed|yellow")
        assert result["type"] == "polyline"
        assert result["closed"] is True
        assert result["color"] == "yellow"

    def test_spline_basic(self):
        """Test basic spline parsing."""
        result = parse_entity_shorthand("spline|0,0;5,10;10,0")
        assert result["type"] == "spline"
        assert result["points"] == "0,0|5,10|10,0"

    def test_dimension_basic(self):
        """Test dimension parsing."""
        result = parse_entity_shorthand("dimension|0,0|10,0")
        assert result["type"] == "dimension"
        assert result["start"] == "0,0"
        assert result["end"] == "10,0"

    def test_unknown_type(self):
        """Test unknown entity type."""
        result = parse_entity_shorthand("unknown|0,0|10,10")
        assert "error" in result

    def test_case_insensitive(self):
        """Test case insensitivity."""
        result = parse_entity_shorthand("LINE|0,0|10,10|RED")
        assert result["type"] == "line"
        assert result["color"] == "red"


class TestDrawingInput:
    """Tests for parse_drawing_input (multi-entity)."""

    def test_single_line(self):
        """Test single entity input."""
        result = parse_drawing_input("line|0,0|10,10|red")
        assert len(result) == 1
        assert result[0]["type"] == "line"

    def test_multi_line(self):
        """Test multi-line input."""
        input_str = """line|0,0|10,10|red
circle|5,5|3|blue
rect|0,0|20,15"""
        result = parse_drawing_input(input_str)
        assert len(result) == 3
        assert result[0]["type"] == "line"
        assert result[1]["type"] == "circle"
        assert result[2]["type"] == "rectangle"

    def test_json_fallback(self):
        """Test JSON format fallback."""
        json_input = '[{"type": "line", "start": "0,0", "end": "10,10", "color": "red"}]'
        result = parse_drawing_input(json_input)
        assert len(result) == 1
        assert result[0]["type"] == "line"
        assert result[0]["color"] == "red"

    def test_json_single_object(self):
        """Test single JSON object."""
        json_input = '{"type": "circle", "center": "5,5", "radius": 3}'
        result = parse_drawing_input(json_input)
        assert len(result) == 1
        assert result[0]["type"] == "circle"

    def test_empty_lines_ignored(self):
        """Test empty lines are ignored."""
        input_str = """line|0,0|10,10

circle|5,5|3

"""
        result = parse_drawing_input(input_str)
        assert len(result) == 2


# ========== Entity Operations Tests ==========


class TestEntityOpShorthand:
    """Tests for entity operation shorthand parsing."""

    def test_select_by_layer(self):
        """Test select by layer."""
        result = parse_entity_op_shorthand("select|layer|walls")
        assert result["action"] == "select"
        assert result["by"] == "layer"
        assert result["value"] == "walls"

    def test_select_by_color(self):
        """Test select by color."""
        result = parse_entity_op_shorthand("select|color|red")
        assert result["action"] == "select"
        assert result["by"] == "color"
        assert result["value"] == "red"

    def test_move_basic(self):
        """Test basic move."""
        result = parse_entity_op_shorthand("move|A1,B2,C3|10|5")
        assert result["action"] == "move"
        assert result["handles"] == "A1,B2,C3"
        assert result["offset_x"] == 10
        assert result["offset_y"] == 5

    def test_rotate_basic(self):
        """Test basic rotate."""
        result = parse_entity_op_shorthand("rotate|A1|45|0|0")
        assert result["action"] == "rotate"
        assert result["handles"] == "A1"
        assert result["angle"] == 45
        assert result["center_x"] == 0
        assert result["center_y"] == 0

    def test_rotate_defaults(self):
        """Test rotate with default center."""
        result = parse_entity_op_shorthand("rotate|A1|45")
        assert result["action"] == "rotate"
        assert result["angle"] == 45
        assert result["center_x"] == 0
        assert result["center_y"] == 0

    def test_scale_basic(self):
        """Test basic scale."""
        result = parse_entity_op_shorthand("scale|A1,B2|2.0|0|0")
        assert result["action"] == "scale"
        assert result["scale_factor"] == 2.0

    def test_set_color(self):
        """Test set color."""
        result = parse_entity_op_shorthand("set_color|A1,B2|red")
        assert result["action"] == "set_color"
        assert result["handles"] == "A1,B2"
        assert result["color"] == "red"

    def test_set_layer(self):
        """Test set layer."""
        result = parse_entity_op_shorthand("set_layer|A1|walls")
        assert result["action"] == "set_layer"
        assert result["layer_name"] == "walls"

    def test_copy(self):
        """Test copy."""
        result = parse_entity_op_shorthand("copy|A1,B2")
        assert result["action"] == "copy"
        assert result["handles"] == "A1,B2"

    def test_delete(self):
        """Test delete."""
        result = parse_entity_op_shorthand("delete|A1,B2,C3")
        assert result["action"] == "delete"
        assert result["handles"] == "A1,B2,C3"

    def test_paste(self):
        """Test paste."""
        result = parse_entity_op_shorthand("paste|100,200")
        assert result["action"] == "paste"
        assert result["base_point"] == "100,200"


class TestEntityOpsInput:
    """Tests for parse_entity_ops_input (multi-operation)."""

    def test_multi_line(self):
        """Test multi-line operations."""
        input_str = """select|layer|walls
move|A1,B2|10|5
set_color|A1,B2|red"""
        result = parse_entity_ops_input(input_str)
        assert len(result) == 3
        assert result[0]["action"] == "select"
        assert result[1]["action"] == "move"
        assert result[2]["action"] == "set_color"

    def test_json_fallback(self):
        """Test JSON fallback."""
        json_input = '[{"action": "move", "handles": "A1", "offset_x": 10, "offset_y": 5}]'
        result = parse_entity_ops_input(json_input)
        assert len(result) == 1
        assert result[0]["action"] == "move"


# ========== Layer Operations Tests ==========


class TestLayerOpShorthand:
    """Tests for layer operation shorthand parsing."""

    def test_create_basic(self):
        """Test basic create."""
        result = parse_layer_op_shorthand("create|walls")
        assert result["action"] == "create"
        assert result["name"] == "walls"
        assert result["color"] == "white"
        assert result["lineweight"] == 25

    def test_create_full(self):
        """Test full create."""
        result = parse_layer_op_shorthand("create|walls|red|50")
        assert result["name"] == "walls"
        assert result["color"] == "red"
        assert result["lineweight"] == 50

    def test_delete(self):
        """Test delete."""
        result = parse_layer_op_shorthand("delete|temp")
        assert result["action"] == "delete"
        assert result["name"] == "temp"

    def test_rename(self):
        """Test rename."""
        result = parse_layer_op_shorthand("rename|Layer1|furniture")
        assert result["action"] == "rename"
        assert result["old_name"] == "Layer1"
        assert result["new_name"] == "furniture"

    def test_on_alias(self):
        """Test 'on' alias for turn_on."""
        result = parse_layer_op_shorthand("on|walls,doors")
        assert result["action"] == "turn_on"
        assert result["names"] == ["walls", "doors"]

    def test_off_alias(self):
        """Test 'off' alias for turn_off."""
        result = parse_layer_op_shorthand("off|Defpoints")
        assert result["action"] == "turn_off"
        assert result["names"] == ["Defpoints"]

    def test_set_color(self):
        """Test set color."""
        result = parse_layer_op_shorthand("set_color|0|white")
        assert result["action"] == "set_color"
        assert result["name"] == "0"
        assert result["color"] == "white"

    def test_list(self):
        """Test list."""
        result = parse_layer_op_shorthand("list")
        assert result["action"] == "list"

    def test_info(self):
        """Test info."""
        result = parse_layer_op_shorthand("info")
        assert result["action"] == "info"

    def test_is_on(self):
        """Test is_on."""
        result = parse_layer_op_shorthand("is_on|walls")
        assert result["action"] == "is_on"
        assert result["name"] == "walls"


class TestLayerOpsInput:
    """Tests for parse_layer_ops_input (multi-operation)."""

    def test_multi_line(self):
        """Test multi-line operations."""
        input_str = """create|walls|red
create|doors|blue
off|Defpoints"""
        result = parse_layer_ops_input(input_str)
        assert len(result) == 3


# ========== Block Operations Tests ==========


class TestBlockOpShorthand:
    """Tests for block operation shorthand parsing."""

    def test_list(self):
        """Test list."""
        result = parse_block_op_shorthand("list")
        assert result["action"] == "list"

    def test_info_basic(self):
        """Test basic info."""
        result = parse_block_op_shorthand("info|Door")
        assert result["action"] == "info"
        assert result["block_name"] == "Door"
        assert result["include"] == "info"

    def test_info_with_include(self):
        """Test info with include."""
        result = parse_block_op_shorthand("info|Door|both")
        assert result["include"] == "both"

    def test_insert_basic(self):
        """Test basic insert."""
        result = parse_block_op_shorthand("insert|Door|10,20")
        assert result["action"] == "insert"
        assert result["block_name"] == "Door"
        assert result["insertion_point"] == "10,20"
        assert result["scale"] == 1.0
        assert result["rotation"] == 0.0

    def test_insert_full(self):
        """Test full insert."""
        result = parse_block_op_shorthand("insert|Door|10,20|1.5|90|walls")
        assert result["scale"] == 1.5
        assert result["rotation"] == 90
        assert result["layer"] == "walls"

    def test_create_basic(self):
        """Test basic create."""
        result = parse_block_op_shorthand("create|MyBlock")
        assert result["action"] == "create"
        assert result["block_name"] == "MyBlock"

    def test_create_with_handles(self):
        """Test create with handles."""
        result = parse_block_op_shorthand("create|MyBlock|A1,B2,C3|0,0|Description")
        assert result["entity_handles"] == ["A1", "B2", "C3"]
        assert result["insertion_point"] == "0,0"
        assert result["description"] == "Description"


# ========== File Operations Tests ==========


class TestFileOpShorthand:
    """Tests for file operation shorthand parsing."""

    def test_save_with_path(self):
        """Test save with full path."""
        result = parse_file_op_shorthand("save|/path/to/file.dwg")
        assert result["action"] == "save"
        assert result["filepath"] == "/path/to/file.dwg"

    def test_save_with_filename(self):
        """Test save with filename only."""
        result = parse_file_op_shorthand("save|backup.dwg")
        assert result["action"] == "save"
        assert result["filename"] == "backup.dwg"

    def test_save_with_format(self):
        """Test save with format."""
        result = parse_file_op_shorthand("save|backup.dxf|dxf")
        assert result["filename"] == "backup.dxf"
        assert result["format"] == "dxf"

    def test_new(self):
        """Test new."""
        result = parse_file_op_shorthand("new")
        assert result["action"] == "new"

    def test_close_default(self):
        """Test close with default."""
        result = parse_file_op_shorthand("close")
        assert result["action"] == "close"
        assert result["save_changes"] is False

    def test_close_save(self):
        """Test close with save."""
        result = parse_file_op_shorthand("close|true")
        assert result["save_changes"] is True

    def test_list(self):
        """Test list."""
        result = parse_file_op_shorthand("list")
        assert result["action"] == "list"

    def test_switch(self):
        """Test switch."""
        result = parse_file_op_shorthand("switch|floor_plan.dwg")
        assert result["action"] == "switch"
        assert result["drawing_name"] == "floor_plan.dwg"


# ========== Edge Cases ==========


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        result = parse_entity_shorthand("  line | 0,0 | 10,10 | red  ")
        assert result["type"] == "line"
        assert result["start"] == "0,0"
        assert result["color"] == "red"

    def test_3d_coordinates(self):
        """Test 3D coordinates."""
        result = parse_entity_shorthand("line|0,0,0|10,10,5|red")
        assert result["start"] == "0,0,0"
        assert result["end"] == "10,10,5"

    def test_float_values(self):
        """Test float values."""
        result = parse_entity_shorthand("circle|5.5,5.5|3.14159")
        assert result["center"] == "5.5,5.5"
        assert result["radius"] == 3.14159

    def test_negative_coordinates(self):
        """Test negative coordinates."""
        result = parse_entity_shorthand("line|-10,-10|10,10")
        assert result["start"] == "-10,-10"
        assert result["end"] == "10,10"

    def test_empty_input(self):
        """Test empty input."""
        result = parse_drawing_input("")
        assert len(result) == 0

    def test_invalid_json_falls_through(self):
        """Test invalid JSON falls through to shorthand."""
        # This looks like JSON but is malformed
        input_str = "[{invalid json"
        # Should not raise, will try shorthand parsing
        result = parse_drawing_input(input_str)
        # Will result in an error entry
        assert len(result) > 0
