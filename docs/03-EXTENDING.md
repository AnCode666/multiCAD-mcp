# 03 - Extending multiCAD-mcp

Guide for adding new features, tools, or adapters.

## Adding a New Drawing Operation

### Example: Draw a Triangle

#### 1. Define in CADInterface

File: `src/core/cad_interface.py`

```python
@abstractmethod
def draw_triangle(self, points: List[Coordinate],
                  layer: str = "0",
                  color: str = "white",
                  lineweight: int = 0) -> str:
    """Draw a triangle from three points.

    Args:
        points: List of three (x, y) or (x, y, z) coordinates
        layer: Layer name
        color: Color name
        lineweight: Line weight

    Returns:
        Entity handle string
    """
    pass
```

#### 2. Implement in Adapter

File: `src/adapters/autocad_adapter.py`

```python
@com_safe(return_type=str, operation_name="draw_triangle")
def draw_triangle(self, points, layer="0", color="white", lineweight=0):
    """Draw a triangle as a closed polyline."""
    self._validate_connection()

    if len(points) != 3:
        raise InvalidParameterError("points", points, "exactly 3 points")

    # Normalize all coordinates
    normalized = [self.normalize_coordinate(p) for p in points]

    # Create polyline through points
    variant_points = self._points_to_variant_array(normalized)
    polyline = self.document.ModelSpace.AddPolyline(variant_points)
    polyline.Closed = True

    # Apply properties
    self._apply_properties(polyline, layer, color, lineweight)

    logger.info(f"Created triangle with 3 points on layer '{layer}'")
    self.refresh_view()

    return str(polyline.Handle)
```

#### 3. Add MCP Tool

File: `src/mcp_tools/tools/drawing.py`

```python
@cad_tool(mcp, "draw_triangle")
def draw_triangle(
    ctx: Context,
    points: str,
    color: str = "white",
    layer: str = "0",
    lineweight: int = 0,
    cad_type: Optional[str] = None,
) -> str:
    """
    Draw a triangle from three points.

    Args:
        points: Three points as "x1,y1|x2,y2|x3,y3"
        color: Triangle color
        layer: Layer to draw on
        lineweight: Line weight
        cad_type: CAD application to use

    Returns:
        Entity handle
    """
    point_list = [parse_coordinate(p.strip()) for p in points.split("|")]

    if len(point_list) != 3:
        raise InvalidParameterError("points", points, "exactly 3 points pipe-separated")

    return get_current_adapter().draw_triangle(
        point_list, layer, color, lineweight
    )
```

#### 4. Add NLP Support (Optional)

File: `src/nlp/processor.py`

```python
# In SHAPE_KEYWORDS dictionary:
"triangle": ["triangle", "tri"],

# In _extract_parameters method:
elif shape_type == "triangle":
    params["points"] = self._extract_multiple_points(text_lower)
```

#### 5. Test It

File: `tests/test_new_tools.py`

```python
def test_draw_triangle():
    """Test triangle drawing."""
    adapter = create_adapter("autocad")

    points = [(0, 0), (100, 0), (50, 100)]
    handle = adapter.draw_triangle(points, color="red")

    assert handle is not None
    assert isinstance(handle, str)

def test_nlp_draw_triangle():
    """Test triangle parsing."""
    processor = NLPProcessor()

    parsed = processor.parse_command("draw a triangle with points 0,0 100,0 50,100")

    assert parsed.operation == "draw_triangle"
    assert len(parsed.parameters["points"]) == 3
```

## Adding a New CAD Application

**Note**: multiCAD-mcp uses a **factory pattern** with a single universal adapter. All compatible CAD applications share the same COM API, so they use the same `AutoCADAdapter` class with different ProgIDs.

### Example: Support for a COM-Compatible CAD

If the new CAD uses the same COM API as AutoCAD:

#### 1. Update Configuration

File: `src/config.json`

```json
{
  "cad": {
    "newcad": {
      "type": "newcad",
      "prog_id": "NewCAD.Application",
      "startup_wait_time": 15.0,
      "command_delay": 0.5
    }
  }
}
```

#### 2. Update Factory Registry

File: `src/adapters/__init__.py`

```python
ADAPTER_REGISTRY = {
    "autocad": AutoCADAdapter,
    "zwcad": AutoCADAdapter,
    "gcad": AutoCADAdapter,
    "bricscad": AutoCADAdapter,
    "newcad": AutoCADAdapter,  # NEW - uses same adapter
}
```

#### 3. Test It

```python
from adapters import create_adapter

adapter = create_adapter("newcad")  # Returns AutoCADAdapter(cad_type="newcad")
adapter.connect()  # Uses "NewCAD.Application" ProgID from config
```

### Example: Support for Non-COM CAD (e.g., LibreCAD)

For CAD software with a different API:

#### 1. Create New Adapter

File: `src/adapters/librecad_adapter.py`

```python
from core import CADInterface

class LibreCADAdapter(CADInterface):
    """LibreCAD adapter using Python API."""

    def __init__(self):
        super().__init__(cad_type="librecad")
        self.document = None
        self.app = None

    def connect(self) -> bool:
        """Connect to LibreCAD."""
        try:
            import PyQt5.QtCore as QtCore
            # LibreCAD connection logic here
            logger.info("Connected to LibreCAD")
            return True
        except Exception as e:
            raise CADConnectionError("librecad", str(e))

    def draw_line(self, start, end, layer="0", color="white", lineweight=0):
        """Implement draw_line for LibreCAD."""
        # Implementation specific to LibreCAD API
        pass

    # Implement all abstract methods from CADInterface...
```

