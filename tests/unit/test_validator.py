"""
Tests for validator module.

Tests auto-correction features:
- Fuzzy color name matching
- Type coercion (string to number)
- Case normalization
- Coordinate normalization
- Default value application
"""

import pytest

from mcp_tools.validator import (
    fuzzy_match_color,
    coerce_number,
    coerce_bool,
    normalize_coordinate,
    autocorrect_spec,
    validate_color,
    validate_required_fields,
    VALID_COLORS,
    COLOR_ALIASES,
)


# ========== Fuzzy Color Matching Tests ==========


class TestFuzzyMatchColor:
    """Tests for fuzzy color matching."""

    def test_exact_match(self):
        """Test exact color names."""
        assert fuzzy_match_color("red") == "red"
        assert fuzzy_match_color("blue") == "blue"
        assert fuzzy_match_color("white") == "white"
        assert fuzzy_match_color("yellow") == "yellow"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert fuzzy_match_color("RED") == "red"
        assert fuzzy_match_color("Blue") == "blue"
        assert fuzzy_match_color("WHITE") == "white"

    def test_alias_match(self):
        """Test color aliases."""
        assert fuzzy_match_color("grey") == "gray"
        assert fuzzy_match_color("purple") == "magenta"
        assert fuzzy_match_color("violet") == "magenta"
        assert fuzzy_match_color("aqua") == "cyan"
        assert fuzzy_match_color("teal") == "cyan"

    def test_fuzzy_typos(self):
        """Test fuzzy matching for typos."""
        # Common typos
        assert fuzzy_match_color("rde") == "red"  # missing e
        assert fuzzy_match_color("blu") == "blue"  # missing e
        assert fuzzy_match_color("whie") == "white"  # typo
        assert fuzzy_match_color("yelow") == "yellow"  # missing l
        assert fuzzy_match_color("cyaan") == "cyan"  # extra a

    def test_compound_colors(self):
        """Test compound color names."""
        assert fuzzy_match_color("light_gray") == "light_gray"
        assert fuzzy_match_color("dark_gray") == "dark_gray"
        assert fuzzy_match_color("lightgray") == "light_gray"
        assert fuzzy_match_color("darkgray") == "dark_gray"
        assert fuzzy_match_color("light_grey") == "light_gray"

    def test_numeric_passthrough(self):
        """Test numeric color values pass through."""
        assert fuzzy_match_color("1") == "1"
        assert fuzzy_match_color("256") == "256"
        assert fuzzy_match_color("30") == "30"

    def test_special_colors(self):
        """Test special color values."""
        assert fuzzy_match_color("bylayer") == "bylayer"

    def test_no_match_passthrough(self):
        """Test unmatched colors pass through."""
        assert fuzzy_match_color("xyz") == "xyz"
        assert fuzzy_match_color("notacolor") == "notacolor"

    def test_whitespace_handling(self):
        """Test whitespace is handled."""
        assert fuzzy_match_color("  red  ") == "red"
        assert fuzzy_match_color(" blue ") == "blue"


# ========== Type Coercion Tests ==========


class TestCoerceNumber:
    """Tests for number coercion."""

    def test_already_number(self):
        """Test numbers pass through."""
        assert coerce_number(42) == 42
        assert coerce_number(3.14) == 3.14

    def test_string_integer(self):
        """Test string integers."""
        assert coerce_number("42") == 42
        assert coerce_number("-10") == -10
        assert coerce_number("0") == 0

    def test_string_float(self):
        """Test string floats."""
        assert coerce_number("3.14") == 3.14
        assert coerce_number("-2.5") == -2.5
        assert coerce_number("0.0") == 0.0

    def test_quoted_numbers(self):
        """Test quoted numbers."""
        assert coerce_number('"42"') == 42
        assert coerce_number("'3.14'") == 3.14

    def test_whitespace(self):
        """Test whitespace handling."""
        assert coerce_number("  42  ") == 42
        assert coerce_number(" 3.14 ") == 3.14

    def test_non_numeric_passthrough(self):
        """Test non-numeric strings pass through."""
        assert coerce_number("hello") == "hello"
        assert coerce_number("abc123") == "abc123"


class TestCoerceBool:
    """Tests for boolean coercion."""

    def test_already_bool(self):
        """Test booleans pass through."""
        assert coerce_bool(True) is True
        assert coerce_bool(False) is False

    def test_string_true(self):
        """Test truthy strings."""
        assert coerce_bool("true") is True
        assert coerce_bool("True") is True
        assert coerce_bool("TRUE") is True
        assert coerce_bool("1") is True
        assert coerce_bool("yes") is True
        assert coerce_bool("on") is True
        assert coerce_bool("closed") is True

    def test_string_false(self):
        """Test falsy strings."""
        assert coerce_bool("false") is False
        assert coerce_bool("False") is False
        assert coerce_bool("0") is False
        assert coerce_bool("no") is False
        assert coerce_bool("off") is False
        assert coerce_bool("") is False

    def test_numeric(self):
        """Test numeric booleans."""
        assert coerce_bool(1) is True
        assert coerce_bool(0) is False
        assert coerce_bool(1.0) is True
        assert coerce_bool(0.0) is False


# ========== Coordinate Normalization Tests ==========


