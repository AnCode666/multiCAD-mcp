# 03 - Extending multiCAD-mcp

## Adding a New Drawing Operation

### Example: Draw a Triangle

#### 1. Define in CADInterface

File: `src/core/cad_interface.py`

```python
@abstractmethod
def draw_triangle(self, points: List[Coordinate], layer: str = "0",
                  color: str = "white", lineweight: int = 0) -> str:
    """Draw a triangle from three points."""
    pass
```

#### 2. Implement in Mixin

File: `src/adapters/mixins/drawing_mixin.py`

```python
def draw_triangle(self, points, layer="0", color="white", lineweight=0):
    """Draw a triangle as a closed polyline."""
    self._validate_connection()

    if len(points) != 3:
        raise InvalidParameterError("points", points, "exactly 3 points")

    normalized = [self.normalize_coordinate(p) for p in points]
    variant_points = self._points_to_variant_array(normalized)
    polyline = self.document.ModelSpace.AddPolyline(variant_points)
    polyline.Closed = True

    self._apply_properties(polyline, layer, color, lineweight)
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
    cad_type: Optional[str] = None,
) -> str:
    """Draw a triangle from three points (pipe-separated: x1,y1|x2,y2|x3,y3)."""
    point_list = [parse_coordinate(p.strip()) for p in points.split("|")]
    return get_current_adapter().draw_triangle(point_list, layer, color)
```

#### 4. Add Test

File: `tests/test_drawing.py`

```python
def test_draw_triangle():
    adapter = AutoCADAdapter("autocad")
    points = [(0, 0), (100, 0), (50, 100)]
    # Test with mock...
```

## Adding a New CAD Application

### COM-Compatible CAD (same API as AutoCAD)

Just add to `src/config.json`:

```json
{
  "cad": {
    "newcad": {
      "type": "newcad",
      "prog_id": "NewCAD.Application",
      "startup_wait_time": 15.0
    }
  }
}
```

The universal adapter handles it automatically.

### Non-COM CAD (different API)

1. Create new adapter in `src/adapters/`
2. Implement all CADInterface methods
3. Register in adapter factory

## Adding a New Tool Category

### Example: Measurement Tools

#### 1. Create Module

File: `src/mcp_tools/tools/measurements.py`

```python
"""Measurement tools."""
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate

def register_measurement_tools(mcp):
    @cad_tool(mcp, "measure_distance")
    def measure_distance(ctx, point1: str, point2: str, cad_type=None) -> str:
        """Measure distance between two points."""
        pt1 = parse_coordinate(point1)
        pt2 = parse_coordinate(point2)
        return str(get_current_adapter().measure_distance(pt1, pt2))
```

#### 2. Register in Server

File: `src/server.py`

```python
from mcp_tools.tools import register_measurement_tools
register_measurement_tools(mcp)
```

## Code Style

1. **Type hints**: Always use them
2. **Docstrings**: Document all functions
3. **Logging**: Log important operations
4. **Error handling**: Use domain-specific exceptions

```python
from core.exceptions import CADOperationError, InvalidParameterError

if not self.is_connected():
    raise CADConnectionError("autocad", "Not connected")
```

## Common Pitfalls

1. **Missing COM init**: Always call `pythoncom.CoInitialize()` in `connect()`
2. **No connection validation**: Every operation should call `_validate_connection()`
3. **Hardcoded ProgID**: Use `self.config.prog_id` from configuration
4. **Bubbling exceptions**: Wrap in `CADOperationError`
