# 01 - Development Setup

## Prerequisites

- Python 3.10+
- Windows OS with COM support
- CAD application (AutoCAD, ZWCAD, GstarCAD, or BricsCAD)

## Installation
 
### 1. Install `uv`

`uv` is the recommended Python package manager for this project. To install it on Windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

For other methods or platforms, see the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

### 2. Clone and Setup

```powershell
# Clone
git clone https://github.com/AnCode666/multiCAD-mcp.git
cd multiCAD-mcp

# Install dependencies (creates .venv automatically)
uv sync --dev
uv run python -m pip install --upgrade pywin32

# Verify
uv run pytest tests/ -v
uv run python src/server.py
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

**Important**: Use the full path to `.venv\Scripts\python.exe` created by `uv sync`, not the system `py`.

## Project Structure

```
multiCAD-mcp/
├── src/
│   ├── server.py              # FastMCP entry point
│   ├── __version__.py         # Version (0.2.0)
│   ├── config.json            # Runtime configuration
│   ├── core/                  # Abstract interfaces
│   │   ├── cad_interface.py   # CADInterface ABC
│   │   ├── config.py          # ConfigManager singleton
│   │   ├── exceptions.py      # Exception hierarchy
│   │   └── models.py          # Data models and schemas
│   ├── adapters/              # CAD implementations
│   │   ├── autocad_adapter.py # Composite class (102 lines)
│   │   ├── adapter_manager.py # AdapterRegistry
│   │   └── mixins/            # 11 mixin modules
│   ├── mcp_tools/             # Server infrastructure
│   │   ├── constants.py       # COLOR_MAP, etc.
│   │   ├── helpers.py         # Utilities
│   │   ├── decorators.py      # @cad_tool
│   │   ├── shorthand.py       # Command parsing logic
│   │   ├── validator.py       # Spec validation and correction
│   │   └── tools/             # 7 unified tools
│   ├── ui/                    # UI resources and templates
│   └── web/                   # Web dashboard API and static files
├── tests/                     # 181 pytest tests
├── docs/                      # Documentation
└── logs/                      # Auto-generated logs
```

## Key Commands

```powershell
uv run pytest tests/ -v                    # Run tests
uv run mypy src/                           # Type check
uv run ruff check src/                     # Lint code
uv run ruff format src/                    # Format code
npx -y @modelcontextprotocol/inspector uv run python src/server.py  # MCP Inspector
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
4. **Test first** - add tests before committing (`uv run pytest tests/ -v`)
5. **Format & Lint** - run `uv run ruff check src/` and `uv run mypy src/` before push

## Next Steps

- [02-ARCHITECTURE.md](02-ARCHITECTURE.md) - Understand the design and how to extend it
- [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) - Debugging guide
