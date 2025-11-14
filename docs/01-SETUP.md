# 01 - Development Setup

Quick setup guide for developers wanting to contribute or extend multiCAD-mcp.

## Prerequisites

- Python 3.10+
- Git
- Windows OS with COM support
- One or more CAD applications (AutoCAD®, ZWCAD®, GstarCAD®, BricsCAD®)

## Installation

### 1. Clone the Repository

```powershell
git clone https://github.com/AnCode666/multiCAD-mcp.git
cd multiCAD-mcp
```

### 2. Create Virtual Environment

```powershell
py -m venv .venv
```

### 3. Activate Virtual Environment

```powershell
.venv\Scripts\Activate.ps1
```

**Note**: If you get an execution policy error, run this once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
py -m pip install --upgrade pywin32
```

### 5. Verify Installation

```powershell
# Test imports
python -c "from src.server import mcp; print('OK')"

# Run tests
pytest tests/ -v

# Start server
py src/server.py

# Or test with MCP Inspector
npx -y @modelcontextprotocol/inspector py src/server.py
```

## Project Structure

```text
multiCAD-mcp/
│
├── .venv                     # Python virtual environment (do not commit to git)
├── .gitignore                # Git ignore rules
├── LICENSE                   # Apache License 2.0
├── README.md                 # Main documentation
├── requirements.txt          # Python dependencies
├── mypy.ini                  # Type checking configuration
│
├── src/                     # Main source code
│   ├── server.py            # FastMCP entry point (main script)
│   ├── __version__.py       # Centralized version management (v0.1.0)
│   ├── config.json          # Runtime configuration
│   │
│   ├── mcp_tools/           # MCP server infrastructure
│   │   ├── __init__.py      # Package initialization
│   │   ├── adapter_manager.py # Adapter lifecycle & caching
│   │   ├── constants.py     # Color maps, selection sets, timing
│   │   ├── decorators.py    # @cad_tool decorator & adapter injection
│   │   ├── helpers.py       # Utilities (parsing, logging, formatting)
│   │   └── tools/           # MCP tools (9 categories, 40+ tools)
│   │       ├── __init__.py  # Tools package initialization
│   │       ├── connection.py # CAD connection management
│   │       ├── debug.py     # Debug utilities
│   │       ├── drawing.py   # Geometric drawing operations
│   │       ├── entities.py  # Entity selection & manipulation
│   │       ├── export.py    # Export operations (Excel, etc.)
│   │       ├── files.py     # File operations (save, open, new)
│   │       ├── layers.py    # Layer management
│   │       ├── nlp.py       # Natural language processing
│   │       └── simple.py    # View & history (zoom, undo, redo)
│   │
│   ├── adapters/            # CAD implementations (factory pattern)
│   │   ├── __init__.py      # Factory: create_adapter(), registry
│   │   └── autocad_adapter.py # Universal adapter (AutoCAD®, ZWCAD®, GstarCAD®, BricsCAD®)
│   │
│   ├── core/                # Abstract interfaces & config
│   │   ├── __init__.py      # Core package initialization
│   │   ├── cad_interface.py # Abstract CADInterface (all operations)
│   │   ├── config.py        # Configuration management (singleton)
│   │   └── exceptions.py    # Custom exceptions (9 types)
│   │
│   └── nlp/                 # Natural language processing
│       ├── __init__.py      # NLP package initialization
│       └── processor.py     # NLP parser with confidence scoring
│
├── tests/                   # Test suite (pytest)
│   ├── __init__.py          # Test package initialization
│   ├── test_adapters.py     # Adapter interface tests
│   ├── test_integration.py  # End-to-end tests
│   └── test_nlp_processor.py # NLP parsing tests
│
├── docs/                    # Documentation (8 files)
│   ├── README.md            # Documentation index
│   ├── 01-SETUP.md          # Development setup (this file)
│   ├── 02-ARCHITECTURE.md   # System design & architecture
│   ├── 03-EXTENDING.md      # Adding new features guide
│   ├── 04-TROUBLESHOOTING.md # Debug & troubleshooting
│   ├── 05-REFERENCE.md      # Complete tool reference (40+ tools)
│   ├── 06-GIT_SETUP.md      # Git workflow
│   └── 07-CHANGELOG.md      # Version history
│
└── logs/                    # Auto-generated logs (created at runtime)
    └── multicad_mcp.log     # Application log file
