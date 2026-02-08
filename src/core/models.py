"""
Pydantic models for data validation in multiCAD-MCP.

Provides runtime validation for coordinates, colors, layers, and drawing requests.
"""

from typing import Tuple, Optional, Union, List
from pydantic import BaseModel, Field, field_validator, model_validator
from mcp_tools.constants import COLOR_MAP


class CoordinateModel(BaseModel):
    """
    Validates a 2D or 3D coordinate.

    Attributes:
        x: X coordinate (float)
        y: Y coordinate (float)
        z: Z coordinate (float, optional, defaults to 0.0)
    """

    x: float
    y: float
    z: float = 0.0

    @classmethod
    def from_tuple(
        cls, coord: Union[Tuple[float, float], Tuple[float, float, float]]
    ) -> "CoordinateModel":
        """Create CoordinateModel from tuple."""
        if len(coord) == 2:
            return cls(x=coord[0], y=coord[1], z=0.0)
        elif len(coord) == 3:
            return cls(x=coord[0], y=coord[1], z=coord[2])
        else:
            raise ValueError(
                f"Coordinate must be 2D or 3D tuple, got {len(coord)} elements"
            )

    def to_tuple_3d(self) -> Tuple[float, float, float]:
        """Convert to 3D tuple (always returns 3 elements)."""
        return (self.x, self.y, self.z)

    def to_tuple_2d(self) -> Tuple[float, float]:
        """Convert to 2D tuple (ignores z)."""
        return (self.x, self.y)

    @field_validator("x", "y", "z")
    @classmethod
    def validate_numeric(cls, v: float) -> float:
        """Ensure coordinates are valid numbers."""
        if not isinstance(v, (int, float)):
            raise ValueError(f"Coordinate must be numeric, got {type(v)}")
        if not (-1e10 <= v <= 1e10):  # Reasonable CAD coordinate range
            raise ValueError(f"Coordinate value {v} is out of reasonable range")
        return float(v)


class ColorValidator(BaseModel):
    """
    Validates AutoCAD colors (names or ACI indices).

    Attributes:
        color: Color name (e.g., 'red', 'blue') or ACI index (0-256)
    """

    color: Union[str, int] = Field(
        default="white", description="Color name or ACI index"
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Union[str, int]) -> Union[str, int]:
        """Validate color is either a known name or valid ACI index."""
        if isinstance(v, str):
            # Normalize to lowercase with underscores
            color_name = v.lower().replace(" ", "_")
            if color_name not in COLOR_MAP:
                valid_colors = ", ".join(sorted(COLOR_MAP.keys()))
                raise ValueError(
                    f"Invalid color name '{v}'. Valid colors: {valid_colors}"
                )
            return color_name
        elif isinstance(v, int):
            # Validate ACI index range (0-256)
            # 0-255 are standard colors, 256 is ByLayer
            if not (0 <= v <= 256):
                raise ValueError(f"ACI color index must be 0-256, got {v}")
            return v
        else:
            raise ValueError(f"Color must be string or int, got {type(v)}")

    def to_aci(self) -> int:
        """Convert color to ACI index."""
        if isinstance(self.color, int):
            return self.color
        return COLOR_MAP.get(self.color, 7)  # Default to white


class LayerValidator(BaseModel):
    """
    Validates layer names.

    Attributes:
        layer: Layer name (non-empty string)
    """

    layer: str = Field(default="0", min_length=1, max_length=255)

    @field_validator("layer")
    @classmethod
    def validate_layer(cls, v: str) -> str:
        """Validate layer name."""
        if not isinstance(v, str):
            raise ValueError(f"Layer name must be string, got {type(v)}")

        v = v.strip()
        if not v:
            raise ValueError("Layer name cannot be empty")

        # AutoCAD layer name restrictions
        invalid_chars = ["<", ">", "/", "\\", '"', ":", ";", "?", "*", "|", "=", "`"]
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"Layer name cannot contain '{char}'")

        return v


