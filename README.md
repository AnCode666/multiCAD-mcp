# multiCAD-mcp

Control your CAD applications with your AI assistant through the Model Context Protocol (MCP).

## What is multiCAD-mcp?

multiCAD-mcp is an MCP server that lets you control your CAD software using AI assistants like Claude for desktop or Cursor. Whether you're drawing shapes, managing layers, automating repetitive tasks, o doing complex ones, you can do it all through text-based instructions.

## Features

- **Multiple CAD Support**: Works with AutoCAD®, ZWCAD®, GstarCAD®, and BricsCAD®
- **7 Unified MCP Tools**: Clean access to **54 CAD commands** for drawing, layers, entities, blocks, and files
- **Block Creation** (v0.1.2+): Create blocks from entities or user selection
- **Batch Operations** (v0.1.1+): 60-70% fewer API calls when managing multiple items
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

### 1. Clone the Repository

```powershell
git clone https://github.com/AnCode666/multiCAD-mcp.git
cd multiCAD-mcp
```

### 2. Setup Virtual Environment (Recommended)

```powershell
# Create virtual environment
py -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
py -m pip install --upgrade pywin32
```

### 4. Verify Installation

Start the server to verify everything works:

```powershell
py src/server.py
```

You should see output indicating that the server has started and auto-detected your CAD application.

**For developers**: See [docs/01-SETUP.md](docs/01-SETUP.md) for detailed setup and troubleshooting.

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
> Use **batch tools** (e.g., `draw_lines`, `rename_layers`) when working with multiple items to minimize token usage and execution time.

### Selected Entity Export

Export or extract data from only the entities currently selected in your CAD viewport:

```text
# Export selected entities to Excel
export_selected_to_excel(filename="selected_entities.xlsx")

# Extract selected entity data as JSON
extract_selected_data()
```

### Complex Tasks

You can ask your AI assistant to execute complex tasks that require multiple tools, such as drawing graphs of equations, complex title blocks, or data tables.

### Natural Language Fallback

If direct tool mapping fails, the `execute_natural_command` tool can trigger simple commands using natural language (e.g., "Draw a red line from 0,0 to 100,100").


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
  "output": {
    "directory": "~/Documents/multiCAD Exports"
  },
}
```

**Key settings**:

- **`logging_level`**: Set to `DEBUG`, `INFO`, `WARNING`, or `ERROR` to control log verbosity
- **`startup_wait_time`**: Seconds to wait for CAD application to start (increase if CAD is slow)
- **`command_delay`**: Delay between commands in seconds
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
- Use the **check_connection** tool to diagnose the issue
- Check logs for detailed error messages (see above)

### "Not connected"

- The server automatically connects on first use
- If it fails, restart the CAD application and try again
- Use the **connect_cad** tool to re-establish connection
- Review logs to identify connection issues

### Commands not working

- Check your CAD application's command line for messages or errors
- Ensure coordinates are in valid format (e.g., "0,0" for 2D, "0,0,0" for 3D)
- Verify connection status with the **check_connection** tool
- Enable DEBUG logging to see detailed command execution information

## Supported CAD Applications

| Application | Status | Notes |
|------------|--------|-------|
| AutoCAD 2018+ | ✅ Full Support | Primary implementation |
| ZWCAD 2020+ | ✅ Full Support | Uses AutoCAD-compatible API |
| GstarCAD 2020+ | ✅ Full Support | Uses AutoCAD-compatible API |
| BricsCAD 21+ | ✅ Full Support | Uses AutoCAD-compatible API |

## Project Status

**Version 0.1.2** - Block creation, code optimization, and set color by layer

- **7 Unified MCP tools** providing access to **54 CAD commands**
- **Block creation** from entity handles or user selection
- **Batch operation support** for ~70% API call reduction
- **Selection-based export** - Export only selected entities to Excel/JSON
- Comprehensive error handling
- Full type safety with Python type hints
- Automated tests for all major components

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details

This project is licensed under the Apache License 2.0.

## Acknowledgments

This project builds upon the work of two foundational projects in CAD-MCP integration:

- **[CAD-MCP](https://github.com/daobataotie/CAD-MCP)** - The original CAD-MCP server implementation that demonstrated how to bridge natural language processing with CAD automation through the Model Context Protocol
- **[Easy-MCP-AutoCAD](https://github.com/zh19980811/Easy-MCP-AutoCad)** - An AutoCAD-specific MCP integration that showed practical approaches to AI-driven CAD control

These projects provided essential inspiration and architectural insights that shaped multiCAD-mcp's base design. multiCAD-mcp expands upon their foundations to create a more robust, multi-CAD compatible, and complete solution.

## Support

For issues, questions, or feature requests, please open an issue on the repository.

---

**Need help setting up?** Start with the installation steps above.

## Learning More

For developers wanting to extend or customize multiCAD-mcp, see the `docs/` folder:

- [**docs/01-SETUP.md**](docs/01-SETUP.md) - Development setup
- [**docs/02-ARCHITECTURE.md**](docs/02-ARCHITECTURE.md) - How the system works
- [**docs/03-EXTENDING.md**](docs/03-EXTENDING.md) - Adding new features
- [**docs/04-TROUBLESHOOTING.md**](docs/04-TROUBLESHOOTING.md) - Debugging guide
- [**docs/05-REFERENCE.md**](docs/05-REFERENCE.md) - Complete tool reference
