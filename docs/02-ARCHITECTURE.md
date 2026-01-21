# 02 - Architecture

## Overview

```
┌─────────────────────────────────────┐
│  FastMCP Server (server.py)         │
│     54 MCP tools                    │
└──────────────┬──────────────────────┘
               │
       ┌───────┴──────────┐
       │                  │
       ▼                  ▼
┌──────────────┐  ┌──────────────┐
│ Tools Layer  │  │ Config       │
│ (mcp_tools/) │  │ (core/)      │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌────────────────────────────────────┐
│  AutoCADAdapter (Mixin Composition)│
│  ├── UtilityMixin                  │
│  ├── ConnectionMixin               │
│  ├── DrawingMixin                  │
│  ├── LayerMixin                    │
│  ├── ... (11 mixins total)         │
│  └── CADInterface (ABC)            │
└────────────────┬───────────────────┘
                 │
    ┌────────────┼────────────┬──────────────┐
    │            │            │              │
 AutoCAD      ZWCAD      GstarCAD      BricsCAD
    │            │            │              │
    └────────────┼────────────┴──────────────┘
                 ▼
        Windows COM Layer (pywin32)
```

---

## Components

### 1. Server (`server.py`)

Entry point that registers 54 MCP tools via FastMCP. Auto-detects CAD on startup.

### 2. Tools (`mcp_tools/tools/`)

8 modules with 54 tools:

| Module | Tools | Purpose |
|--------|-------|---------|
| connection.py | 4 | Connect/disconnect, status |
| drawing.py | 10 | Draw shapes, create blocks |
| blocks.py | 5 | Block management |
| layers.py | 8 | Layer management |
| files.py | 5 | Save, open, close |
| entities.py | 13 | Select, move, rotate, scale |
| simple.py | 3 | Zoom, undo, redo |
| export.py | 4 | Excel export |
| debug.py | 2 | Diagnostics |

### 3. Adapter (`adapters/`)

**Mixin-based architecture** - The adapter was refactored from a 3,198-line monolithic file to a composite class using 11 specialized mixins:

```python
class AutoCADAdapter(
    UtilityMixin,       # Helpers, converters, property access
    ConnectionMixin,    # COM connection lifecycle
    DrawingMixin,       # draw_line, draw_circle, etc.
    LayerMixin,         # Layer management
    FileMixin,          # File operations
    ViewMixin,          # Zoom, undo, redo
    SelectionMixin,     # Entity selection
    EntityMixin,        # Entity properties
    ManipulationMixin,  # Move, rotate, scale, copy
    BlockMixin,         # Block operations
    ExportMixin,        # Excel export
    CADInterface,       # Abstract base class
):
    pass  # All functionality via mixins
```

**Why Mixins?**
- Each file <500 lines (maintainable)
- Single responsibility per mixin
- Easy code review and navigation
- Reduced merge conflicts
- Testable in isolation

**Why Single Universal Adapter?**
- All compatible CADs use identical COM API
- No code duplication (DRY)
- Bug fixes apply to all CAD types
- Add new CAD = add config only

### 4. AdapterRegistry (`adapter_manager.py`)

Singleton class that encapsulates adapter state:

```python
class AdapterRegistry:
    _instances: Dict[str, AutoCADAdapter]  # Cached adapters
    _active_type: Optional[str]            # Current CAD

    def get_adapter(cad_type) -> AutoCADAdapter
    def set_active(cad_type) -> None
    def reset() -> None  # For testing
```

**Benefits over global variables:**
- Thread-safe state management
- Testable (can reset between tests)
- Explicit lifecycle control

### 5. Core (`core/`)

- **CADInterface**: Abstract base class defining 50+ methods
- **ConfigManager**: Singleton with cascading config search
- **Exceptions**: 8 domain-specific exception types

---

## Data Flow

```
┌─────────────┐    MCP     ┌─────────────┐
│ MCP Client  │ ─────────> │  server.py  │
│ (Claude)    │  Protocol  │  (FastMCP)  │
└─────────────┘            └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ @cad_tool   │ ← Resolves adapter
                           │  decorator  │ ← Error handling
                           └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ Adapter     │ ← get_adapter(cad_type)
                           │ Registry    │
                           └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ AutoCAD     │ ← Mixin methods
                           │ Adapter     │
                           └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ Windows COM │ ← pywin32/pythoncom
                           │ Layer       │
                           └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ CAD App     │
                           │ (AutoCAD)   │
                           └─────────────┘
```

---

## Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Mixin Composition** | AutoCADAdapter | Modular functionality |
| **Singleton** | AdapterRegistry, ConfigManager | Shared state |
| **Context Manager** | com_session, SelectionSetManager | Resource cleanup |
| **Decorator** | @cad_tool, @com_safe | Cross-cutting concerns |
| **Abstract Base** | CADInterface | Contract definition |
| **Dataclass** | All configs | Type-safe configuration |

---

## Exception Hierarchy

```
MultiCADError
├── CADConnectionError     (cad_type, reason)
├── CADOperationError      (operation, reason)
├── InvalidParameterError  (param, value, expected)
│   ├── CoordinateError
│   └── ColorError
├── LayerError             (layer_name, reason)
├── CADNotSupportedError   (cad_type, supported_cads)
└── ConfigError            (config_file, reason)
```

**Benefits:**
- Context-rich error messages
- Granular error handling
- Clear debugging info

---

## Architectural Strengths

### 1. Clean Layer Separation

```
Core (abstractions) ← Adapters (implementation) ← Infrastructure ← Tools ← Server
```

- **0 circular dependencies**
- Each layer only knows the one below
- Easy to replace implementations

### 2. 100% Type Safety

- Type hints on all functions
- Dataclasses for configuration
- mypy-clean (no type errors)

### 3. Robust Resource Management

```python
# Context managers ensure cleanup
with com_session():
    # COM initialized
    with SelectionSetManager(doc, "TempSet") as ss:
        # Selection set created
        ss.SelectAll()
    # Selection set deleted
# COM uninitialized
```

### 4. Performance Optimizations

| Optimization | Impact |
|--------------|--------|
| Connection pooling | Avoids 5-20s reconnections |
| Batch operations | 60-70% fewer API calls |
| PickfirstSelectionSet | Fast entity access |
| Deferred refresh | `_skip_refresh=True` for batches |
| LRU cache | `@lru_cache` on `get_adapter` |

---

## Configuration

Cascading search order:
1. Current directory
2. `src/core/`
3. `src/`
4. Project root
5. Hardcoded defaults

Type-safe via dataclasses:

```python
@dataclass
class CADConfig:
    type: str
    prog_id: str
    startup_wait_time: float
```