class LineWeightValidator(BaseModel):
    """
    Validates lineweight values.

    Attributes:
        lineweight: Lineweight in hundredths of mm (e.g., 25 = 0.25mm)
    """

    lineweight: int = Field(default=25, ge=-3, le=211)

    @field_validator("lineweight")
    @classmethod
    def validate_lineweight(cls, v: int) -> int:
        """Validate lineweight is in valid range."""
        # Valid lineweights: -3 (ByLayer), -2 (ByBlock), -1 (Default), 0-211 (actual weights)
        valid_weights = [
            -3,
            -2,
            -1,
            0,
            5,
            9,
            13,
            15,
            18,
            20,
            25,
            30,
            35,
            40,
            50,
            53,
            60,
            70,
            80,
            90,
            100,
            106,
            120,
            140,
            158,
            200,
            211,
        ]
        if v not in valid_weights:
            raise ValueError(f"Invalid lineweight {v}. Must be one of: {valid_weights}")
        return v


# ========== Drawing Request Models ==========


class DrawLineRequest(BaseModel):
    """Request model for drawing a line."""

    start: Tuple[float, float] | Tuple[float, float, float]
    end: Tuple[float, float] | Tuple[float, float, float]
    layer: str = "0"
    color: Union[str, int] = "white"
    lineweight: int = 25

    @model_validator(mode="after")
    def validate_all(self) -> "DrawLineRequest":
        """Validate all fields using validators."""
        # Validate coordinates
        CoordinateModel.from_tuple(self.start)
        CoordinateModel.from_tuple(self.end)

        # Validate color
        ColorValidator(color=self.color)

        # Validate layer
        LayerValidator(layer=self.layer)

        # Validate lineweight
        LineWeightValidator(lineweight=self.lineweight)

        return self


class DrawCircleRequest(BaseModel):
    """Request model for drawing a circle."""

    center: Tuple[float, float] | Tuple[float, float, float]
    radius: float = Field(gt=0, description="Radius must be positive")
    layer: str = "0"
    color: Union[str, int] = "white"
    lineweight: int = 25

    @model_validator(mode="after")
    def validate_all(self) -> "DrawCircleRequest":
        """Validate all fields."""
        CoordinateModel.from_tuple(self.center)
        ColorValidator(color=self.color)
        LayerValidator(layer=self.layer)
        LineWeightValidator(lineweight=self.lineweight)
        return self


class DrawArcRequest(BaseModel):
    """Request model for drawing an arc."""

    center: Tuple[float, float] | Tuple[float, float, float]
    radius: float = Field(gt=0)
    start_angle: float = Field(
        ge=0, lt=360, description="Start angle in degrees (0-360)"
    )
    end_angle: float = Field(ge=0, lt=360, description="End angle in degrees (0-360)")
    layer: str = "0"
    color: Union[str, int] = "white"
    lineweight: int = 25

    @model_validator(mode="after")
    def validate_all(self) -> "DrawArcRequest":
        """Validate all fields."""
        CoordinateModel.from_tuple(self.center)
        ColorValidator(color=self.color)
        LayerValidator(layer=self.layer)
        LineWeightValidator(lineweight=self.lineweight)

        # Validate angles
        if self.start_angle == self.end_angle:
            raise ValueError("Start and end angles cannot be equal")

        return self


class DrawRectangleRequest(BaseModel):
    """Request model for drawing a rectangle."""

    corner1: Tuple[float, float] | Tuple[float, float, float]
    corner2: Tuple[float, float] | Tuple[float, float, float]
    layer: str = "0"
    color: Union[str, int] = "white"
    lineweight: int = 25

    @model_validator(mode="after")
    def validate_all(self) -> "DrawRectangleRequest":
        """Validate all fields."""
        c1 = CoordinateModel.from_tuple(self.corner1)
        c2 = CoordinateModel.from_tuple(self.corner2)

        # Ensure corners are different
        if c1.x == c2.x or c1.y == c2.y:
            raise ValueError(
                "Rectangle corners must form a valid rectangle (different x and y)"
            )

        ColorValidator(color=self.color)
        LayerValidator(layer=self.layer)
        LineWeightValidator(lineweight=self.lineweight)
        return self


