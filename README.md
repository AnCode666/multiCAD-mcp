# multiCAD-mcp

Control your CAD applications with your AI assistant through the Model Context Protocol (MCP).

## What is multiCAD-mcp?

multiCAD-mcp is an MCP server that lets you control your CAD software using AI assistants like Claude for desktop or Cursor. Whether you're drawing shapes, managing layers, automating repetitive tasks, o doing complex ones, you can do it all through text-based instructions.

## Features

- **Multiple CAD Support**: Works with AutoCAD®, ZWCAD®, GstarCAD®, and BricsCAD®
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

The primary way to use multiCAD-mcp is through direct tool calls:

#### Drawing (8 tools)

- **draw_line**: Draw lines between two points
- **draw_circle**: Draw circles with radius
- **draw_arc**: Draw arcs with angles
- **draw_rectangle**: Draw rectangles
- **draw_polyline**: Draw connected lines
- **draw_circle_and_line**: Draw circle and tangent line
- **draw_text**: Add text annotations
- **add_dimension**: Add dimension annotations

#### Entity Operations (10 tools)

- **select_by_color/layer/type**: Select entities by criteria
- **move_entities**: Move selected entities
- **rotate_entities**: Rotate entities around a point
- **scale_entities**: Scale entities by factor
- **copy_entities**: Copy entities to clipboard
- **paste_entities**: Paste from clipboard
- **change_entity_color/layer**: Modify entity properties

#### Layer Management (7 tools)

- **create_layer**: Create new layers
- **list_layers**: List all layers
- **rename_layer**: Rename existing layer
- **delete_layer**: Remove layers
- **turn_layer_on/off**: Toggle layer visibility
- **is_layer_on**: Check layer visibility status

#### File Operations (5 tools)

- **save_drawing**: Save to DWG, DXF, or PDF
- **new_drawing**: Create blank drawing
- **close_drawing**: Close active drawing
- **get_open_drawings**: List open files
- **switch_drawing**: Switch between open drawings

#### Data Export (2 tools)

- **export_drawing_to_excel**: Export entities and layers to Excel
- **extract_drawing_data**: Get raw entity data as JSON

#### Connection & Control (9 tools)

- **connect_cad/disconnect_cad**: Manage CAD connections
- **check_connection**: Verify connection status
- **get_active_cad_type**: Get current CAD application
- **zoom_extents**: Fit view to all entities
- **undo/redo**: Undo/redo operations
- **get_server_info/get_mcp_config**: Server diagnostics
- **execute_natural_command**: Natural language fallback

### Complex tasks that require multiple Tool Calls

You can also ask you AI assistant to execute complex tasks, that require the use of several drawing tools:

- **Draw the graphic of a ecuation**: Fast and accurate drawing of complex shapes
- **Draw a title block**: Automate drawing layout related tasks
- **Draw a table with some data"**: Automate the creation of data tables in drawings.

### Natural Language Fallback

For AI assistants: if direct tool mapping fails, the **execute_natural_command** tool can trigger simple commands using natural language:

```text
"Draw a red line from 0,0 to 100,100"
"Create a blue circle at 50,50 with radius 25"
```

**Note**: This is a fallback mechanism. AI assistants should prefer direct tool calls for better reliability and type safety.

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
  "nlp": {
    "strict_mode": false
  }
}
```

**Key settings**:

- **`logging_level`**: Set to `DEBUG`, `INFO`, `WARNING`, or `ERROR` to control log verbosity
- **`startup_wait_time`**: Seconds to wait for CAD application to start (increase if CAD is slow)
- **`command_delay`**: Delay between commands in seconds
- **`output.directory`**: Default directory for saved drawings and exports
- **`nlp.strict_mode`**: When `true`, requires all parameters in natural language commands

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

**Note**: As noted before, the `config.json` file controls various aspects of multiCAD-mcp behavior including CAD startup timeouts, output directories, and NLP settings. Restart the MCP server after changing configuration.

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

**Version 0.1.0** - First stable version

- 40+ MCP tools covering all major CAD operations
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
