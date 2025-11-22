# Changelog

All notable changes to multiCAD-mcp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-11-22

### Added - Batch Operations Optimization

Implemented batch operation tools to reduce API calls and improve efficiency for the Claude AI assistant when making multiple drawings or managing layers.

#### New Tools

**Drawing Tools** (7 new batch operations):

- `draw_lines` - Draw multiple lines in one API call
- `draw_circles` - Draw multiple circles in one API call
- `draw_arcs` - Draw multiple arcs in one API call
- `draw_rectangles` - Draw multiple rectangles in one API call
- `draw_polylines` - Draw multiple polylines in one API call
- `draw_texts` - Add multiple text labels in one API call
- `add_dimensions` - Add multiple dimensions in one API call

**Layer Tools** (4 new batch operations):

- `rename_layers` - Rename multiple layers in one API call
- `delete_layers` - Delete multiple layers in one API call
- `turn_layers_on` - Show multiple layers in one API call
- `turn_layers_off` - Hide multiple layers in one API call

**Entity Tools** (2 new batch operations):

- `change_entities_colors` - Change color of multiple entity groups with individual colors
- `change_entities_layers` - Move multiple entity groups to different layers

#### Improvements

- **JSON-based Input Format**: All batch operations accept JSON arrays for clean, structured data
- **Standardized Response Format**: Consistent JSON responses with:
  - `total` - Number of items processed
  - `created`/`renamed`/`changed`/`deleted` - Count of successful operations
  - `results` - Detailed per-item status including errors
- **Per-item Error Reporting**: Each item in a batch has individual success/failure tracking
- **Default Values**: Optional parameters use sensible defaults (color="white", layer="0")
- **Backward Compatibility**: All original single-operation tools remain unchanged

#### Performance Impact

- **60-70% reduction** in API calls for typical drawing workflows
- **Example**: Drawing 10 lines reduced from 10 calls to 1 call
- **Estimated token savings**: 50-70% reduction in AI tool invocations for complex drawings

#### Documentation

- Updated `05-REFERENCE.md` with all new batch operation details
- Added JSON structure examples for each batch operation
- Added test suite `test_batch_operations.py` with 20+ test cases
- Updated tool summary: 47 tools total (13 new batch operations)

#### Technical Details

**Data Structure**: Uses Python `TypedDict` for type safety

```python
class LineSpec(TypedDict, total=False):
    start: str
    end: str
    color: str
    layer: str
    lineweight: int
```

**Input Format**: JSON string containing array of specifications
**Output Format**: Structured JSON with operation status and error details

---

## [0.1.0] - 2025-11-12

### Initial Release

multiCAD-mcp is a MCP (Model Context Protocol) server that enables natural language control of multiple CAD applications through Claude AI and other LLM clients.

#### Core Features

- **Multi-CAD Support**: AutoCAD®, ZWCAD®, GstarCAD®, BricsCAD®
  - Single universal adapter with factory pattern
  - ProgID-based CAD selection
  - Windows COM API integration

- **40+ MCP Tools** organized in 9 categories:
  - Connection management
  - Drawing operations (lines, circles, arcs, rectangles, ellipses, polylines, text, hatches, dimensions)
  - Layer management
  - File operations
  - Entity manipulation (select by color/layer/type, move, rotate, scale, copy, paste, change properties)
  - Simple view and history tools
  - Natural language command execution
  - Export tools (Excel integration)
  - Debug and diagnostic tools

- **Natural Language Processing**:
  - Parse commands like "draw a red circle at 50,50 with radius 25"
  - Multi-language support (English, Spanish)
  - Confidence scoring for parse quality
  - Coordinate and dimension extraction

- **Export Capabilities**:
  - Export drawing data to Excel with proper formatting
  - Regional decimal separator support (works in any locale)
  - Extract drawing data programmatically
  - Security: Files saved only to configured output directory

#### Architecture

- **FastMCP 2.0** framework for MCP server implementation
- **Factory Pattern**: Single `AutoCADAdapter` serving all CAD types
- **Singleton Pattern**: Centralized configuration management
- **Abstract Base Classes**: CADInterface defines contract for all adapters
- **Type Safety**: 100% type hints throughout codebase
- **Error Handling**: 9 domain-specific exception types

#### Documentation

- Comprehensive documentation in `docs/` folder (8 files)
- `README.md` - Documentation index
- `01-SETUP.md` - Development environment setup
- `02-ARCHITECTURE.md` - System design and architecture
- `03-EXTENDING.md` - Guide to adding new features
- `04-TROUBLESHOOTING.md` - Debugging and troubleshooting
- `05-REFERENCE.md` - Complete API reference (40+ tools)
- `06-GIT_SETUP.md` - Git workflow and contribution guide
- `07-CHANGELOG.md` - This file

#### Testing

- Comprehensive test suite with 45+ test cases
- Unit tests for NLP processor
- Integration tests for adapters
- All tests pass independently (no CAD required)

#### Configuration

- Flexible configuration via `config.json` with fallback defaults
- Configurable CAD startup times
- NLP language and mode settings
- Output directory configuration
- Logging level control (INFO, DEBUG, WARNING, ERROR)

#### Technical Stack

- **Python 3.10+**
- **FastMCP 2.0** - MCP server framework
- **pywin32** - Windows COM API
- **pytest** - Testing framework
- **openpyxl** - Excel export

---

## [Planned for Future Releases]

### - Entity Manipulation Enhancements

- Mirror entities (horizontal/vertical reflection)
- Advanced paste operations with insertion point control
- Batch entity property changes
- Entity grouping and block creation

### - Advanced NLP

- Machine learning-based NLP
- Better coordinate parsing (natural language like "from top-left to bottom-right")
- Multi-step command execution
- Additional language support

### - Drawing Analysis

- Extract drawing properties and metadata
- Measure distances and angles
- Query entity properties
- Generate drawing statistics

### - Managing

- Multi-user support with PostgreSQL backend
- Additional CAD application support (LibreCAD, NanoCAD, DraftSight)
- REST API wrapper for HTTP clients
- Web UI for visual drawing preview

---

## How to Contribute

When contributing, please:

1. Follow the existing code style (black, flake8, mypy)
2. Write tests for new functionality
3. Update documentation as needed
4. Follow conventional commit messages
5. Reference issues when applicable

---

**Current Status**: First stable version
**Maintenance**: Active Development
**Last Updated**: 2025-11-12
