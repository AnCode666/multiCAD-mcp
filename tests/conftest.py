"""
pytest configuration for multiCAD-MCP tests.

Adds src directory to sys.path to enable proper imports for testing.
This allows tests to use absolute imports like "from core import ..."
which work when the server is running.
"""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
