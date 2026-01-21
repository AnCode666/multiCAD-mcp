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

from core import CADConnectionError

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Singleton registry for managing CAD adapter instances.

    Encapsulates global state for adapter caching and active CAD tracking.
    """

    _instance: Optional["AdapterRegistry"] = None

    def __init__(self):
        """Initialize the registry with empty state."""
        # Cache of adapter instances
        self._cad_instances: Dict[str, Any] = {}
        # Currently active CAD type
        self._active_cad_type: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "AdapterRegistry":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def get_active_cad_type(self, requested_cad_type: Optional[str] = None) -> str:
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
        if requested_cad_type:
            return requested_cad_type.lower()

        if self._active_cad_type and self._active_cad_type in self._cad_instances:
            active_adapter = self._cad_instances[self._active_cad_type]
            if active_adapter.is_connected():
                return self._active_cad_type

        for cad_type, adapter in self._cad_instances.items():
            if adapter.is_connected():
                self._active_cad_type = cad_type
                return cad_type

        return "autocad"

    def set_active_cad_type(self, cad_type: Optional[str]) -> None:
        """Set the active CAD type explicitly.

        Args:
            cad_type: CAD type to set as active
        """
        if cad_type:
            self._active_cad_type = cad_type.lower()

    def get_adapter(self, cad_type: Optional[str] = None) -> Any:
        """
        Get or create a CAD adapter instance (cached).

        Args:
            cad_type: Type of CAD to use. If None, uses the active CAD type.

        Returns:
            CAD adapter instance

        Raises:
            CADConnectionError: If adapter cannot be created or connected
        """
        # Lazy import to avoid circular dependency
        from adapters import AutoCADAdapter

        resolved_cad_type = self.get_active_cad_type(cad_type)

        if resolved_cad_type in self._cad_instances:
            adapter = self._cad_instances[resolved_cad_type]
            if adapter.is_connected():
                self.set_active_cad_type(resolved_cad_type)
                return adapter

        try:
            adapter = AutoCADAdapter(resolved_cad_type)
            adapter.connect()
            self._cad_instances[resolved_cad_type] = adapter
            self.set_active_cad_type(resolved_cad_type)
            return adapter
        except Exception as e:
            raise CADConnectionError(resolved_cad_type, str(e))

    def get_cad_instances(self) -> Dict[str, Any]:
        """
        Get the dictionary of all CAD adapter instances.

        Returns:
            Dictionary mapping CAD type to adapter instance
        """
        return self._cad_instances

    def auto_detect_cad(self) -> None:
        """
        Auto-detect and connect to available CAD applications on startup.

        Tries CAD types in order: zwcad, autocad, bricscad, gcad
        Sets the first available as the active CAD type.
        """
        # Lazy import to avoid circular dependency
        from adapters import AutoCADAdapter

        cad_priorities = ["zwcad", "autocad", "bricscad", "gcad"]

        for cad_type in cad_priorities:
            try:
                logger.info(f"Auto-detecting {cad_type}...")
                adapter = AutoCADAdapter(cad_type)
                adapter.connect()
                self._cad_instances[cad_type] = adapter
                self._active_cad_type = cad_type
                logger.info(f"Auto-detected: {cad_type} is available and active")
                return
            except Exception as e:
                logger.debug(f"{cad_type} not available: {e}")
                continue

        logger.warning(
            "No CAD application detected. " "Will attempt to connect on first use."
        )

    def shutdown_all(self) -> None:
        """
        Disconnect and cleanup all CAD adapter instances.

        Safely disconnects all active adapters and clears the registry.
        Useful for graceful shutdown or testing cleanup.
        """
        for cad_type, adapter in list(self._cad_instances.items()):
            try:
                if adapter.is_connected():
                    logger.info(f"Disconnecting {cad_type}...")
                    adapter.disconnect()
                    logger.info(f"Disconnected {cad_type}")
            except Exception as e:
                logger.error(f"Error disconnecting {cad_type}: {e}")

        self._cad_instances.clear()
        self._active_cad_type = None
        logger.info("All adapters shutdown successfully")


# Singleton instance
_registry = AdapterRegistry.get_instance()


# Module-level convenience functions for backward compatibility
def get_active_cad_type(requested_cad_type: Optional[str] = None) -> str:
    """Convenience function - delegates to singleton registry."""
    return _registry.get_active_cad_type(requested_cad_type)


def set_active_cad_type(cad_type: Optional[str]) -> None:
    """Convenience function - delegates to singleton registry."""
    _registry.set_active_cad_type(cad_type)


def get_adapter(cad_type: Optional[str] = None) -> Any:
    """Convenience function - delegates to singleton registry."""
    return _registry.get_adapter(cad_type)


def get_cad_instances() -> Dict[str, Any]:
    """Convenience function - delegates to singleton registry."""
    return _registry.get_cad_instances()


def auto_detect_cad() -> None:
    """Convenience function - delegates to singleton registry."""
    _registry.auto_detect_cad()


def shutdown_all() -> None:
    """Convenience function - delegates to singleton registry."""
    _registry.shutdown_all()
