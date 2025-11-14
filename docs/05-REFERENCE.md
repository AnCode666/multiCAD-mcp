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

### draw_line

Draw a line between two points.

**Parameters**:

- `start` - Start point as "x,y" or "x,y,z"
- `end` - End point as "x,y" or "x,y,z"
- `color` (default: "white") - Line color
- `layer` (default: "0") - Layer name
- `lineweight` (default: 0) - Line weight
- `cad_type` (default: auto) - CAD to use

**Returns**: Entity handle

### draw_circle

Draw a circle.

**Parameters**:

- `center` - Center point as "x,y" or "x,y,z"
- `radius` - Circle radius (positive number)
- `color` (default: "white")
- `layer` (default: "0")
- `lineweight` (default: 0)
- `cad_type` (default: auto)

**Returns**: Entity handle

### draw_arc

Draw an arc.

**Parameters**:

- `center` - Center point as "x,y" or "x,y,z"
- `radius` - Arc radius (positive number)
- `start_angle` - Start angle in degrees
- `end_angle` - End angle in degrees
- `color` (default: "white")
- `layer` (default: "0")
- `lineweight` (default: 0)
- `cad_type` (default: auto)

**Returns**: Entity handle

### draw_rectangle

Draw a rectangle from two opposite corners.

**Parameters**:

- `corner1` - First corner as "x,y" or "x,y,z"
- `corner2` - Opposite corner as "x,y" or "x,y,z"
- `color` (default: "white")
- `layer` (default: "0")
- `lineweight` (default: 0)
- `cad_type` (default: auto)

**Returns**: Entity handle

### draw_polyline

Draw a polyline through multiple points.

**Parameters**:

- `points` - Points as "x1,y1|x2,y2|x3,y3|..." (pipe-separated)
- `closed` (default: false) - Whether to close the polyline
- `color` (default: "white")
- `layer` (default: "0")
- `lineweight` (default: 0)
- `cad_type` (default: auto)

**Returns**: Entity handle

**Example**:

```text
draw_polyline(points="0,0|100,0|100,100|0,100", closed=true)
```

### draw_text

Add text to the drawing.

**Parameters**:

- `position` - Text position as "x,y" or "x,y,z"
- `text` - Text content
- `height` (default: 2.5) - Text height
- `rotation` (default: 0.0) - Rotation angle in degrees
- `color` (default: "white")
- `layer` (default: "0")
- `cad_type` (default: auto)

**Returns**: Entity handle

### add_dimension

Add a dimension annotation.

**Parameters**:

- `start` - Start point as "x,y" or "x,y,z"
- `end` - End point as "x,y" or "x,y,z"
- `color` (default: "white")
- `layer` (default: "0")
- `text` (optional) - Custom dimension text
- `offset` (default: 10.0) - Distance from edge to dimension line
- `cad_type` (default: auto)

**Returns**: Entity handle

### draw_circle_and_line

Draw a circle and a line in a single operation.

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

### rename_layer

Rename an existing layer.

**Parameters**:

- `old_name` - Current layer name
- `new_name` - New layer name
- `cad_type` (default: auto)

**Returns**: Status message

### delete_layer

Delete a layer from the drawing.

**Parameters**:

- `name` - Layer name to delete
- `cad_type` (default: auto)

**Returns**: Status message

**Note**: Cannot delete default layer "0"

### turn_layer_on

Turn on (make visible) a layer.

**Parameters**:

- `name` - Layer name
- `cad_type` (default: auto)

**Returns**: Status message

### turn_layer_off

Turn off (hide) a layer.

**Parameters**:

- `name` - Layer name
- `cad_type` (default: auto)

**Returns**: Status message

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

## Entity Tools (10 tools)

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

Change color of entities.

**Parameters**:

- `handles` - Comma-separated entity handles
- `color` - New color name
- `cad_type` (default: auto)

**Returns**: Status message

### change_entity_layer

Move entities to a different layer.

**Parameters**:

- `handles` - Comma-separated entity handles
- `layer_name` - Target layer name
- `cad_type` (default: auto)

**Returns**: Status message

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

Total: **40+ MCP tools**

- 4 Connection tools
- 8 Drawing tools
- 7 Layer tools
- 5 File tools
- 10 Entity tools
- 3 Simple tools
- 1 NLP tool
- 2 Export tools
- 2 Debug tools
