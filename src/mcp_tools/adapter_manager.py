"""
CAD Adapter management and caching.

Handles:
- Adapter resolution (which CAD to use)
- Adapter caching and reuse
- Active CAD type tracking
- Lazy connection on first use
"""

import logging
from typing import Optional, Dict, Any
from functools import lru_cache

from core import CADConnectionError
from adapters import create_adapter

logger = logging.getLogger(__name__)

# Global state
_cad_instances: Dict[str, Any] = {}  # Cache of adapter instances
_active_cad_type: Optional[str] = None  # Currently active CAD type


def get_active_cad_type(requested_cad_type: Optional[str] = None) -> str:
    """
    Determine which CAD type to use.

    Priority:
    1. Explicitly requested CAD type
    2. Previously set active CAD type
    3. First connected CAD type
    4. AutoCAD (default)

    Args:
        requested_cad_type: Explicitly requested CAD type (overrides all)

    Returns:
        CAD type to use
    """
    global _active_cad_type

    if requested_cad_type:
        return requested_cad_type.lower()

    if _active_cad_type and _active_cad_type in _cad_instances:
        if _cad_instances[_active_cad_type].is_connected():
            return _active_cad_type

    for cad_type, adapter in _cad_instances.items():
        if adapter.is_connected():
            _active_cad_type = cad_type
            return cad_type

    return "autocad"


def set_active_cad_type(cad_type: Optional[str]) -> None:
    """Set the active CAD type explicitly.

    Args:
        cad_type: CAD type to set as active
    """
    global _active_cad_type
    if cad_type:
        _active_cad_type = cad_type.lower()


@lru_cache(maxsize=4)
def get_adapter(cad_type: Optional[str] = None) -> Any:
    """
    Get or create a CAD adapter instance (cached).

    Args:
        cad_type: Type of CAD to use. If None, uses the active CAD type.

    Returns:
        CAD adapter instance

    Raises:
        CADConnectionError: If adapter cannot be created or connected
    """
    resolved_cad_type = get_active_cad_type(cad_type)

    if resolved_cad_type in _cad_instances:
        adapter = _cad_instances[resolved_cad_type]
        if adapter.is_connected():
            set_active_cad_type(resolved_cad_type)
            return adapter

    try:
        adapter = create_adapter(resolved_cad_type)
        adapter.connect()
        _cad_instances[resolved_cad_type] = adapter
        set_active_cad_type(resolved_cad_type)
        return adapter
    except Exception as e:
        raise CADConnectionError(resolved_cad_type, str(e))


def get_cad_instances() -> Dict[str, Any]:
    """
    Get the dictionary of all CAD adapter instances.

    Returns:
        Dictionary mapping CAD type to adapter instance
    """
    return _cad_instances


def auto_detect_cad() -> None:
    """
    Auto-detect and connect to available CAD applications on startup.

    Tries CAD types in order: zwcad, autocad, bricscad, gcad
    Sets the first available as the active CAD type.
    """
    global _active_cad_type

    cad_priorities = ["zwcad", "autocad", "bricscad", "gcad"]

    for cad_type in cad_priorities:
        try:
            logger.info(f"Auto-detecting {cad_type}...")
            adapter = create_adapter(cad_type)
            adapter.connect()
            _cad_instances[cad_type] = adapter
            _active_cad_type = cad_type
            logger.info(f"Auto-detected: {cad_type} is available and active")
            return
        except Exception as e:
            logger.debug(f"{cad_type} not available: {e}")
            continue

    logger.warning("No CAD application detected. Will attempt to connect on first use.")