#### 2. Register in Factory

File: `src/adapters/__init__.py`

```python
from .librecad_adapter import LibreCADAdapter

ADAPTER_REGISTRY = {
    "autocad": AutoCADAdapter,
    "zwcad": AutoCADAdapter,
    "gcad": AutoCADAdapter,
    "bricscad": AutoCADAdapter,
    "librecad": LibreCADAdapter,  # NEW - different adapter class
}

def create_adapter(cad_type: str) -> CADInterface:
    """Create adapter instance for given CAD type."""
    adapter_class = ADAPTER_REGISTRY.get(cad_type.lower())
    if adapter_class is None:
        raise CADNotSupportedError(cad_type)
    return adapter_class()
```

#### 3. Update Configuration

File: `src/config.json`

```json
{
  "cad": {
    "librecad": {
      "type": "librecad",
      "prog_id": "librecad.Application",
      "startup_wait_time": 15.0,
      "command_delay": 0.5
    }
  }
}
```

## Adding a New Tool Category

### Example: Add Measurement Tools

#### 1. Create Module

File: `src/mcp_tools/tools/measurements.py`

```python
"""Measurement and query tools."""

def register_measurement_tools(mcp):
    """Register measurement tools with FastMCP."""

    @cad_tool(mcp, "measure_distance")
    def measure_distance(
        ctx: Context,
        point1: str,
        point2: str,
        cad_type: Optional[str] = None,
    ) -> str:
        """
        Measure distance between two points.

        Args:
            point1: First point as "x,y" or "x,y,z"
            point2: Second point as "x,y" or "x,y,z"
            cad_type: CAD application to use

        Returns:
            Distance value
        """
        pt1 = parse_coordinate(point1)
        pt2 = parse_coordinate(point2)
        return str(get_current_adapter().measure_distance(pt1, pt2))

    # ... more measurement tools ...
```

#### 2. Register in Server

File: `src/server.py`

```python
from mcp_tools.tools import (
    # ... existing imports ...
    register_measurement_tools,
)

def register_all_tools():
    """Register all MCP tools."""
    # ... existing registrations ...
    register_measurement_tools(mcp)
    logger.debug("  ✓ Measurement tools registered")
```

#### 3. Add to CADInterface

File: `src/core/cad_interface.py`

```python
@abstractmethod
def measure_distance(self, point1: Coordinate, point2: Coordinate) -> float:
    """Calculate distance between two points."""
    pass
```

## Modifying Existing Tools

### Pattern: Update Error Handling

Tools follow this pattern:

```python
@cad_tool(mcp, "operation_name")
def operation_name(ctx: Context, param1: str, cad_type: Optional[str] = None) -> str:
    """Tool documentation."""
    try:
        # Validate parameters
        if not param1:
            raise InvalidParameterError("param1", param1, "non-empty string")

        # Call adapter
        result = get_current_adapter().operation_name(param1)

        # Format result
        return result_message("operation name", True, result)
    except (InvalidParameterError, CADOperationError):
        raise  # Re-raise domain exceptions
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise CADOperationError("operation_name", str(e))
```

## Testing New Features

### Unit Test Template

```python
import pytest
from src.adapters import create_adapter
from src.core import InvalidParameterError

def test_new_feature():
    """Test new feature."""
    adapter = create_adapter("autocad")

    # Setup
    result = adapter.new_feature(test_param)

    # Assert
    assert result is not None
    assert isinstance(result, str)

def test_new_feature_validation():
    """Test parameter validation."""
    adapter = create_adapter("autocad")

    # Should raise InvalidParameterError
    with pytest.raises(InvalidParameterError):
        adapter.new_feature(invalid_param)
```

### Run Tests

```powershell
pytest tests/ -v
pytest tests/test_new_feature.py::test_new_feature -v
```

## Code Style Guidelines

1. **Type Hints**: Always use type hints

   ```python
   def draw_line(self, start: Coordinate, end: Coordinate) -> str:
   ```

2. **Docstrings**: Follow this format

   ```python
   def draw_line(self, start, end, layer="0", color="white"):
       """Draw a line between two points.

       Args:
           start: Start coordinate
           end: End coordinate
           layer: Layer name
           color: Color name

       Returns:
           Entity handle string
       """
   ```

3. **Logging**: Log significant operations

   ```python
   logger.info(f"Created line from {start} to {end}")
   logger.debug(f"Applied properties: layer={layer}, color={color}")
   ```

4. **Error Handling**: Use domain-specific exceptions

   ```python
   if not self.is_connected():
       raise CADConnectionError("autocad", "Not connected")
   ```

## Common Pitfalls

1. **Forgetting COM initialization**: Always call in `connect()`

   ```python
   pythoncom.CoInitialize()
   ```

2. **Not validating connection**: Every operation should validate

   ```python
   self._validate_connection()
   ```

3. **Hardcoding COM details**: Use configuration instead

   ```python
   prog_id = self.config.prog_id  # Good
   prog_id = "AutoCAD.Application"  # Bad
   ```

4. **Missing error handling**: Don't let exceptions bubble up

   ```python
   raise CADOperationError(operation, str(e))  # Good
   raise e  # Bad
   ```

## Next Steps

- See [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) for debugging
- Check [05-REFERENCE.md](05-REFERENCE.md) for complete API
- Review existing tools in `src/mcp_tools/tools/` for examples
