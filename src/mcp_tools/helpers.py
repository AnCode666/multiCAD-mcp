"""
Helper functions for server initialization and utilities.

Includes:
- UTF-8 encoding setup
- Logging configuration
- Coordinate parsing
- Handle parsing
- Message formatting
"""

import logging
import sys
import os
import re

from core import get_config, InvalidParameterError

# ========== Setup Functions ==========


def setup_utf8_encoding() -> None:
    """Configure UTF-8 encoding on Windows."""
    if sys.platform == "win32" and os.environ.get("PYTHONIOENCODING") is None:
        try:
            sys.stdin.reconfigure(encoding="utf-8")  # type: ignore
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore
        except AttributeError:
            pass


def setup_logging() -> logging.Logger:
    """Configure logging based on config.json."""
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "multicad_mcp.log")

    config = get_config()
    log_level = getattr(logging, config.logging_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    return logging.getLogger(__name__)


# ========== Parsing Functions ==========

# Precompiled regex for coordinate parsing
_COORD_PATTERN = re.compile(r"(-?\d+\.?\d*)")


def parse_coordinate(coord_str: str) -> tuple:
    """
    Parse coordinate string like "x,y" or "x,y,z" to tuple.
    Uses precompiled regex for efficiency.

    Args:
        coord_str: Coordinate string

    Returns:
        Tuple of floats

    Raises:
        InvalidParameterError: If coordinate cannot be parsed
    """
    matches = _COORD_PATTERN.findall(coord_str)

    if len(matches) < 2:
        raise InvalidParameterError(
            "coordinate", coord_str, "format like '10,20' or '10,20,30'"
        )

    return tuple(float(m) for m in matches[:3])


def parse_handles(handles_str: str) -> list[str]:
    """
    Parse comma-separated handle string to list.

    Args:
        handles_str: Comma-separated handles (e.g., "h1,h2,h3")

    Returns:
        List of handles with whitespace stripped
    """
    return [h.strip() for h in handles_str.split(",") if h.strip()]


# ========== Message Formatting ==========


def result_message(action: str, success: bool, detail: str = "") -> str:
    """
    Generate consistent success/failure messages.

    Args:
        action: Action name (e.g., "create layer", "move entities")
        success: Whether operation succeeded
        detail: Additional detail to append

    Returns:
        Formatted message
    """
    if success:
        if detail:
            return f"{action.capitalize()} successful: {detail}"
        return f"{action.capitalize()} successful"
    return f"Failed to {action}"