class DrawPolylineRequest(BaseModel):
    """Request model for drawing a polyline."""

    points: List[Tuple[float, float] | Tuple[float, float, float]] = Field(min_length=2)
    closed: bool = False
    layer: str = "0"
    color: Union[str, int] = "white"
    lineweight: int = 25

    @model_validator(mode="after")
    def validate_all(self) -> "DrawPolylineRequest":
        """Validate all fields."""
        # Validate all points
        for point in self.points:
            CoordinateModel.from_tuple(point)

        ColorValidator(color=self.color)
        LayerValidator(layer=self.layer)
        LineWeightValidator(lineweight=self.lineweight)
        return self


class DrawTextRequest(BaseModel):
    """Request model for drawing text."""

    text: str = Field(min_length=1)
    position: Tuple[float, float] | Tuple[float, float, float]
    height: float = Field(gt=0, default=2.5)
    rotation: float = Field(ge=0, lt=360, default=0.0)
    layer: str = "0"
    color: Union[str, int] = "white"

    @model_validator(mode="after")
    def validate_all(self) -> "DrawTextRequest":
        """Validate all fields."""
        CoordinateModel.from_tuple(self.position)
        ColorValidator(color=self.color)
        LayerValidator(layer=self.layer)
        return self


class DrawSplineRequest(BaseModel):
    """Request model for drawing a spline curve."""

    points: List[Tuple[float, float] | Tuple[float, float, float]] = Field(min_length=2)
    closed: bool = False
    degree: int = Field(default=3, ge=1, le=3, description="Spline degree (1-3)")
    layer: str = "0"
    color: Union[str, int] = "white"
    lineweight: int = 25

    @model_validator(mode="after")
    def validate_all(self) -> "DrawSplineRequest":
        """Validate all fields."""
        # Validate all points
        for point in self.points:
            CoordinateModel.from_tuple(point)

        ColorValidator(color=self.color)
        LayerValidator(layer=self.layer)
        LineWeightValidator(lineweight=self.lineweight)
        return self


# ========== Layer Request Models ==========


class CreateLayerRequest(BaseModel):
    """Request model for creating a layer."""

    name: str
    color: Union[str, int] = "white"
    lineweight: int = 25

    @model_validator(mode="after")
    def validate_all(self) -> "CreateLayerRequest":
        """Validate all fields."""
        LayerValidator(layer=self.name)
        ColorValidator(color=self.color)
        LineWeightValidator(lineweight=self.lineweight)
        return self


class ModifyLayerRequest(BaseModel):
    """Request model for modifying a layer."""

    name: str
    color: Optional[Union[str, int]] = None
    lineweight: Optional[int] = None
    on: Optional[bool] = None
    frozen: Optional[bool] = None
    locked: Optional[bool] = None

    @model_validator(mode="after")
    def validate_all(self) -> "ModifyLayerRequest":
        """Validate all fields."""
        LayerValidator(layer=self.name)

        if self.color is not None:
            ColorValidator(color=self.color)

        if self.lineweight is not None:
            LineWeightValidator(lineweight=self.lineweight)

        return self


# ========== Entity Request Models ==========


class EntityHandleValidator(BaseModel):
    """Validates entity handles."""

    handle: str = Field(min_length=1, max_length=16)

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        """Validate entity handle format."""
        v = v.strip().upper()

        # AutoCAD handles are hexadecimal strings
        if not all(c in "0123456789ABCDEF" for c in v):
            raise ValueError(f"Entity handle must be hexadecimal, got '{v}'")

        return v


class MoveEntityRequest(BaseModel):
    """Request model for moving entities."""

    handles: List[str] = Field(min_length=1)
    displacement: Tuple[float, float] | Tuple[float, float, float]

    @model_validator(mode="after")
    def validate_all(self) -> "MoveEntityRequest":
        """Validate all fields."""
        # Validate handles
        for handle in self.handles:
            EntityHandleValidator(handle=handle)

        # Validate displacement
        CoordinateModel.from_tuple(self.displacement)

        return self


