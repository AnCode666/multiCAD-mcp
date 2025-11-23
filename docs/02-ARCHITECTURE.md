# 02 - Architecture

Overview of how multiCAD-mcp is organized and how components interact.

## Three-Layer Architecture

```text
┌─────────────────────────────────────┐
│  FastMCP Server (server.py)         │
│     MCP tools, tool schemas         │
└──────────────┬──────────────────────┘
               │
       ┌───────┴──────────┬─────────────┐
       │                  │             │
       ▼                  ▼             ▼
┌────────────────┐  ┌──────────────┐  ┌──────────────┐
│ NLP Processor  │  │ CAD Manager  │  │ Config       │
│ (nlp/)         │  │ (adapters/)  │  │ (core/)      │
└────────────────┘  └──────┬───────┘  └──────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │ AutoCADAdapter     │
                  │ (Factory Pattern)  │
                  │ - cad_type param   │
                  └────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┬─────────────┐
         │                 │                 │             │
    AutoCAD           ZWCAD              GstarCAD      BricsCAD
    (prog_id:        (prog_id:          (prog_id:    (prog_id:
     AutoCAD.        ZWCAD.             GCAD.        BricscadApp.
     Application)    Application)       Application) AcadApplication)
         │                 │                 │             │
         └─────────────────┼─────────────────┴─────────────┘
                           ▼
              ┌──────────────────────┐
              │  Windows COM Layer   │
              │  (pywin32, pythoncom)│
              └──────────────────────┘
                         ▼
              ┌──────────────────────┐
              │  CAD Application     │
              │  (All Compatible)    │
              └──────────────────────┘
```

## Core Components

### 1. FastMCP Server (`server.py`)

**Role**: Entry point that registers and orchestrates all tools.

- Initializes FastMCP with 46 MCP tools
- Tools organized into 9 categories (connection, drawing, entities, files, layers, nlp, simple, debug, export)
- Handles auto-detection of connected CAD applications on startup
- Lean entry point that delegates to mcp_tools modules

### 2. Server Infrastructure (`mcp_tools/`)

**Modules**:

- **constants.py**: Color maps, selection set names, timing defaults
- **helpers.py**: Parsing, logging setup, message formatting, result formatting
- **decorators.py**: `@cad_tool` decorator for unified error handling
- **adapter_manager.py**: Adapter lifecycle, caching, auto-detection

**Key Pattern**: Tools use `@cad_tool(mcp, operation_name)` decorator which:

1. Resolves correct adapter based on `cad_type` parameter
2. Injects adapter into global `_current_adapter` variable
3. Wraps with try/catch for consistent error handling

### 3. MCP Tools (`mcp_tools/tools/`)

**9 Tool Modules** (46 tools total):

- **connection.py**: Connect/disconnect CAD, check status, list supported apps
- **drawing.py**: Draw lines, circles, rectangles, polylines, text, dimensions
- **entities.py**: Select by color/layer/type, move, rotate, scale, copy, paste
- **files.py**: Save/open drawings, manage open files
- **layers.py**: Create, list, delete, rename layers; toggle visibility
- **nlp.py**: Execute natural language commands
- **simple.py**: Zoom extents, undo, redo
- **debug.py**: List entities, test selection methods
- **export.py**: Export to Excel, CSV, and other formats

**Pattern**: Each tool module contains a `register_*_tools(mcp)` function that:

1. Defines all tools in that category
2. Uses `@cad_tool` decorator for error handling
3. Gets called once at server startup

### 4. Abstract Interface (`core/cad_interface.py`)

**CADInterface**: Abstract base class defining all operations:

- Connection management: `connect()`, `disconnect()`, `is_connected()`
- Drawing: `draw_line()`, `draw_circle()`, `draw_arc()`, `draw_rectangle()`, etc.
- Layers: `create_layer()`, `list_layers()`, `delete_layer()`, etc.
- Files: `save_drawing()`, `new_drawing()`, `close_drawing()`, etc.
- Selection: `select_by_color()`, `select_by_layer()`, `select_by_type()`
- Manipulation: `move_entities()`, `rotate_entities()`, `scale_entities()`, etc.

All adapters must implement this interface.

### 5. CAD Adapters (`adapters/`)

**Factory Pattern Architecture** (v1.0.1+):

```text
adapters/
├── __init__.py              # Factory: create_adapter(cad_type)
└── autocad_adapter.py       # Universal adapter (1900+ lines)
    └── Supports all CAD types via ProgID selection:
        - AutoCAD (prog_id: "AutoCAD.Application")
        - ZWCAD (prog_id: "ZWCAD.Application")
        - GstarCAD (prog_id: "GCAD.Application")
        - BricsCAD (prog_id: "BricscadApp.AcadApplication")
```

