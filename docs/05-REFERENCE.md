# 05 - Reference

Complete documentation of all MCP tools.

## Connection Tools (4 tools)

### connect_cad

Connect to a CAD application.

**Parameters**:

- `cad_type` (default: "autocad") - One of: autocad, zwcad, gcad, bricscad

**Returns**: Status message

**Example**:

```text
connect_cad(cad_type="autocad")
→ "Successfully connected to autocad"
```

### disconnect_cad

Disconnect from a CAD application.

**Parameters**:

- `cad_type` (default: "autocad") - CAD to disconnect from

**Returns**: Status message

### list_supported_cads

List all supported CAD applications.

**Returns**: Comma-separated list of CAD types

**Example**:

```text
→ "Supported CAD types: autocad, zwcad, gcad, bricscad"
```

### get_connection_status

Get connection status for all CAD types.

**Returns**: Dictionary with status for each CAD type

**Example**:

```text
→ {'autocad': 'connected', 'zwcad': 'not initialized', ...}
```

## Drawing Tools (8 tools)

Batch operations optimized for drawing multiple entities in a single API call.

### draw_lines

Draw multiple lines in a single operation.

**Parameters**:

- `lines` - JSON array of line specifications

  ```json
  [
    {"start": "0,0", "end": "10,10", "color": "white", "layer": "0", "lineweight": 0}
  ]
  ```

- `cad_type` (default: auto) - CAD to use

**Returns**: JSON with created handles and status

**Example**:

```json
{
  "total": 2,
  "created": 2,
  "results": [
    {"index": 0, "handle": "ABC123", "success": true},
    {"index": 1, "handle": "ABC124", "success": true}
  ]
}
```

### draw_circles

Draw multiple circles in a single operation.

**Parameters**:

- `circles` - JSON array of circle specifications

  ```json
  [
    {"center": "0,0", "radius": 5.0, "color": "blue", "layer": "0"}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with created handles and status

### draw_arcs

Draw multiple arcs in a single operation.

**Parameters**:

- `arcs` - JSON array of arc specifications

  ```json
  [
    {"center": "0,0", "radius": 5.0, "start_angle": 0, "end_angle": 90}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with created handles and status

### draw_rectangles

Draw multiple rectangles in a single operation.

**Parameters**:

- `rectangles` - JSON array of rectangle specifications

  ```json

  [
    {"corner1": "0,0", "corner2": "10,10", "color": "yellow"}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with created handles and status

### draw_polylines

Draw multiple polylines in a single operation.

**Parameters**:

- `polylines` - JSON array of polyline specifications

  ```json
  [
    {"points": "0,0|10,10|20,0", "closed": true, "color": "cyan"}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with created handles and status

**Example**:

```text
draw_polylines(polylines='[{"points":"0,0|100,0|100,100|0,100","closed":true}]')
```

### draw_texts

Add multiple text labels in a single operation.

**Parameters**:

- `texts` - JSON array of text specifications

  ```json
  [
    {"position": "0,0", "text": "Label 1", "height": 2.5, "color": "red"}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with created handles and status

### add_dimensions

Add multiple dimension annotations in a single operation.

**Parameters**:

- `dimensions` - JSON array of dimension specifications

  ```json
  [
    {"start": "0,0", "end": "10,10", "color": "white", "offset": 10.0}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with created handles and status

### draw_circle_and_line

Draw a circle and a line in a single operation (helper).

**Parameters**:

- `line_start` - Line start as "x,y"
- `line_end` - Line end as "x,y"
- `circle_center` - Circle center as "x,y"
- `circle_radius` - Circle radius
- `color` (default: "white")
- `layer` (default: "0")
- `cad_type` (default: auto)

**Returns**: Message with both entity handles

## Layer Tools (7 tools)

Batch operations for managing multiple layers efficiently.

### create_layer

Create a new layer.

**Parameters**:

- `name` - Layer name
- `color` (default: "white") - Layer color
- `lineweight` (default: 0) - Layer line weight
- `cad_type` (default: auto)

**Returns**: Status message

### list_layers

List all layers in the current drawing.

**Parameters**:

- `cad_type` (default: auto)

**Returns**: Comma-separated list of layer names

**Example**:

```text
→ "Layers: 0, Dimensions, Construction, Hidden"
```

### rename_layers

Rename multiple layers in a single operation.

**Parameters**:

- `renames` - JSON array of rename specifications

  ```json
  [
    {"old_name": "Layer1", "new_name": "NewName1"},
    {"old_name": "Layer2", "new_name": "NewName2"}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with operation status

### delete_layers

Delete multiple layers in a single operation.

**Parameters**:

- `layer_names` - JSON array of layer names to delete

  ```json
  ["Layer1", "Layer2", "Layer3"]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with operation status

**Note**: Cannot delete default layer "0"

### turn_layers_on

Turn on (make visible) multiple layers in a single operation.

**Parameters**:

- `layer_names` - JSON array of layer names

  ```json
  ["Layer1", "Layer2", "Layer3"]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with operation status

### turn_layers_off

Turn off (hide) multiple layers in a single operation.

**Parameters**:

- `layer_names` - JSON array of layer names

  ```json
  ["Layer1", "Layer2", "Layer3"]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with operation status

### is_layer_on

Check if a layer is visible.

**Parameters**:

- `name` - Layer name
- `cad_type` (default: auto)

**Returns**: "Layer 'X' is on (visible)" or "Layer 'X' is off (hidden)"

## File Tools (5 tools)

### save_drawing

Save the current drawing to a file.

**Parameters**:

- `filepath` (optional) - Full file path (overrides other params)
- `filename` (optional) - Just the filename (saved to output directory)
- `format` (default: "dwg") - File format (dwg, dxf, pdf)
- `cad_type` (default: auto)

**Returns**: Status message with file path

**Examples**:

```text
# Save with full path
save_drawing(filepath="C:\\drawings\\myfile.dwg")

# Save with filename only (uses output directory)
save_drawing(filename="myfile.dwg")
```

### new_drawing

Create a new blank drawing.

**Parameters**:

- `cad_type` (default: auto)

**Returns**: Status message

### close_drawing

Close the current drawing.

**Parameters**:

- `save_changes` (default: false) - Whether to save before closing
- `cad_type` (default: auto)

**Returns**: Status message

**Note**: If other drawings are open, switches to the first one

### get_open_drawings

Get list of all open drawings.

**Parameters**:

- `cad_type` (default: auto)

**Returns**: Comma-separated list of open drawing names

### switch_drawing

Switch to a different open drawing.

**Parameters**:

- `drawing_name` - Name of the drawing to switch to
- `cad_type` (default: auto)

**Returns**: Status message or list of available drawings

## Entity Tools (12 tools)

Selection and manipulation tools for entities, with batch operations for color and layer changes.

### select_by_color

Select all entities of a specific color.

**Parameters**:

- `color` - Color name (red, blue, green, etc.)
- `cad_type` (default: auto)

**Returns**: Count and handles of selected entities

### select_by_layer

Select all entities on a specific layer.

**Parameters**:

- `layer_name` - Name of layer
- `cad_type` (default: auto)

**Returns**: Count and handles of selected entities

### select_by_type

Select all entities of a specific type.

**Parameters**:

- `entity_type` - Type (line, circle, arc, polyline, text, point)
- `cad_type` (default: auto)

**Returns**: Count and handles of selected entities

### move_entities

Move entities by an offset.

**Parameters**:

- `handles` - Comma-separated entity handles
- `offset_x` - X offset distance
- `offset_y` - Y offset distance
- `cad_type` (default: auto)

**Returns**: Status message

**Example**:

```text
move_entities(handles="h1,h2,h3", offset_x=10, offset_y=20)
```

### rotate_entities

Rotate entities around a point.

**Parameters**:

- `handles` - Comma-separated entity handles
- `center_x` - X coordinate of rotation center
- `center_y` - Y coordinate of rotation center
- `angle` - Rotation angle in degrees
- `cad_type` (default: auto)

**Returns**: Status message

### scale_entities

Scale entities around a point.

**Parameters**:

- `handles` - Comma-separated entity handles
- `center_x` - X coordinate of scale center
- `center_y` - Y coordinate of scale center
- `scale_factor` - Scale factor (1.0 = no change, 2.0 = double)
- `cad_type` (default: auto)

**Returns**: Status message

### copy_entities

Copy entities to clipboard.

**Parameters**:

- `handles` - Comma-separated entity handles
- `cad_type` (default: auto)

**Returns**: Status message

### paste_entities

Paste entities from clipboard at a base point.

**Parameters**:

- `base_point_x` - X coordinate of base point
- `base_point_y` - Y coordinate of base point
- `cad_type` (default: auto)

**Returns**: Status message

### change_entity_color

Change color of entities (all to same color).

**Parameters**:

- `handles` - Comma-separated entity handles
- `color` - New color name
- `cad_type` (default: auto)

**Returns**: Status message

### change_entities_colors

Change color of multiple entity groups with individual colors.

**Parameters**:

- `color_changes` - JSON array of color change specifications

  ```json
  [
    {"handles": "h1,h2,h3", "color": "red"},
    {"handles": "h4,h5", "color": "blue"}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with operation status

**Example**:

```json
{
  "total_changes": 2,
  "total_changed": 5,
  "results": [
    {"index": 0, "handles": "h1,h2,h3", "color": "red", "count": 3, "success": true},
    {"index": 1, "handles": "h4,h5", "color": "blue", "count": 2, "success": true}
  ]
}
```

### change_entity_layer

Move entities to a different layer (all to same layer).

**Parameters**:

- `handles` - Comma-separated entity handles
- `layer_name` - Target layer name
- `cad_type` (default: auto)

**Returns**: Status message

### change_entities_layers

Move multiple entity groups to different layers.

**Parameters**:

- `layer_changes` - JSON array of layer change specifications

  ```json
  [
    {"handles": "h1,h2,h3", "layer_name": "Layer1"},
    {"handles": "h4,h5", "layer_name": "Layer2"}
  ]
  ```

- `cad_type` (default: auto)

**Returns**: JSON with operation status

## Simple Tools (3 tools)

### zoom_extents

Zoom to show all entities in the view.

**Parameters**:

- `cad_type` (default: auto)

**Returns**: Status message

### undo

Undo last action(s).

**Parameters**:

- `count` (default: 1) - Number of operations to undo
- `cad_type` (default: auto)

**Returns**: Status message

**Example**:

```text
undo(count=5)  # Undo last 5 operations
```

### redo

Redo last undone action(s).

**Parameters**:

- `count` (default: 1) - Number of operations to redo
- `cad_type` (default: auto)

**Returns**: Status message

## Natural Language Tool (1 tool)

### execute_natural_command

Execute a CAD command from natural language description.

**Parameters**:

- `command` - Natural language description
- `cad_type` (default: auto)

**Returns**: Result of executed command

**Examples**:

```text
execute_natural_command("draw a red line from 0,0 to 100,100")
execute_natural_command("create a blue circle at 50,50 with radius 25")
execute_natural_command("add text 'Hello' at 10,10 with height 5")
```

## Export Tools (2 tools)

### export_drawing_to_excel

Export all drawing data to an Excel file.

**Parameters**:

- `filename` (default: "drawing_data.xlsx") - Excel filename or path
- `cad_type` (default: auto)

**Returns**: Status message with file location

**Features**:

- Extracts all entities with properties (Handle, Type, Layer, Color, Length, Area, Name)
- Files saved to configured output directory for security
- Supports subdirectories within output directory

**Examples**:

```text
export_drawing_to_excel(filename="data.xlsx")
→ Saved to output/data.xlsx

export_drawing_to_excel(filename="exports/project1.xlsx")
→ Saved to output/exports/project1.xlsx
```

### extract_drawing_data

Extract all drawing data without saving to file.

**Parameters**:

- `cad_type` (default: auto)

**Returns**: JSON with extracted entity data

**Use**: Get drawing data programmatically for processing

**Data Fields**:

- Handle - Entity identifier
- ObjectType - Entity type (LINE, CIRCLE, etc.)
- Layer - Layer name
- Color - Color index or name
- Length - Length for linear objects
- Area - Area for closed objects
- Name - Name for blocks

## Debug Tools (2 tools)

### debug_entities

List all entities in the drawing with their properties.

**Parameters**:

- `cad_type` (default: auto)

**Returns**: Detailed information about all entities

**Use**: Debugging - see what's in your drawing

### test_select_by_layer

Test entity selection by layer with detailed output.

**Parameters**:

- `layer_name` - Layer to test selection for
- `cad_type` (default: auto)

**Returns**: Detailed debug information about matching entities

**Use**: Debugging - verify selection logic

## Color Names

Supported colors:

- `black` - Black (0)
- `red` - Red (1)
- `yellow` - Yellow (2)
- `green` - Green (3)
- `cyan` - Cyan (4)
- `blue` - Blue (5)
- `magenta` - Magenta (6)
- `white` - White (7)
- `gray` - Gray (8)
- `light_gray` - Light Gray (252)
- `dark_gray` - Dark Gray (251)
- `orange` - Orange (30)

## Entity Types

For `select_by_type`:

- `line` - Line entities
- `circle` - Circle entities
- `arc` - Arc entities
- `polyline` - Polyline entities
- `text` - Text entities
- `point` - Point entities

## CAD Types

For any `cad_type` parameter:

- `autocad` - AutoCAD
- `zwcad` - ZWCAD
- `gcad` - GstarCAD
- `bricscad` - BricsCAD

If omitted, uses currently active CAD.

## Coordinate Formats

All coordinate parameters accept:

**2D Format**:

```text
"0,0"          # (x, y)
"100.5,50.25"  # Floating point OK
"-10,-20"      # Negative OK
```

**3D Format**:

```text
"0,0,0"        # (x, y, z)
"100,200,50"
```

## Summary

Total: **47 MCP tools** (optimized with batch operations)

- 4 Connection tools
- 8 Drawing tools (7 batch + 1 helper)
- 7 Layer tools (4 batch + 3 single)
- 5 File tools
- 12 Entity tools (2 batch color/layer + 10 standard)
- 3 Simple tools
- 1 NLP tool
- 2 Export tools
- 2 Debug tools

### Batch Operations Optimization

**47% of tools are now batch-optimized**:

- Drawing: 7/8 tools support batch operations
- Layers: 4/7 tools support batch operations
- Entities: 2/12 tools support batch operations (color, layer)

**Benefits**:

- 60-70% reduction in API calls for typical workflows
- Single JSON array input for multiple operations
- Detailed per-item error reporting
- Standardized JSON response format
