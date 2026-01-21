# 01 - Development Setup

## Prerequisites

- Python 3.10+
- Windows OS with COM support
- CAD application (AutoCAD, ZWCAD, GstarCAD, or BricsCAD)

## Installation

```powershell
# Clone
git clone https://github.com/AnCode666/multiCAD-mcp.git
cd multiCAD-mcp

# Virtual environment
py -m venv .venv
.venv\Scripts\Activate.ps1

# Dependencies
pip install -r requirements.txt
py -m pip install --upgrade pywin32

# Verify
pytest tests/ -v
py src/server.py
```

**Note**: If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Claude Desktop Integration

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "multiCAD": {
      "command": "C:\\path\\to\\multiCAD-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\multiCAD-mcp\\src\\server.py"]
    }
  }
}
```

**Important**: Use full path to `.venv\Scripts\python.exe`, not system `py`.

## Project Structure

```
multiCAD-mcp/
├── src/
│   ├── server.py              # FastMCP entry point
│   ├── __version__.py         # Version (0.1.2)
│   ├── config.json            # Runtime configuration
│   ├── core/                  # Abstract interfaces
│   │   ├── cad_interface.py   # CADInterface ABC
│   │   ├── config.py          # ConfigManager singleton
│   │   └── exceptions.py      # Exception hierarchy
│   ├── adapters/              # CAD implementations
│   │   ├── autocad_adapter.py # Composite class (99 lines)
│   │   ├── adapter_manager.py # AdapterRegistry
│   │   └── mixins/            # 11 mixin modules
│   └── mcp_tools/             # Server infrastructure
│       ├── constants.py       # COLOR_MAP, etc.
│       ├── helpers.py         # Utilities
│       ├── decorators.py      # @cad_tool
│       └── tools/             # 7 tool modules (47 tools)
├── tests/                     # 62 pytest tests
├── docs/                      # Documentation
└── logs/                      # Auto-generated logs
```

## Key Commands

```powershell
pytest tests/ -v                    # Run tests
mypy src/                           # Type check
black src/                          # Format code
npx -y @modelcontextprotocol/inspector py src/server.py  # MCP Inspector
```

## Development Tips

1. **Type hints everywhere** - enables IDE autocomplete
2. **Absolute imports** - `from core import X`, not `from ..core`
3. **Log operations** - use `logger.info()` and `logger.debug()`
4. **Test first** - add tests for new features
5. **Keep venv activated** - all commands use project's venv

## Next Steps

- [02-ARCHITECTURE.md](02-ARCHITECTURE.md) - Understand the design
- [03-EXTENDING.md](03-EXTENDING.md) - Add new features