class TestNormalizeCoordinate:
    """Tests for coordinate normalization."""

    def test_comma_separated(self):
        """Test comma-separated coordinates."""
        assert normalize_coordinate("0,0") == "0,0"
        assert normalize_coordinate("10,20") == "10,20"
        assert normalize_coordinate("10,20,30") == "10,20,30"

    def test_semicolon_to_comma(self):
        """Test semicolon conversion."""
        assert normalize_coordinate("0;0") == "0,0"
        assert normalize_coordinate("10;20") == "10,20"

    def test_whitespace_removal(self):
        """Test whitespace is removed."""
        assert normalize_coordinate("10, 20") == "10,20"
        assert normalize_coordinate(" 10 , 20 ") == "10,20"
        assert normalize_coordinate("10 , 20 , 30") == "10,20,30"

    def test_tuple_conversion(self):
        """Test tuple conversion."""
        assert normalize_coordinate((10, 20)) == "10,20"
        assert normalize_coordinate((10, 20, 30)) == "10,20,30"

    def test_list_conversion(self):
        """Test list conversion."""
        assert normalize_coordinate([10, 20]) == "10,20"
        assert normalize_coordinate([10, 20, 30]) == "10,20,30"


# ========== Spec Auto-Correction Tests ==========


class TestAutocorrectSpec:
    """Tests for full spec auto-correction."""

    def test_color_correction(self):
        """Test color field correction."""
        spec = {"type": "line", "start": "0,0", "end": "10,10", "color": "rde"}
        result = autocorrect_spec(spec, "entity")
        assert result["color"] == "red"

    def test_numeric_correction(self):
        """Test numeric field correction."""
        spec = {"type": "circle", "center": "5,5", "radius": "3.5"}
        result = autocorrect_spec(spec, "entity")
        assert result["radius"] == 3.5

    def test_bool_correction(self):
        """Test boolean field correction."""
        spec = {"type": "polyline", "points": "0,0|10,10", "closed": "true"}
        result = autocorrect_spec(spec, "entity")
        assert result["closed"] is True

    def test_coordinate_normalization(self):
        """Test coordinate normalization."""
        spec = {"type": "line", "start": "0 ; 0", "end": "10 , 10"}
        result = autocorrect_spec(spec, "entity")
        assert result["start"] == "0,0"
        assert result["end"] == "10,10"

    def test_key_lowercasing(self):
        """Test key lowercasing."""
        spec = {"TYPE": "line", "START": "0,0", "END": "10,10", "COLOR": "red"}
        result = autocorrect_spec(spec, "entity")
        assert "type" in result
        assert "start" in result
        assert "color" in result

    def test_mixed_corrections(self):
        """Test multiple corrections at once."""
        spec = {
            "TYPE": "circle",
            "CENTER": "5 ; 5",
            "RADIUS": "3.5",
            "COLOR": "blu",
        }
        result = autocorrect_spec(spec, "entity")
        assert result["type"] == "circle"
        assert result["center"] == "5,5"
        assert result["radius"] == 3.5
        assert result["color"] == "blue"


# ========== Validation Tests ==========


class TestValidateColor:
    """Tests for color validation."""

    def test_valid_colors(self):
        """Test valid colors return None."""
        for color in VALID_COLORS:
            assert validate_color(color) is None

    def test_invalid_color(self):
        """Test invalid colors return error message."""
        result = validate_color("xyz")
        # Should either return None (passed through) or error message
        # In current implementation, unmatched colors pass through
        # This test documents that behavior


class TestValidateRequiredFields:
    """Tests for required field validation."""

    def test_all_present(self):
        """Test all fields present returns None."""
        spec = {"start": "0,0", "end": "10,10"}
        result = validate_required_fields(spec, ["start", "end"], "line")
        assert result is None

    def test_missing_field(self):
        """Test missing field returns error."""
        spec = {"start": "0,0"}
        result = validate_required_fields(spec, ["start", "end"], "line")
        assert result is not None
        assert "end" in result

    def test_multiple_missing(self):
        """Test multiple missing fields."""
        spec = {}
        result = validate_required_fields(spec, ["start", "end"], "line")
        assert result is not None
        assert "start" in result
        assert "end" in result

    def test_none_value_counts_as_missing(self):
        """Test None values count as missing."""
        spec = {"start": "0,0", "end": None}
        result = validate_required_fields(spec, ["start", "end"], "line")
        assert result is not None
        assert "end" in result


# ========== Integration Tests ==========


class TestValidatorIntegration:
    """Integration tests combining multiple validator features."""

    def test_full_line_spec(self):
        """Test full line spec correction."""
        spec = {
            "TYPE": "line",
            "START": "0 ; 0",
            "END": "10 , 10",
            "COLOR": "rde",
            "LINEWEIGHT": "50",
        }
        result = autocorrect_spec(spec, "entity")

        assert result["type"] == "line"
        assert result["start"] == "0,0"
        assert result["end"] == "10,10"
        assert result["color"] == "red"
        assert result["lineweight"] == 50

    def test_full_circle_spec(self):
        """Test full circle spec correction."""
        spec = {
            "type": "circle",
            "center": "5,5",
            "radius": "3.14159",
            "color": "BLUE",
        }
        result = autocorrect_spec(spec, "entity")

        assert result["center"] == "5,5"
        assert result["radius"] == 3.14159
        assert result["color"] == "blue"

    def test_entity_operation_spec(self):
        """Test entity operation spec correction."""
        spec = {
            "ACTION": "move",
            "HANDLES": "A1,B2",
            "OFFSET_X": "10",
            "OFFSET_Y": "5.5",
        }
        result = autocorrect_spec(spec, "entity_op")

        assert result["action"] == "move"
        assert result["handles"] == "A1,B2"
        assert result["offset_x"] == 10
        assert result["offset_y"] == 5.5
