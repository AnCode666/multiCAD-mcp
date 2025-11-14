"""
Unit tests for NLP processor.
Tests parsing of natural language commands.
"""

import pytest
from src.nlp import NLPProcessor, ParsedCommand


class TestNLPProcessor:
    """Test suite for NLPProcessor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = NLPProcessor(strict_mode=False)
        self.strict_processor = NLPProcessor(strict_mode=True)

    def test_parse_draw_line_command(self):
        """Test parsing of draw line command."""
        command = "draw a line from 0,0 to 100,100"
        result = self.processor.parse_command(command)

        assert isinstance(result, ParsedCommand)
        assert result.operation == "draw_line"
        assert "start" in result.parameters
        assert "end" in result.parameters
        assert result.parameters["start"] == (0.0, 0.0)
        assert result.parameters["end"] == (100.0, 100.0)

    def test_parse_draw_circle_command(self):
        """Test parsing of draw circle command."""
        command = "create a blue circle at 50,50 with radius 25"
        result = self.processor.parse_command(command)

        assert result.operation == "draw_circle"
        assert result.parameters["center"] == (50.0, 50.0)
        assert result.parameters["radius"] == 25.0
        assert result.parameters["color"] == "blue"

    def test_parse_rectangle_command(self):
        """Test parsing of rectangle command."""
        command = "draw a red rectangle from 0,0 to 100,100"
        result = self.processor.parse_command(command)

        assert result.operation == "draw_rectangle"
        assert result.parameters["corner1"] == (0.0, 0.0)
        assert result.parameters["corner2"] == (100.0, 100.0)
        assert result.parameters["color"] == "red"

    def test_parse_polyline_command(self):
        """Test parsing of polyline command."""
        command = "draw a polyline with points 0,0 100,0 100,100"
        result = self.processor.parse_command(command)

        assert result.operation == "draw_polyline"
        assert "points" in result.parameters
        assert len(result.parameters["points"]) == 3
        assert result.parameters["points"][0] == (0.0, 0.0)
        assert result.parameters["points"][1] == (100.0, 0.0)
        assert result.parameters["points"][2] == (100.0, 100.0)
        assert result.parameters["closed"] == False

    def test_parse_closed_polyline_command(self):
        """Test parsing of closed polyline command."""
        command = "draw a closed polyline with points 0,0 100,0 100,100 0,100"
        result = self.processor.parse_command(command)

        assert result.operation == "draw_polyline"
        assert result.parameters["closed"] == True
        assert len(result.parameters["points"]) == 4

    def test_parse_colored_polyline_command(self):
        """Test parsing of colored polyline command."""
        command = "create a red polyline through 10,10 50,50 90,10"
        result = self.processor.parse_command(command)

        assert result.operation == "draw_polyline"
        assert result.parameters["color"] == "red"
        assert len(result.parameters["points"]) == 3

    def test_parse_polygon_as_polyline(self):
        """Test that polygon keyword maps to polyline."""
        command = "draw a polygon with points 0,0 50,0 25,50"
        result = self.processor.parse_command(command)

        assert result.operation == "draw_polyline"
        assert len(result.parameters["points"]) == 3

    def test_parse_text_command(self):
        """Test parsing of text command."""
        command = 'add text "Hello World" at 10,10 with height 5'
        result = self.processor.parse_command(command)

        assert result.operation == "draw_text"
        assert result.parameters["position"] == (10.0, 10.0)
        assert result.parameters["text"] == "Hello World"
        assert result.parameters["height"] == 5.0

    def test_color_extraction(self):
        """Test color extraction from commands."""
        assert self.processor._extract_color("red line") == "red"
        assert self.processor._extract_color("blue circle") == "blue"
        assert self.processor._extract_color("green rectangle") == "green"
        assert self.processor._extract_color("unknown") == "white"  # Default

    def test_layer_extraction(self):
        """Test layer extraction from commands."""
        assert self.processor._extract_layer('on layer "MyLayer"') == "MyLayer"
        assert self.processor._extract_layer("layer Construction") == "Construction"
        assert self.processor._extract_layer("default") == "0"  # Default

    def test_coordinate_extraction(self):
        """Test coordinate extraction."""
        # Test 2D coordinates
        pt = self.processor._extract_single_point("point at 10,20")
        assert pt == (10.0, 20.0)

        # Test with spaces
        pt = self.processor._extract_single_point("point at 10, 20")
        assert pt == (10.0, 20.0)

        # Test parentheses
        pt = self.processor._extract_single_point("point at (10,20)")
        assert pt == (10.0, 20.0)

    def test_multiple_coordinates(self):
        """Test extraction of multiple coordinates."""
        points = self.processor._extract_multiple_points("10,20 30,40 50,60")
        assert len(points) == 3
        assert points[0] == (10.0, 20.0)
        assert points[1] == (30.0, 40.0)
        assert points[2] == (50.0, 60.0)

    def test_radius_extraction(self):
        """Test radius extraction."""
        assert self.processor._extract_radius("radius 25") == 25.0
        assert self.processor._extract_radius("r = 50") == 50.0
        assert self.processor._extract_radius("no radius") == 50.0  # Default

    def test_angle_extraction(self):
        """Test angle extraction."""
        assert self.processor._extract_angle("start angle 45") == 45.0
        assert self.processor._extract_angle("end angle 180") == 180.0
        assert self.processor._extract_angle("no angle") == 0.0  # Default

    def test_text_height_extraction(self):
        """Test text height extraction."""
        assert self.processor._extract_text_height("height 10") == 10.0
        assert self.processor._extract_text_height("size 5.5") == 5.5
        assert self.processor._extract_text_height("default") == 2.5  # Default

    def test_command_type_identification(self):
        """Test command type identification."""
        assert self.processor._identify_command_type("draw a line") == "draw"
        assert self.processor._identify_command_type("create a circle") == "draw"
        assert self.processor._identify_command_type("erase that line") == "erase"
        assert self.processor._identify_command_type("move the shape") == "move"

    def test_shape_type_identification(self):
        """Test shape type identification."""
        assert self.processor._identify_shape_type("draw a line") == "line"
        assert self.processor._identify_shape_type("create a circle") == "circle"
        assert self.processor._identify_shape_type("arc from 0 to 180") == "arc"
        assert self.processor._identify_shape_type("rectangle bounds") == "rectangle"
        assert self.processor._identify_shape_type("polyline path") == "polyline"
        assert self.processor._identify_shape_type("polygon shape") == "polyline"
        assert self.processor._identify_shape_type("ellipse shape") == "ellipse"

    def test_strict_mode_raises_on_missing_params(self):
        """Test that strict mode raises when parameters are missing."""
        strict = NLPProcessor(strict_mode=True)

        # This should work - has required parameters
        result = strict.parse_command("draw line from 0,0 to 100,100")
        assert result.operation == "draw_line"

        # This should raise - missing required coordinates
        with pytest.raises(ValueError):
            strict.parse_command("draw line without coordinates")

    def test_lenient_mode_uses_defaults(self):
        """Test that lenient mode uses defaults for missing parameters."""
        lenient = NLPProcessor(strict_mode=False)

        result = lenient.parse_command("draw a circle")
        assert result.operation == "draw_circle"
        # Should use defaults
        assert result.parameters["center"] == (0.0, 0.0)
        assert result.parameters["radius"] == 50.0

    def test_confidence_scoring(self):
        """Test confidence scoring."""
        # Explicit command should have high confidence
        result1 = self.processor.parse_command(
            "draw a red line from 0,0 to 100,100 on layer MyLayer"
        )
        conf1 = result1.confidence

        # Vague command should have lower confidence
        result2 = self.processor.parse_command("line")
        conf2 = result2.confidence

        assert conf1 > conf2

    def test_coordinate_with_decimals(self):
        """Test extraction of decimal coordinates."""
        pt = self.processor._extract_single_point("point at 10.5, 20.75")
        assert pt == (10.5, 20.75)

    def test_negative_coordinates(self):
        """Test extraction of negative coordinates."""
        pt = self.processor._extract_single_point("point at -10, -20")
        assert pt == (-10.0, -20.0)

    def test_hatch_pattern_extraction(self):
        """Test hatch pattern extraction."""
        assert self.processor._extract_hatch_pattern("solid fill") == "SOLID"
        assert self.processor._extract_hatch_pattern("angle pattern") == "ANGLE"
        assert self.processor._extract_hatch_pattern("cross hatch") == "CROSS"


class TestParsedCommand:
    """Test suite for ParsedCommand dataclass."""

    def test_parsed_command_creation(self):
        """Test ParsedCommand creation."""
        cmd = ParsedCommand(
            operation="draw_line",
            parameters={"start": (0, 0), "end": (100, 100)},
            confidence=0.95,
            raw_text="draw a line from 0,0 to 100,100",
        )

        assert cmd.operation == "draw_line"
        assert cmd.parameters["start"] == (0, 0)
        assert cmd.confidence == 0.95
        assert "draw" in cmd.raw_text


class TestLayerCommands:
    """Test suite for layer management commands."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = NLPProcessor(strict_mode=False)

    def test_parse_create_layer_command(self):
        """Test parsing of create layer command."""
        command = "create layer MyLayer"
        result = self.processor.parse_command(command)

        assert result.operation == "create_layer"
        assert result.parameters["name"] == "MyLayer"  # Preserve case
        assert result.confidence > 0.8

    def test_parse_create_layer_with_color(self):
        """Test parsing of create layer command with color."""
        command = "create a red layer walls"
        result = self.processor.parse_command(command)

        assert result.operation == "create_layer"
        assert result.parameters["name"] == "walls"
        assert result.parameters["color"] == "red"

    def test_parse_delete_layer_command(self):
        """Test parsing of delete layer command."""
        command = "delete layer unused"
        result = self.processor.parse_command(command)

        assert result.operation == "delete_layer"
        assert result.parameters["name"] == "unused"

    def test_parse_rename_layer_command(self):
        """Test parsing of rename layer command."""
        command = "rename layer old_name to new_name"
        result = self.processor.parse_command(command)

        assert result.operation == "rename_layer"
        assert result.parameters["old_name"] == "old_name"
        assert result.parameters["new_name"] == "new_name"

    def test_parse_rename_layer_quoted(self):
        """Test parsing of rename layer with quoted names."""
        command = 'rename "OldLayer" to "NewLayer"'
        result = self.processor.parse_command(command)

        assert result.operation == "rename_layer"
        assert result.parameters["old_name"].lower() == "oldlayer"
        assert result.parameters["new_name"].lower() == "newlayer"

    def test_parse_turn_on_layer_command(self):
        """Test parsing of turn on layer command."""
        command = "turn on layer construction"
        result = self.processor.parse_command(command)

        assert result.operation == "turn_layer_on"
        assert result.parameters["name"] == "construction"

    def test_parse_show_layer_command(self):
        """Test parsing of show layer command (alias for turn on)."""
        command = "show layer guides"
        result = self.processor.parse_command(command)

        assert result.operation == "turn_layer_on"
        assert result.parameters["name"] == "guides"

    def test_parse_turn_off_layer_command(self):
        """Test parsing of turn off layer command."""
        command = "turn off layer construction"
        result = self.processor.parse_command(command)

        assert result.operation == "turn_layer_off"
        assert result.parameters["name"] == "construction"

    def test_parse_hide_layer_command(self):
        """Test parsing of hide layer command (alias for turn off)."""
        command = "hide layer guides"
        result = self.processor.parse_command(command)

        assert result.operation == "turn_layer_off"
        assert result.parameters["name"] == "guides"

    def test_parse_list_layers_command(self):
        """Test parsing of list layers command."""
        command = "list all layers"
        result = self.processor.parse_command(command)

        assert result.operation == "list_layers"
        assert result.confidence > 0.9

    def test_layer_command_with_quoted_name(self):
        """Test layer command with quoted layer name."""
        command = 'delete layer "construction-temp"'
        result = self.processor.parse_command(command)

        assert result.operation == "delete_layer"
        assert result.parameters["name"] == "construction-temp"

    def test_create_layer_with_lineweight(self):
        """Test creating layer with lineweight."""
        command = "create layer walls with lineweight 20"
        result = self.processor.parse_command(command)

        assert result.operation == "create_layer"
        assert result.parameters["name"] == "walls"
        assert result.parameters["lineweight"] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
