# multiCAD-mcp

Control your CAD applications with your AI assistant through the Model Context Protocol (MCP).

[![Documentation](https://img.shields.io/badge/docs-mkdocs--material-blue?logo=readthedocs)](https://AnCode666.github.io/multiCAD-mcp/)
[![License](https://img.shields.io/github/license/AnCode666/multiCAD-mcp)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP%202.0-green)](https://github.com/jlowin/fastmcp)

**Documentation**: https://AnCode666.github.io/multiCAD-mcp/

## What is multiCAD-mcp?

multiCAD-mcp is an MCP server that lets you control your CAD software using AI assistants like Claude for desktop or Cursor. Whether you're drawing shapes, managing layers, automating repetitive tasks, o doing complex ones, you can do it all through text-based instructions.

## Features

- **Multiple CAD Support**: Works with AutoCAD®, ZWCAD®, GstarCAD®, and BricsCAD®
- **7 Unified MCP Tools**: Clean access to **55 CAD commands** for drawing, layers, entities, blocks, and files
- **Block Attributes** (v0.2.0+): Read and write block attribute values
- **Block Creation**: Create blocks from entities or user selection
- **Simple command execution**: "Draw a red circle at 50,50 with radius 25" - no complex syntax needed
- **Complex tasks execution**: "Draw the graph of y = sen(X) and label the axes"
- **Simple Integration**: Works with Claude, Cursor, VS Code, and any MCP-compatible client
- **Fast & Reliable**: Efficient COM-based architecture for real-time CAD control
- **Flexible**: Direct tool calls or natural language - choose what works for you

## System Requirements

- **Windows OS** (required - uses Windows COM technology)
- **Python 3.10 or higher**
- **One or more CAD applications** installed in your computer

## Installation

Detailed installation instructions are available in [docs/01-SETUP.md](docs/01-SETUP.md).

Quick start:

```powershell
git clone https://github.com/AnCode666/multiCAD-mcp.git
cd multiCAD-mcp
uv sync --dev
uv run python -m pip install --upgrade pywin32
```

## Setup with Claude Desktop

Add this to your `claude_desktop_config.json`:

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

**Important**: Use the full path to the Python interpreter in your virtual environment (`.venv\Scripts\python.exe`), not the system `py` command. This ensures Claude Desktop uses the correct Python environment with all required dependencies installed.

Replace `C:\path\to\multiCAD-mcp` with your actual installation path.

## Usage Examples

### Direct Tool Calls

multiCAD-mcp provides **7 unified MCP tools** that provide access to **54 different CAD commands**. This architecture is designed for high efficiency, allowing multiple operations to be dispatched in single calls, reducing API overhead by up to 70%.

- **Drawing & Shapes**: Lines, circles, arcs, rectangles, polylines, and splines.
- **Block Management**: Create blocks (from entities or selection), insert (batch/single), list, and audit.
- **Layer Management**: Create, list, rename/delete (batch), and toggle visibility.
- **Entity Manipulation**: Move, rotate, scale, copy/paste, and selection (by type/layer/color).
- **Property Management**: Change color/layer (batch/single) and set color ByLayer.
- **Data & Export**: Extract data (JSON), export to Excel (total or selected), and entity debug.
- **View & Navigation**: Zoom extents, fit view, and undo/redo operations.
- **Files & Session**: Save (DWG/DXF/PDF), new/close drawings, and multi-drawing switching.
- **Connection & Control**: Connection lifecycle, diagnostics, and natural language fallback.

> [!TIP]
> Each tool accepts multiple operations in a single call using a compact shorthand format, reducing API overhead by up to 70%.

### Selected Entity Export

Export or extract data from only the entities currently selected in your CAD viewport:

```text
# Export selected entities to Excel
export_data(scope="selected", format="excel", filename="selected_entities.xlsx")

# Extract selected entity data as JSON
export_data(scope="selected", format="json")
```

### Complex Tasks

You can ask your AI assistant to execute complex tasks that require multiple tools, such as drawing graphs of equations, complex title blocks, or data tables.

## Configuration

Edit `src/config.json` to customize:

```json
{
  "logging_level": "INFO",
  "cad": {
    "autocad": {
      "startup_wait_time": 20,
      "command_delay": 0.5
    }
  },
  "dashboard": {
    "port": 8888
  },
  "output": {
    "directory": "~/Documents/multiCAD Exports"
  }
}
```

**Key settings**:

- **`logging_level`**: Set to `DEBUG`, `INFO`, `WARNING`, or `ERROR` to control log verbosity
- **`startup_wait_time`**: Seconds to wait for CAD application to start (increase if CAD is slow)
- **`command_delay`**: Delay between commands in seconds
- **`dashboard.port`**: Web dashboard port (default: 8888)
- **`open_dashboard`**: [host, port] — open web dashboard in browser (default from config.json: 8888)
- **`output.directory`**: Default directory for saved drawings and exports

## Troubleshooting

### Checking Logs

multiCAD-mcp generates detailed logs to help diagnose issues:

**Log Location**: `logs/multicad_mcp.log` (created automatically in the project's `logs/` directory)

**View logs**:

```powershell
# View latest 50 log entries
Get-Content logs/multicad_mcp.log -Tail 50

# View all logs
Get-Content logs/multicad_mcp.log

# Monitor logs in real-time (updates automatically)
Get-Content logs/multicad_mcp.log -Wait -Tail 10
```

**Adjust log level** in `src/config.json`:

```json
{
  "logging_level": "DEBUG"
}
```

Available levels (from most to least verbose):

- `DEBUG`: Detailed information for diagnosing problems
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages only

**Note**: Restart the MCP server after changing configuration.

### "Connection failed"

- Make sure your CAD application is running
- Check that you have the correct version installed
- Verify Windows COM is properly configured
- Use `manage_session` with `{"action": "status"}` to diagnose the issue
- Check logs for detailed error messages (see above)

The dashboard provides a real-time view of the CAD state. You can manually refresh the data using the "Refresh Now" button.

- **Dashboard Port**: Change `dashboard.port` in `src/config.json` to your preferred port.
- **Manual Refresh**: Click the refresh button to sync with current CAD state.

### "Not connected"

- The server automatically connects on first use
- If it fails, restart the CAD application and try again
- Use `manage_session` with `{"action": "connect"}` to re-establish connection
- Review logs to identify connection issues

### Commands not working

- Check your CAD application's command line for messages or errors
- Ensure coordinates are in valid format (e.g., "0,0" for 2D, "0,0,0" for 3D)
- Verify connection status with `manage_session` → `{"action": "status"}`
- Enable DEBUG logging to see detailed command execution information

## Documentation

- [**Setup & Installation**](docs/01-SETUP.md) - detailed setup guide and Claude Desktop integration.
- [**Architecture**](docs/02-ARCHITECTURE.md) - system design and extension guide.
- [**Troubleshooting**](docs/04-TROUBLESHOOTING.md) - solutions for common issues.
- [**Reference**](docs/05-REFERENCE.md) - complete MCP tool reference.
- [**Changelog**](docs/07-CHANGELOG.md) - version history.

## Supported CAD Applications

| Application | Status | Notes |
|------------|--------|-------|
| AutoCAD 2018+ | ✅ Full Support | Primary implementation |
| ZWCAD 2020+ | ✅ Full Support | Uses AutoCAD-compatible API |
| GstarCAD 2020+ | ✅ Full Support | Uses AutoCAD-compatible API |
| BricsCAD 21+ | ✅ Full Support | Uses AutoCAD-compatible API |

## Project Status

**Version 0.2.0** - Unified tool architecture, block attribute management, and modern packaging.

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Acknowledgments

This project builds upon:
- [CAD-MCP](https://github.com/daobataotie/CAD-MCP)
- [Easy-MCP-AutoCAD](https://github.com/zh19980811/Easy-MCP-AutoCad)

## Support

For issues, questions, or feature requests, please open an issue on the repository.

---

**Need help setting up?** Start with the installation steps above.