**Why Single Adapter?**

- All compatible CADs use the same COM API
- No code duplication (DRY principle)
- Bug fixes apply to all CAD types
- Easy to add new CAD types (just config)

**Key Features**:

- COM threading safety: `pythoncom.CoInitialize/CoUninitialize`
- Unified error handling with logging
- Polling-based synchronization: `_wait_for()` replaces brittle `time.sleep()`
- Helper methods: `_select_entities_generic()` for unified selection logic
- Proper cleanup in `disconnect()`
- Uses `win32com.client.GetActiveObject()` for active instances
- Falls back to creating new instance if needed
- Validates connection before each operation

### 6. Configuration (`core/config.py`)

**ConfigManager** (Singleton pattern):

- Loads `config.json` with fallback defaults
- Per-CAD settings: startup times, COM ProgID, command delays
- NLP settings: strict mode, confidence thresholds
- Output settings: default drawing directory

**Key Config Values**:

- `startup_wait_time`: How long to wait for CAD to start (20s default)
- `command_delay`: Pause between commands (0.5s default)
- `strict_mode`: NLP parameter validation (false = use defaults)

### 7. NLP Processor (`nlp/processor.py`)

**ParsedCommand** (dataclass):

```python
@dataclass
class ParsedCommand:
    operation: str          # "draw_line", "draw_circle", etc.
    confidence: float       # 0.0-1.0
    parameters: Dict[str, Any]
```

**Parsing Flow**:

1. Identify operation from keywords (shape type, action)
2. Extract parameters (coordinates, colors, dimensions)
3. Calculate confidence score
4. Return ParsedCommand or raise NLPParseError

**Supported Operations**:

- `draw_line`: Extract start/end coordinates
- `draw_circle`: Extract center, radius
- `draw_rectangle`: Extract corners
- `draw_polyline`: Extract point list
- `draw_text`: Extract position, text, height

## Data Flow Example

**User Request**: "Draw a red line from 0,0 to 100,100"

1. **Server.py** receives request → calls `execute_natural_command()`
2. **@cad_tool decorator**:
   - Calls `get_adapter()` to get/create AutoCAD adapter
   - Sets `_current_adapter` global variable
3. **NLP Tool** calls `nlp_processor.parse_command()`
4. **NLP Processor**:
   - Identifies `draw_line` operation
   - Extracts coordinates and color
   - Returns ParsedCommand with 95% confidence
5. **NLP Tool** calls `adapter.draw_line()`
6. **AutoCAD Adapter**:
   - Validates connection
   - Normalizes coordinates
   - Calls COM to create line entity
   - Applies properties (color, layer, lineweight)
   - Returns entity handle
7. **Server** returns result to client

## Key Design Patterns

1. **Abstract Base Class**: CADInterface defines contract
2. **Adapter Pattern**: Implementations for different CADs
3. **Factory Pattern**: `create_adapter()` in `adapters/__init__.py`
4. **Decorator Pattern**: `@cad_tool` for error handling
5. **Singleton Pattern**: ConfigManager
6. **Strategy Pattern**: Different filter functions for entity selection
7. **Template Method**: Consistent operation flow across adapters

## Error Handling

**Custom Exceptions**:

- `CADConnectionError` - Connection failed
- `CADOperationError` - Operation failed
- `InvalidParameterError` - Bad parameter
- `CoordinateError` - Invalid coordinate
- `ColorError` - Invalid color
- `LayerError` - Layer operation failed
- `CADNotSupportedError` - Unknown CAD type
- `NLPParseError` - NLP parsing failed
- `ConfigError` - Config loading failed

**Pattern**: Tools catch specific exceptions and re-raise as CADOperationError for consistency.

## Performance Optimizations

- **Adapter Caching**: `@lru_cache(maxsize=4)` on `get_adapter()`
- **Connection Pooling**: Global `_cad_instances` dict prevents reconnections
- **Regex Precompilation**: `_COORD_PATTERN` compiled once at module load
- **Lazy Initialization**: Adapters created on first use, not at startup
- **Polling over Sleep**: `_wait_for()` replaces brittle `time.sleep()`

## Testing Strategy

**Unit Tests**:

- NLP parser tests (25+ cases)
- Adapter interface tests (20+ cases)
- No CAD required - all tests isolated

**Integration Tests**:

- Tool registration verification
- End-to-end CAD operations

**Test File**: `tests/test_*.py`

## Next Steps

- [03-EXTENDING.md](03-EXTENDING.md) - How to add new features
- [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) - Debugging guide
- [05-REFERENCE.md](05-REFERENCE.md) - Complete tool reference
