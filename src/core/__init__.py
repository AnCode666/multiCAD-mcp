"""
Core modules for multiCAD-MCP.
Provides configuration, exception handling, and abstract interfaces.
"""

from .config import (
    ConfigManager,
    ServerConfig,
    CADConfig,
    OutputConfig,
    get_config,
    get_cad_config,
    get_supported_cads,
)
from .exceptions import (
    MultiCADError,
    CADConnectionError,
    CADOperationError,
    InvalidParameterError,
    CoordinateError,
    ColorError,
    LayerError,
    CADNotSupportedError,
    ConfigError,
)
from .cad_interface import (
    CADInterface,
    LineWeight,
    Color,
    Coordinate,
    Point,
)

__all__ = [
    # Config
    "ConfigManager",
    "ServerConfig",
    "CADConfig",
    "OutputConfig",
    "get_config",
    "get_cad_config",
    "get_supported_cads",
    # Exceptions
    "MultiCADError",
    "CADConnectionError",
    "CADOperationError",
    "InvalidParameterError",
    "CoordinateError",
    "ColorError",
    "LayerError",
    "CADNotSupportedError",
    "ConfigError",
    # Interfaces
    "CADInterface",
    "LineWeight",
    "Color",
    "Coordinate",
    "Point",
]
