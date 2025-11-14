# 04 - Troubleshooting

Common issues and solutions.

## Connection Issues

### "Connection failed: AutoCAD.Application"

**Causes**:

- CAD application not installed
- Outdated Windows COM drivers
- CAD not running

**Solutions**:

```powershell
# Check if CAD is running - open it manually first
# Verify installation: AutoCAD 2018+, ZWCAD 2020+, etc.
# Reinstall pywin32:
py -m pip install --upgrade pywin32

# Verify COM registration:
python -c "import win32com.client; print('COM OK')"
```

### "Not connected to cad - will attempt to connect on first use"

**This is normal** - Server auto-connects on first tool call.

**If it fails**:

1. Check CAD is running
2. Restart CAD application
3. Check firewall/antivirus isn't blocking COM access

### "Document is not available"

**Causes**:

- CAD closed while operation running
- Document closed

**Solutions**:

- Keep CAD application open during operations
- Check CAD's command line for errors
- Restart CAD if document becomes unavailable

## Operation Failures

### "Failed to draw_line: unknown"

**Causes**:

- Invalid coordinates
- AutoCAD in different state (dialog open)
- COM error from AutoCAD

**Debug**:

```powershell
# Check logs
tail -f logs/multicad_mcp.log

# Enable debug logging in src/config.json:
{
  "logging_level": "DEBUG"
}

# Test with MCP Inspector
npx -y @modelcontextprotocol/inspector py src/server.py
```

### Commands work, but drawing is not visible

**Causes**:

- Drawing on hidden layer
- Entity properties not set correctly
- Need to zoom to extents

**Solutions**:

```python
# Call zoom after drawing
zoom_extents()

# Check layer visibility
list_layers()  # See which layers exist

# Verify color/layer in output
draw_line(start="0,0", end="100,100", color="red", layer="0")
```

### "Coordinates out of range" or "Invalid coordinate"

**Valid formats**:

```text
"0,0"          # 2D point
"0,0,0"        # 3D point
"100.5,50.25"  # Floating point OK
"-10,-20"      # Negative coordinates OK
```

**Invalid formats** (will fail):

```text
"0, 0"         # Space after comma
"0"            # Only one coordinate
"a,b"          # Non-numeric
"(0,0)"        # Parentheses not allowed
```

## NLP Issues

### "NLP parsing failed" or low confidence

**Causes**:

- Ambiguous natural language
- Unsupported operation
- Missing parameters

**Solutions**:

```powershell
# Use direct tool calls instead
draw_line(start="0,0", end="100,100")

# Check what was parsed
# Look at logs to see parsed operation and confidence score

# Try clearer language:
# Good: "draw a line from 0,0 to 100,100"
# Bad: "draw something"
```

### NLP strict mode errors

If `strict_mode: true` in config.json:

- All parameters must be provided
- Set to `false` to use defaults

```json
{
  "nlp": {
    "strict_mode": false  # Use defaults for missing params
  }
}
```

## Performance Issues

### Server is slow

**Causes**:

- CAD application is slow
- Network latency (if remote)
- Too many operations queued

**Solutions**:

```json
{
  "cad": {
    "autocad": {
      "command_delay": 1.0  # Increase from 0.5s
    }
  }
}
```

### Operations timeout

**Causes**:

- CAD application frozen
- Very complex drawing
- System resources exhausted

**Solutions**:

```python
# Increase timeout in adapter_manager.py
# Default is 20 seconds - some operations may need more

# Break complex operations into smaller steps
# Instead of 1000 lines at once, do 100 lines at a time
```

## Configuration Issues

### "Config file not found" or config defaults not working

**Check file location**:

```powershell
# config.json should be at:
src/config.json

# Verify structure:
{
  "cad": {
    "autocad": {
      "startup_wait_time": 20.0,
      "command_delay": 0.5
    }
  }
}
```

### Changes to config.json not taking effect

**Solutions**:

- Restart server after changing config
- Config is loaded at startup, not on each call
- Check for JSON syntax errors: `python -m json.tool src/config.json`

## Import/Installation Issues

### "ModuleNotFoundError: No module named 'win32com'"

```powershell
pip install -r requirements.txt
py -m pip install --upgrade pywin32
```

### "pythoncom not found"

This comes with pywin32:

```powershell
py -m pip install --upgrade pywin32
```

### "Type checking errors (Pylance)"

If you see "is not a known attribute of None":

- These are false positives from dynamic adapter resolution
- Code works at runtime despite Pylance warnings
- Use `# type: ignore` if necessary

## File/Directory Issues

### "Output directory not found"

**Check config**:

```json
{
  "output": {
    "directory": "~/Documents/multiCAD Exports"
  }
}
```

The `~` (home directory) is expanded automatically.

### "Permission denied" when saving

**Causes**:

- Directory doesn't exist
- No write permission
- File is locked by CAD

**Solutions**:

- Use full path: `C:\Users\YourName\Documents\drawing.dwg`
- Check directory permissions
- Close file in CAD if already open

## Debugging Tips

### Enable Debug Logging

File: `src/config.json`

```json
{
  "logging_level": "DEBUG"
}
```

Then check logs:

```powershell
tail -f logs/multicad_mcp.log
```

### Check Tool Registration

```powershell
# Verify all tools registered
python -c "
from src.server import mcp
tools = [t.name for t in mcp.tools.values()]
print(f'Registered {len(tools)} tools')
for tool in sorted(tools):
    print(f'  - {tool}')
"
```

### Test CAD Connection Directly

```python
from src.adapters import create_adapter

adapter = create_adapter("autocad")
print(f"Connected: {adapter.is_connected()}")
print(f"Document: {adapter.document}")
```

### Use MCP Inspector

Open the terminal in the root folder of the project and execute the command that runs MCP Inspector.

```powershell
npx -y @modelcontextprotocol/inspector
```

If you like, you can add here the py command, and the relative path to the server.py file: `py src/server.py`

```powershell
npx -y @modelcontextprotocol/inspector py src/server.py
```

Browse to `http://localhost:3000` to:

- See all available tools
- Test tools with different parameters
- See real-time request/response

## Getting Help

1. **Check logs**: `logs/multicad_mcp.log` has detailed information
2. **Enable debug**: Set `logging_level: "DEBUG"` in config
3. **Test directly**: Use Python REPL to test adapters
4. **Use Inspector**: MCP Inspector shows tool details
5. **Check examples**: Look at `README.md` and `tests/`

## Common Error Messages

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| "Not connected" | CAD not running | Start CAD application |
| "Invalid coordinate" | Bad format | Use "x,y" or "x,y,z" format |
| "Unknown operation" | NLP parse failed | Use direct tool call instead |
| "Failed to..." | Operation error | Check CAD's command line, try again |
| "Permission denied" | File access issue | Check file permissions, path |
| "Document not available" | CAD closed | Restart CAD, reconnect |

## Still Stuck?

1. Collect debug information:

   ```powershell
   # Show system info
   python --version
   python -c "import sys; print(sys.platform)"

   # Show logs
   cat logs/multicad_mcp.log
   ```

2. Check the [02-ARCHITECTURE.md](02-ARCHITECTURE.md) to understand how things work

3. Review examples in [03-EXTENDING.md](03-EXTENDING.md)

4. Search [05-REFERENCE.md](05-REFERENCE.md) for tool documentation
