"""
Custom exceptions for multiCAD-MCP server.
Provides domain-specific error handling for CAD operations.
"""

from typing import Any, List


class MultiCADError(Exception):
    """Base exception for all multiCAD-MCP errors."""

    pass


class CADConnectionError(MultiCADError):
    """Raised when connection to CAD application fails."""

    def __init__(self, cad_type: str, reason: str):
        self.cad_type = cad_type
        self.reason = reason
        super().__init__(f"Failed to connect to {cad_type}: {reason}")


class CADOperationError(MultiCADError):
    """Raised when a CAD operation fails."""

    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        super().__init__(f"CAD operation '{operation}' failed: {reason}")


class InvalidParameterError(MultiCADError):
    """Raised when invalid parameters are provided."""

    def __init__(self, param_name: str, param_value: Any, expected_type: str):
        self.param_name = param_name
        self.param_value = param_value
        self.expected_type = expected_type
        super().__init__(
            f"Invalid parameter '{param_name}': got {type(param_value).__name__}, "
            f"expected {expected_type}"
        )


class CoordinateError(InvalidParameterError):
    """Raised when coordinate validation fails."""

    def __init__(self, coordinate: Any, reason: str):
        super().__init__("coordinate", coordinate, "tuple/list of 2-3 numbers")
        self.reason = reason


class ColorError(InvalidParameterError):
    """Raised when color specification is invalid."""

    def __init__(self, color: str, reason: str):
        super().__init__("color", color, "valid color name or hex code")
        self.reason = reason


class LayerError(MultiCADError):
    """Raised when layer operations fail."""

    def __init__(self, layer_name: str, reason: str):
        self.layer_name = layer_name
        self.reason = reason
        super().__init__(f"Layer operation on '{layer_name}' failed: {reason}")


class CADNotSupportedError(MultiCADError):
    """Raised when requested CAD application is not supported."""

    def __init__(self, cad_type: str, supported: List[str]):
        self.cad_type = cad_type
        self.supported = supported
        super().__init__(
            f"CAD type '{cad_type}' is not supported. "
            f"Supported: {', '.join(supported)}"
        )


class NLPParseError(MultiCADError):
    """Raised when NLP parsing fails or produces ambiguous results."""

    def __init__(self, command: str, reason: str):
        self.command = command
        self.reason = reason
        super().__init__(f"Failed to parse command '{command}': {reason}")


class ConfigError(MultiCADError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, config_file: str, reason: str):
        self.config_file = config_file
        self.reason = reason
        super().__init__(f"Configuration error in '{config_file}': {reason}")
