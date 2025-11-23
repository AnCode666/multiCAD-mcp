# multiCAD-mcp Documentation

Welcome to the multiCAD-mcp documentation! This index will guide you through all available documentation.

## For Users

Start with the **[README.md](../README.md)** in the project root for:

- Installation and setup
- Usage examples
- Configuration
- Troubleshooting basics

## For Developers

### Quick Links

1. **[01-SETUP.md](01-SETUP.md)** - Development environment setup
   - Installation for contributors
   - Project structure
   - Running tests and building

2. **[02-ARCHITECTURE.md](02-ARCHITECTURE.md)** - How the system works
   - Three-layer architecture
   - Component descriptions
   - Data flow examples
   - Design patterns used

3. **[03-EXTENDING.md](03-EXTENDING.md)** - Adding new features
   - Step-by-step guides for:
     - New drawing operations
     - New CAD applications
     - New tool categories
   - Code style guidelines
   - Common pitfalls to avoid

4. **[04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md)** - Debugging guide
   - Common issues and solutions
   - Debugging tips
   - How to enable debug logging
   - Using MCP Inspector

5. **[05-REFERENCE.md](05-REFERENCE.md)** - Complete API reference
   - All MCP tools documented
   - Parameters and return values
   - Usage examples
   - Color names and entity types

6. **[06-GIT_SETUP.md](06-GIT_SETUP.md)** - Git workflow
   - Setting up git for contributions
   - Commit conventions
   - Pull request guidelines
   - Development branch strategy

## Directory Structure

```text
docs/
├── README.md                   # This file - documentation index
├── 01-SETUP.md                 # Development environment setup
├── 02-ARCHITECTURE.md          # System design and architecture
├── 03-EXTENDING.md             # Guide to adding new features
├── 04-TROUBLESHOOTING.md       # Debugging and troubleshooting
├── 05-REFERENCE.md             # Complete API reference
├── 06-GIT_SETUP.md             # Git workflow and contribution guide
└── 07-CHANGELOG.md             # Version history and changes
```

## Quick Navigation

**I want to...**

- **Get the server running** → See [../README.md](../README.md) Installation section
- **Understand the code** → Read [02-ARCHITECTURE.md](02-ARCHITECTURE.md)
- **Add a new feature** → Follow [03-EXTENDING.md](03-EXTENDING.md)
- **Fix a problem** → Check [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md)
- **Use a specific tool** → Look up in [05-REFERENCE.md](05-REFERENCE.md)
- **Set up for development** → Start with [01-SETUP.md](01-SETUP.md)

## Project Statistics

- **46 MCP Tools** organized in 9 categories (13 batch operations)
- **Software CAD compatible:** AutoCAD®, ZWCAD®, GstarCAD®, BricsCAD®
- **30% batch-optimized tools** (13 of 46) reducing API calls by 60-70%
- **Full type hints** throughout codebase
- **Complete test coverage** for critical components

## Key Concepts

### Modular Design

The server is split into focused modules:

- `constants.py` - Static configuration
- `helpers.py` - Reusable utilities
- `decorators.py` - Tool registration
- `adapter_manager.py` - CAD adapter lifecycle
- `tools/` - 9 categories of MCP tools (connection, drawing, entities, files, layers, nlp, simple, debug, export)

### Tool Pattern

All MCP tools follow this pattern:

```python
@cad_tool(mcp, "operation_name")
def operation_name(ctx: Context, param1: str, cad_type: Optional[str] = None) -> str:
    # Implementation using get_current_adapter()
    pass
```

### Error Handling

- Domain-specific exceptions for clear error messages
- Unified error handling via `@cad_tool` decorator
- Detailed logging for debugging

## Common Tasks

### Run Tests

```powershell
pytest tests/ -v
```

### Start Server

```powershell
py src/server.py
```

### Check Types

```powershell
mypy src/
```

### Format Code

```powershell
black src/
```

### Enable Debug Logging

Edit `src/config.json`:

```json
{
  "logging_level": "DEBUG"
}
```

## Getting Help

1. **Check the relevant doc** - See Quick Navigation above
2. **Search the code** - Comments and docstrings are clear
3. **Run tests** - Tests show usage examples
4. **Check logs** - Enable debug logging to see what's happening
5. **Use MCP Inspector** - Test tools interactively

## Version Info

- **multiCAD-mcp v0.1.1** - Batch operations optimization
- **Python 3.10+**
- **FastMCP 2.0**
- **Windows COM API**

---

**Questions?** Refer to the documentation above or check the source code - it's well-documented with type hints and docstrings.