```

**Key Configuration Files**:

- `mypy.ini` - Type checking configuration for `mypy src/`
- `requirements.txt` - Python package dependencies (pinned versions)
- `.venv/` - Project virtual environment (do not commit to git)

## Key Commands

```powershell
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_nlp_processor.py::TestNLPProcessor::test_parse_draw_line -v

# Check types
mypy src/

# Lint code
flake8 src/

# Format code
black src/

# Start server with debug logging
PYTHONPATH=src py -m server
```

## Configuration

### Runtime Configuration

- **src/config.json** - Runtime settings (startup times, output directory, NLP settings)
- See [03-EXTENDING.md](03-EXTENDING.md) for customization options

### Type Checking Configuration

**mypy.ini** - Configures Python type checking:

```ini
[mypy]
python_version = 3.10              # Target Python version
check_untyped_defs = True          # Check untyped function definitions
warn_no_return = True              # Warn on missing return statements
strict_optional = True             # Strict Optional type checking

[mypy-win32com.*]                  # Skip type checking for Windows COM
ignore_missing_imports = True      # (libraries without type stubs)
```

Run type checking with:

```powershell
mypy src/
```

### Constants & Defaults

- **Color Map**: AutoCAD Color Index (ACI) mapping in `src/adapters/autocad_adapter.py`
- **Selection Sets**: Predefined names in `src/mcp_tools/constants.py`
- **Timing**: Command delays & startup waits in `src/config.json`

## File Organization

**Infrastructure (no CAD operations)**:

- `constants.py` - Static configuration
- `helpers.py` - Reusable utilities
- `decorators.py` - Unified tool registration
- `adapter_manager.py` - Adapter lifecycle

**Operations (CAD-specific)**:

- `tools/*.py` - Individual tool modules (53 tools total)
- `adapters/*.py` - CAD implementations
- `nlp/processor.py` - Natural language parsing

## Testing

Tests are located in `tests/`:

- `test_nlp_processor.py` - NLP parsing tests
- `test_adapters.py` - Adapter interface tests
- `test_integration.py` - End-to-end tests

All tests run independently without requiring CAD applications.

## Virtual Environment Management

### Always Use the Virtual Environment

Before running any commands (tests, server, MCP Inspector), ensure the virtual environment is **activated**:

```powershell
# Activate
.venv\Scripts\Activate.ps1

# Check if activated (prompt should show ".venv")
# Run your commands
pytest tests/ -v

# Deactivate when done
deactivate
```

### Virtual Environment Troubleshooting

**Issue**: "ModuleNotFoundError: No module named 'mcp'"

- Solution: Ensure `.venv` is activated before running commands
- Verify: Check prompt shows `(.venv)` prefix

**Issue**: "Packages are installed but not found"

- Solution: Delete and recreate the virtual environment:

  ```powershell
  Remove-Item -Recurse -Force .venv
  py -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  py -m pip install --upgrade pywin32
  ```

**Issue**: "MCP Inspector can't find packages"

- MCP Inspector automatically uses your activated venv
- Ensure venv is activated before running: `npx -y @modelcontextprotocol/inspector py src/server.py`

**Issue**: Dependencies have wrong versions

- Check `requirements.txt` has compatible versions (latest: openpyxl≥3.1.0, mcp≥1.2.0, pywin32≥300)
- Reinstall: `pip install --upgrade -r requirements.txt`

## Development Tips

1. **Always use type hints** - enables IDE autocomplete and catches errors early
2. **Follow existing patterns** - look at similar tools before implementing new ones
3. **Log important operations** - use `logger.info()` and `logger.debug()` to write the logs on the multiCAD-mcp log file
4. **Write docstrings** - document function purpose, args, return value
5. **Test thoroughly** - add tests for new features
6. **Keep venv activated** - all Python commands should use the project's virtual environment

## Next Steps

- Read [02-ARCHITECTURE.md](02-ARCHITECTURE.md) to understand the design
- Check [03-EXTENDING.md](03-EXTENDING.md) to add new features
- See [05-REFERENCE.md](05-REFERENCE.md) for tool documentation
