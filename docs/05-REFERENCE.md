# 05 - Tool Reference

## Summary

**54 MCP tools** organized in 9 categories:

| Category | Tools | Batch |
|----------|-------|-------|
| Connection | 4 | - |
| Drawing | 10 | 8 |
| Blocks | 5 | 1 |
| Layers | 8 | 4 |
| Files | 5 | - |
| Entities | 13 | 3 |
| Simple | 3 | - |
| Export | 4 | - |
| Debug | 2 | - |

---

## Connection Tools (4)

| Tool | Description |
|------|-------------|
| `connect_cad` | Connect to CAD (cad_type: autocad, zwcad, gcad, bricscad) |
| `disconnect_cad` | Disconnect from CAD |
| `list_supported_cads` | List supported CAD types |
| `get_connection_status` | Get connection status |

---

## Drawing Tools (10)

### Batch Operations

| Tool | Description |
|------|-------------|
| `draw_lines` | Draw multiple lines `[{"start":"0,0","end":"10,10","color":"red"}]` |
| `draw_circles` | Draw multiple circles `[{"center":"0,0","radius":5}]` |
| `draw_arcs` | Draw multiple arcs |
| `draw_rectangles` | Draw multiple rectangles |
| `draw_polylines` | Draw multiple polylines |
| `draw_texts` | Draw multiple text labels |
| `draw_splines` | Draw multiple splines |
| `add_dimensions` | Add multiple dimensions |

### Single Operations

| Tool | Description |
|------|-------------|
| `draw_circle_and_line` | Helper: draw circle and line |
| `create_block` | Create block from handles or selection |

---

## Block Tools (5)

| Tool | Description |
|------|-------------|
| `create_block` | Create block from entities |
| `insert_block` | Insert block at point |
| `insert_blocks_batch` | Insert multiple blocks |
| `list_blocks` | List all block definitions |
| `get_block_info` | Get block properties |
| `get_block_references` | Get block reference instances |

---

## Layer Tools (8)

### Batch Operations

| Tool | Description |
|------|-------------|
| `rename_layers` | Rename multiple layers |
| `delete_layers` | Delete multiple layers |
| `turn_layers_on` | Show multiple layers |
| `turn_layers_off` | Hide multiple layers |

### Single Operations

| Tool | Description |
|------|-------------|
| `create_layer` | Create new layer |
| `list_layers` | List all layers |
| `is_layer_on` | Check layer visibility |
| `set_layer_color` | Set layer color |

---

## File Tools (5)

| Tool | Description |
|------|-------------|
| `save_drawing` | Save to DWG, DXF, or PDF |
| `new_drawing` | Create blank drawing |
| `close_drawing` | Close active drawing |
| `get_open_drawings` | List open files |
| `switch_drawing` | Switch between drawings |

---

## Entity Tools (13)

### Selection

| Tool | Description |
|------|-------------|
| `select_by_color` | Select entities by color |
| `select_by_layer` | Select entities by layer |
| `select_by_type` | Select entities by type (line, circle, etc.) |

### Manipulation

| Tool | Description |
|------|-------------|
| `move_entities` | Move entities by offset |
| `rotate_entities` | Rotate around point |
| `scale_entities` | Scale from point |
| `copy_entities` | Copy to clipboard |
| `paste_entities` | Paste at point |

### Property Changes

| Tool | Description |
|------|-------------|
| `change_entity_color` | Change color (single) |
| `change_entities_colors` | Change colors (batch) |
| `change_entity_layer` | Change layer (single) |
| `change_entities_layers` | Change layers (batch) |
| `set_entities_color_bylayer` | Set color ByLayer |

---

## Simple Tools (3)

| Tool | Description |
|------|-------------|
| `zoom_extents` | Fit view to all entities |
| `undo` | Undo operations (count param) |
| `redo` | Redo operations (count param) |

---

## Export Tools (4)

| Tool | Description |
|------|-------------|
| `export_drawing_to_excel` | Export all entities to Excel |
| `extract_drawing_data` | Get all entity data as JSON |
| `export_selected_to_excel` | Export selected entities to Excel |
| `extract_selected_data` | Get selected entity data as JSON |

---

## Debug Tools (2)

| Tool | Description |
|------|-------------|
| `debug_entities` | List all entities with properties |
| `test_select_by_layer` | Test layer selection |

---

## Common Parameters

### Coordinates
```
"0,0"        # 2D
"0,0,0"      # 3D
"100.5,-20"  # Floats, negatives OK
```

### Colors
`red`, `blue`, `green`, `yellow`, `cyan`, `magenta`, `white`, `black`, `gray`, `orange`

### CAD Types
`autocad`, `zwcad`, `gcad`, `bricscad`

### Entity Types
`line`, `circle`, `arc`, `polyline`, `text`, `point`
