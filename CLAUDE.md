# CLAUDE.md

AI assistant guidance for working with the multiCAD-mcp codebase.

## Project Overview

**multiCAD-mcp** - MCP server for controlling CAD applications (AutoCAD, ZWCAD, GstarCAD, BricsCAD) via Windows COM.

**Stack**: Python 3.10+ | FastMCP 2.0 | pywin32 | Windows-only

**Version**: 0.1.3 (in `src/__version__.py`)

---

## Quick Commands

```powershell
# Setup
pip install -r requirements.txt
py -m pip install --upgrade pywin32

# Run
py src/server.py

# Test
pytest tests/ -v                      # 62 tests
npx -y @modelcontextprotocol/inspector py src/server.py

# Quality
black src/ && mypy src/
```

---

## Architecture

**Three Layers**:
1. **FastMCP Server** (`src/server.py`) - 7 unified MCP tools
2. **Core** (`src/core/`) - Interfaces, config, exceptions
3. **Adapters** (`src/adapters/`) - Mixin-based universal adapter

**Mixin Architecture** (v0.1.3+):

```
adapters/
├── autocad_adapter.py      # 99 lines - composite class
├── adapter_manager.py      # AdapterRegistry singleton
└── mixins/                 # 11 specialized mixins
    ├── utility_mixin.py    # Helpers, converters (403 lines)
    ├── connection_mixin.py # COM connection (176 lines)
    ├── drawing_mixin.py    # draw_line, draw_circle (421 lines)
    ├── layer_mixin.py      # Layer management (430 lines)
    ├── file_mixin.py       # File operations (294 lines)
    ├── view_mixin.py       # Zoom, undo/redo (121 lines)
    ├── selection_mixin.py  # Entity selection (288 lines)
    ├── entity_mixin.py     # Entity properties (73 lines)
    ├── manipulation_mixin.py # Move, rotate, scale (458 lines)
    ├── block_mixin.py      # Block operations (514 lines)
    └── export_mixin.py     # Excel export (800 lines)
```

**Usage**:
```python
from adapters import AutoCADAdapter
adapter = AutoCADAdapter("autocad")  # or "zwcad", "gcad", "bricscad"
```

---

## File Structure

```
multiCAD-mcp/
├── src/
│   ├── server.py              # Entry point
│   ├── __version__.py         # Version: 0.1.3
│   ├── config.json            # Configuration
│   ├── core/                  # Interfaces, config, exceptions
│   ├── adapters/              # Mixin-based adapter + manager
│   │   ├── autocad_adapter.py
│   │   ├── adapter_manager.py # AdapterRegistry
│   │   └── mixins/            # 11 mixin files
│   └── mcp_tools/
│       ├── helpers.py, decorators.py, constants.py
│       └── tools/             # 7 tool modules
├── tests/                     # 62 pytest tests
├── docs/                      # Documentation
└── requirements.txt
```

---

## Critical Notes

### 1. Imports (Absolute Only)

```python
# ✓ CORRECT
from core import CADInterface
from adapters import AutoCADAdapter

# ✗ WRONG (relative imports)
from ..core import CADInterface
```

### 2. Version

Single source: `src/__version__.py` → Edit only this file to bump version.

### 3. AutoCAD Color Index

```python
COLOR_MAP = {"red": 1, "blue": 5, "white": 7, ...}  # Do NOT modify
```

### 4. Coordinates

- Input: 2D `(x, y)` or 3D `(x, y, z)`
- Internal: Always 3D via `normalize_coordinate()`
- COM: VARIANT arrays via `_to_variant_array()`

### 5. Excel Localization

```python
cell.value = round(length, 3)    # Float, not string
cell.number_format = '0.000'     # Regional separator
```

---

## Configuration

`src/config.json`:
```json
{
  "logging_level": "INFO",
  "cad": {
    "autocad": {
      "prog_id": "AutoCAD.Application",
      "startup_wait_time": 20.0
    }
  },
  "output": {"directory": "~/Documents/multiCAD Exports"}
}
```

---

## Common Tasks

### Add New Operation

1. Define abstract method in `src/core/cad_interface.py`
2. Implement in appropriate mixin (`src/adapters/mixins/*.py`)
3. Register tool in `src/mcp_tools/tools/*.py`
4. Add test in `tests/`

### Add New CAD Type

Just add to `src/config.json`:
```json
"newcad": {"prog_id": "NewCAD.Application", "startup_wait_time": 15.0}
```
The universal adapter handles it automatically.

---

---

## Error Handling

```python
from core.exceptions import (
    CADConnectionError,    # Connection failed
    CADOperationError,     # Operation failed
    InvalidParameterError, # Bad parameter
    CoordinateError,       # Bad coordinate
    ColorError,            # Bad color
    LayerError,            # Layer failed
)
```

---

## Design Patterns

- **Mixin Composition**: `AutoCADAdapter` inherits from 11 mixins
- **Singleton**: `AdapterRegistry`, `ConfigManager`
- **Context Managers**: `com_session()`, `SelectionSetManager`
- **Decorator**: `@cad_tool` for tool registration

---

## Workflow

### Before Committing
1. `pytest tests/ -v` - All 62 tests must pass
2. `black src/` - Format
3. `mypy src/` - Type check (must be clean)

### Commit Policy
⚠️ **Always ask user before committing**

```powershell
git commit -m "feat(module): description"
git commit -m "fix(adapter): description"
```

---

## Windows-Only

- COM required: pywin32
- Use PowerShell commands
- CAD startup: 15-20s (configurable)

---

**Version**: 0.1.3 | **Commands**: 54 | **Unified Tools**: 7