class CopyEntityRequest(BaseModel):
    """Request model for copying entities."""

    handles: List[str] = Field(min_length=1)
    displacement: Tuple[float, float] | Tuple[float, float, float]

    @model_validator(mode="after")
    def validate_all(self) -> "CopyEntityRequest":
        """Validate all fields."""
        for handle in self.handles:
            EntityHandleValidator(handle=handle)

        CoordinateModel.from_tuple(self.displacement)

        return self


class RotateEntityRequest(BaseModel):
    """Request model for rotating entities."""

    handles: List[str] = Field(min_length=1)
    base_point: Tuple[float, float] | Tuple[float, float, float]
    angle: float = Field(ge=0, lt=360, description="Rotation angle in degrees")

    @model_validator(mode="after")
    def validate_all(self) -> "RotateEntityRequest":
        """Validate all fields."""
        for handle in self.handles:
            EntityHandleValidator(handle=handle)

        CoordinateModel.from_tuple(self.base_point)

        return self


class ScaleEntityRequest(BaseModel):
    """Request model for scaling entities."""

    handles: List[str] = Field(min_length=1)
    base_point: Tuple[float, float] | Tuple[float, float, float]
    scale_factor: float = Field(gt=0, description="Scale factor must be positive")

    @model_validator(mode="after")
    def validate_all(self) -> "ScaleEntityRequest":
        """Validate all fields."""
        for handle in self.handles:
            EntityHandleValidator(handle=handle)

        CoordinateModel.from_tuple(self.base_point)

        return self


# ========== Drawing Request Models (continued) ==========


class DrawLeaderRequest(BaseModel):
    """Request model for drawing a leader (dimension leader line)."""

    points: List[Tuple[float, float] | Tuple[float, float, float]] = Field(
        min_length=2, description="At least 2 points required for a leader"
    )
    text: Optional[str] = Field(default=None, description="Optional annotation text")
    text_height: float = Field(gt=0, default=2.5, description="Height of annotation text")
    layer: str = "0"
    color: Union[str, int] = "white"
    leader_type: str = Field(
        default="line_with_arrow",
        description="Leader type: line_with_arrow, line_no_arrow, spline_with_arrow, spline_no_arrow",
    )

    @model_validator(mode="after")
    def validate_all(self) -> "DrawLeaderRequest":
        """Validate all fields."""
        # Validate all points
        for point in self.points:
            CoordinateModel.from_tuple(point)

        # Validate color
        ColorValidator(color=self.color)

        # Validate layer
        LayerValidator(layer=self.layer)

        # Validate leader_type
        valid_types = ["line_with_arrow", "line_no_arrow", "spline_with_arrow", "spline_no_arrow"]
        if self.leader_type.lower() not in valid_types:
            raise ValueError(
                f"Invalid leader_type '{self.leader_type}'. Must be one of: {valid_types}"
            )

        return self


class DrawMLeaderRequest(BaseModel):
    """Request model for drawing a multi-leader (multiple arrow leaders)."""

    base_point: Tuple[float, float] | Tuple[float, float, float] = Field(
        description="Base point for the multi-leader annotation"
    )
    leader_groups: List[List[Tuple[float, float] | Tuple[float, float, float]]] = Field(
        min_length=1, description="List of leader line point groups (minimum 1 line, each with 2+ points)"
    )
    text: Optional[str] = Field(default=None, description="Optional annotation text")
    text_height: float = Field(gt=0, default=2.5, description="Height of annotation text")
    layer: str = "0"
    color: Union[str, int] = "white"
    arrow_style: str = Field(
        default="_ARROW",
        description="Arrow head style: _ARROW, _DOT, _CLOSED_FILLED, etc.",
    )

    @model_validator(mode="after")
    def validate_all(self) -> "DrawMLeaderRequest":
        """Validate all fields."""
        # Validate base point
        CoordinateModel.from_tuple(self.base_point)

        # Validate each leader group has at least 2 points
        for i, group in enumerate(self.leader_groups):
            if len(group) < 2:
                raise ValueError(
                    f"Leader group {i} has {len(group)} points, minimum 2 required"
                )
            for point in group:
                CoordinateModel.from_tuple(point)

        # Validate color
        ColorValidator(color=self.color)

        # Validate layer
        LayerValidator(layer=self.layer)

        return self
