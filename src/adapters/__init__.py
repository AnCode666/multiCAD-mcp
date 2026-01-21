"""
CAD adapters for multiCAD-MCP.

Design:
- All compatible CADs (AutoCAD, ZWCAD, GstarCAD, BricsCAD) use the same COM API
- Single AutoCADAdapter works with all CAD types via ProgID configuration in config.json
- No factory pattern needed - just instantiate AutoCADAdapter(cad_type)
"""

from .autocad_adapter import AutoCADAdapter

__all__ = ["AutoCADAdapter"]
