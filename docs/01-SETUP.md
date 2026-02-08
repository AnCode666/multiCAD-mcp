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
│       └── tools/             # 7 unified tools (54 commands)
├── tests/                     # 62 pytest tests
├── docs/                      # Documentation
└── logs/                      # Auto-generated logs
```

## Key Commands

```powershell
pytest tests/ -v                    # Run tests
mypy src/                           # Type check
flake8 src/ --max-line-length 150   # Lint code
black src/                          # Format code
npx -y @modelcontextprotocol/inspector py src/server.py  # MCP Inspector
```

## Git Workflow

### Repository
**URL**: https://github.com/AnCode666/multiCAD-mcp

### Branch Naming
- `feature/<description>` - New features
- `fix/<description>` - Bug fixes
- `refactor/<description>` - Refactoring
- `docs/<description>` - Documentation

### Commit Convention
Use the following format: `<type>(<scope>): <subject>`
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation
- **refactor**: Code refactoring
- **test**: Tests
- **chore**: Build, dependencies

**Example**: `git commit -m "feat(blocks): add insert_block tool"`

## Development Tips

1. **Type hints everywhere** - enables IDE autocomplete
2. **Absolute imports** - `from core import X`, not `from ..core`
3. **Log operations** - use `logger.info()` and `logger.debug()`
4. **Test first** - add tests before committing (`pytest tests/ -v`)
5. **Format & Lint** - run `black src/` and `mypy src/` before push

## Next Steps

- [02-ARCHITECTURE.md](02-ARCHITECTURE.md) - Understand the design and how to extend it
- [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) - Debugging guide
