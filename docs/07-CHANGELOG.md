# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.3] - 2026-02-12

### Changed - Mixin Architecture Refactor

Major refactoring of the adapter layer for better maintainability.

#### Architecture

- **Mixin-based adapter**: `autocad_adapter.py` reduced from 3,198 to 99 lines
- **11 specialized mixins**: Each mixin handles a specific responsibility
  - `UtilityMixin` (403 lines) - Helpers, converters
  - `ConnectionMixin` (176 lines) - COM connection
  - `DrawingMixin` (421 lines) - Draw operations
  - `LayerMixin` (430 lines) - Layer management
  - `FileMixin` (294 lines) - File operations
  - `ViewMixin` (121 lines) - View control
  - `SelectionMixin` (288 lines) - Entity selection
  - `EntityMixin` (73 lines) - Entity properties
  - `ManipulationMixin` (458 lines) - Move, rotate, scale
  - `BlockMixin` (514 lines) - Block operations
  - `ExportMixin` (800 lines) - Excel export

- **AdapterRegistry**: Encapsulated global state in singleton class
- **Removed NLP**: Natural language processor removed (use direct tool calls)

#### New Tools (54 total)

- `draw_splines` - Draw multiple splines
- `set_layer_color` - Set layer color
- `set_entities_color_bylayer` - Set color ByLayer
- `insert_block` - Insert block at point
- `insert_blocks_batch` - Insert multiple blocks
- `list_blocks` - List block definitions
- `get_block_info` - Get block properties
- `get_block_references` - Get block references

#### Bug Fixes

- Fixed `@staticmethod` error in `validate_lineweight`

### Improvements

- **Refactored `DrawingMixin`**: Reduces boilerplate code in drawing methods using `_finalize_entity` helper.
- **Simplified `draw_mleader`**: Extracted complex fallback logic to improve readability.
- **Documentation**: Simplified `README.md` and updated documentation structure.

---

## [0.1.2] - 2025-12-09

### Added

- **Block creation**: `create_block` tool (from handles or selection)
- Core methods: `create_block_from_entities()`, `create_block_from_selection()`
- 7 new tests (42 total)

### Changed

- Direct instantiation: `AutoCADAdapter(cad_type)` replaces factory
- Context managers: `com_session()`, `SelectionSetManager`
- Performance: `PickfirstSelectionSet` for fast entity access

---

## Unreleased

### Added

- Block management tools (insert, batch insert, list and audit blocks)

## [0.1.1] - 2025-11-22

### Added - Batch Operations

**13 batch operation tools** reducing API calls by 60-70%:

- Drawing: `draw_lines`, `draw_circles`, `draw_arcs`, `draw_rectangles`, `draw_polylines`, `draw_texts`, `add_dimensions`
- Layers: `rename_layers`, `delete_layers`, `turn_layers_on`, `turn_layers_off`
- Entities: `change_entities_colors`, `change_entities_layers`
- Export: `export_selected_to_excel`, `extract_selected_data`

---

## [0.1.0] - 2025-11-12

### Initial Release

- **Multi-CAD support**: AutoCAD, ZWCAD, GstarCAD, BricsCAD
- **FastMCP 2.0** server with MCP tools
- **Universal adapter** via COM API
- **Excel export** with locale support
- **Type safety**: 100% type hints
- **Testing**: Comprehensive test suite
