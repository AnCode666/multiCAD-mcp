"""
CAD adapters for multiCAD-MCP.
Provides unified adapter factory for all compatible CAD applications.

Design:
- All compatible CADs (AutoCAD, ZWCAD, GstarCAD, BricsCAD) use the same COM API
- Instead of creating separate adapter classes, use a single AutoCADAdapter
- The adapter is initialized with a cad_type parameter to select the correct ProgID
- This eliminates code duplication and simplifies maintenance
"""

from typing import Type
from .autocad_adapter import AutoCADAdapter

__all__ = [
    "AutoCADAdapter",
    "create_adapter",
    "get_adapter",
    "ADAPTER_REGISTRY",
]


# Supported CAD types and their ProgIDs (from config.json)
# All use AutoCADAdapter since they share the same COM API
SUPPORTED_CADS = {
    "autocad": "AutoCAD.Application",
    "zwcad": "ZWCAD.Application",
    "gcad": "GCAD.Application",
    "bricscad": "BricscadApp.AcadApplication",
}

# Registry maps CAD type to adapter class
# All CAD types use AutoCADAdapter with appropriate cad_type parameter
ADAPTER_REGISTRY = {cad_type: AutoCADAdapter for cad_type in SUPPORTED_CADS.keys()}


def get_adapter(cad_type: str) -> Type[AutoCADAdapter]:
    """
    Get adapter class for specified CAD type.

    Args:
        cad_type: Type of CAD (autocad, zwcad, gcad, bricscad)

    Returns:
        Adapter class (AutoCADAdapter for all supported types)

    Raises:
        ValueError: If CAD type is not supported
    """
    cad_type = cad_type.lower()
    if cad_type not in ADAPTER_REGISTRY:
        supported = ", ".join(ADAPTER_REGISTRY.keys())
        raise ValueError(
            f"CAD type '{cad_type}' not supported. " f"Supported types: {supported}"
        )
    return ADAPTER_REGISTRY[cad_type]


def create_adapter(cad_type: str) -> AutoCADAdapter:
    """
    Create an instance of the adapter for specified CAD type.

    All compatible CADs (AutoCAD, ZWCAD, GstarCAD, BricsCAD) use the same
    COM API, so this factory creates AutoCADAdapter instances with the
    appropriate cad_type parameter.

    Args:
        cad_type: Type of CAD (autocad, zwcad, gcad, bricscad)

    Returns:
        AutoCADAdapter instance configured for the specified CAD type

    Raises:
        ValueError: If CAD type is not supported
    """
    adapter_class = get_adapter(cad_type)
    return adapter_class(cad_type=cad_type.lower())
