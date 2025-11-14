# Changelog

All notable changes to multiCAD-mcp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
