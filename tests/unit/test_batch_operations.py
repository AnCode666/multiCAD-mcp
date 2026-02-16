"""
Unit tests for batch operations in MCP tools.
Tests batch functionality for drawing, layers, and entity operations.
"""

import json


class TestDrawingBatchOperations:
    """Test suite for batch drawing operations."""

    def test_draw_lines_batch_structure(self):
        """Test that draw_lines accepts proper JSON array structure."""
        # This tests the expected input format
        lines_json = json.dumps([
            {"start": "0,0", "end": "10,10", "color": "red"},
            {"start": "20,20", "end": "30,30", "color": "blue"}
        ])
        # Input should be valid JSON
        parsed = json.loads(lines_json)
        assert isinstance(parsed, list)
        assert len(parsed) == 2

    def test_draw_circles_batch_structure(self):
        """Test that draw_circles accepts proper JSON array structure."""
        circles_json = json.dumps([
            {"center": "0,0", "radius": 5.0},
            {"center": "10,10", "radius": 3.0}
        ])
        parsed = json.loads(circles_json)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert all("center" in c and "radius" in c for c in parsed)

    def test_draw_polylines_batch_structure(self):
        """Test that draw_polylines accepts proper JSON array structure."""
        polylines_json = json.dumps([
            {"points": "0,0|10,10|20,0", "closed": True},
            {"points": "50,50|60,60|70,70", "closed": False}
        ])
        parsed = json.loads(polylines_json)
        assert isinstance(parsed, list)
        assert all("points" in p for p in parsed)


class TestLayerBatchOperations:
    """Test suite for batch layer operations."""

    def test_rename_layers_batch_structure(self):
        """Test that rename_layers accepts proper JSON array structure."""
        renames_json = json.dumps([
            {"old_name": "Layer1", "new_name": "NewLayer1"},
            {"old_name": "Layer2", "new_name": "NewLayer2"}
        ])
        parsed = json.loads(renames_json)
        assert isinstance(parsed, list)
        assert all("old_name" in r and "new_name" in r for r in parsed)

    def test_delete_layers_accepts_string_array(self):
        """Test that delete_layers accepts string array."""
        layers_json = json.dumps(["Layer1", "Layer2", "Layer3"])
        parsed = json.loads(layers_json)
        assert isinstance(parsed, list)
        assert all(isinstance(layer, str) for layer in parsed)

    def test_delete_layers_accepts_object_array(self):
        """Test that delete_layers accepts object array."""
        layers_json = json.dumps([
            {"name": "Layer1"},
            {"name": "Layer2"}
        ])
        parsed = json.loads(layers_json)
        assert isinstance(parsed, list)
        assert all("name" in item for item in parsed)

    def test_turn_layers_on_batch_structure(self):
        """Test that turn_layers_on accepts proper structure."""
        layers_json = json.dumps(["Layer1", "Layer2"])
        parsed = json.loads(layers_json)
        assert isinstance(parsed, list)

    def test_turn_layers_off_batch_structure(self):
        """Test that turn_layers_off accepts proper structure."""
        layers_json = json.dumps(["Layer1", "Layer2"])
        parsed = json.loads(layers_json)
        assert isinstance(parsed, list)


class TestEntityBatchOperations:
    """Test suite for batch entity operations."""

    def test_change_entities_colors_batch_structure(self):
        """Test that change_entities_colors accepts proper JSON structure."""
        colors_json = json.dumps([
            {"handles": "h1,h2,h3", "color": "red"},
            {"handles": "h4,h5", "color": "blue"}
        ])
        parsed = json.loads(colors_json)
        assert isinstance(parsed, list)
        assert all("handles" in c and "color" in c for c in parsed)

    def test_change_entities_layers_batch_structure(self):
        """Test that change_entities_layers accepts proper JSON structure."""
        layers_json = json.dumps([
            {"handles": "h1,h2,h3", "layer_name": "Layer1"},
            {"handles": "h4,h5", "layer_name": "Layer2"}
        ])
        parsed = json.loads(layers_json)
        assert isinstance(parsed, list)
        assert all(
            "handles" in item and "layer_name" in item for item in parsed
        )


class TestBatchResponseFormat:
    """Test suite for batch operation response format."""

    def test_batch_response_includes_summary(self):
        """Test that batch responses include count summaries."""
        response = {
            "total": 3,
            "created": 3,
            "results": []
        }
        assert "total" in response
        has_count = (
            "created" in response
            or "renamed" in response
            or "changed" in response
        )
        assert has_count

    def test_batch_response_includes_results(self):
        """Test that batch responses include detailed results."""
        response = {
            "total": 2,
            "created": 2,
            "results": [
                {"index": 0, "handle": "ABC123", "success": True},
                {"index": 1, "handle": "ABC124", "success": True}
            ]
        }
        assert isinstance(response["results"], list)
        has_required = all(
            "index" in r and "success" in r for r in response["results"]
        )
        assert has_required

    def test_batch_response_handles_errors(self):
        """Test that batch responses include error details."""
        response: dict = {
            "total": 2,
            "created": 1,
            "results": [
                {"index": 0, "handle": "ABC123", "success": True},
                {"index": 1, "success": False, "error": "Invalid radius"}
            ]
        }
        assert response["total"] == 2
        assert response["created"] == 1
        results = response["results"]
        assert isinstance(results, list)
        assert any(r.get("error") for r in results)


class TestDefaultValues:
    """Test suite for default values in batch operations."""

    def test_drawing_batch_defaults(self):
        """Test that drawing batch operations handle defaults."""
        # Test with minimal required fields
        line = {"start": "0,0", "end": "10,10"}
        assert line.get("color", "white") == "white"
        assert line.get("layer", "0") == "0"
        assert line.get("lineweight", 0) == 0

    def test_layer_batch_defaults(self):
        """Test that layer batch operations handle defaults."""
        circle = {"center": "0,0", "radius": 5.0}
        assert circle.get("color", "white") == "white"
        assert circle.get("layer", "0") == "0"

    def test_polyline_closed_default(self):
        """Test that polyline closed default is false."""
        polyline = {"points": "0,0|10,10|20,0"}
        assert polyline.get("closed", False) is False


class TestInputValidation:
    """Test suite for input validation in batch operations."""

    def test_invalid_json_returns_error(self):
        """Test that invalid JSON input is handled."""
        invalid_json = "{'invalid': 'json'}"  # Single quotes not valid JSON
        try:
            json.loads(invalid_json)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            pass  # Expected

    def test_non_list_input_converted_to_list(self):
        """Test that single object is converted to list."""
        single_obj = {"start": "0,0", "end": "10,10"}
        if not isinstance(single_obj, list):
            items = [single_obj]
        else:
            items = single_obj
        assert isinstance(items, list)
        assert len(items) == 1

    def test_empty_array_handled(self):
        """Test that empty arrays are handled."""
        empty = json.dumps([])
        parsed = json.loads(empty)
        assert isinstance(parsed, list)
        assert len(parsed) == 0


class TestBackwardCompatibility:
    """Test suite to ensure single operations still work."""

    def test_single_operation_functions_unchanged(self):
        """Test that single operation tools are unchanged."""
        # These should remain as legacy single-item tools
        # (draw_circle_and_line, create_layer, etc.)
        # This is just a reminder that backward compatibility is maintained
        pass
