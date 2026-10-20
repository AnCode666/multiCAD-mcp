"""
CAD Adapter management and caching.

Handles:
- Adapter resolution (which CAD to use)
- Adapter caching and reuse
- Active CAD type tracking
- Lazy connection on first use
"""

import logging
import threading
from typing import Optional, Dict, Any

from core import CADConnectionError

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Singleton registry for managing CAD adapter instances.

    Encapsulates global state for adapter caching and active CAD tracking.
    Thread-safe with locks for concurrent access.
    """

    _instance: Optional["AdapterRegistry"] = None
    _lock = threading.Lock()  # Class-level lock for singleton instantiation

    def __init__(self):
        """Initialize the registry with empty state."""
        # Single active adapter instance
        self._adapter: Optional[Any] = None
        # Currently active CAD type name (e.g., "zwcad")
        self._cad_type: Optional[str] = None
        # Instance-level lock for mutations
        self._instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AdapterRegistry":
        """Return the singleton AdapterRegistry instance, creating it if necessary.

        Thread-safe via double-checked locking.

        Returns:
            The singleton AdapterRegistry instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton instance, forcing re-creation on next access.

        Primarily used in tests to reset state between test cases.
        """
        cls._instance = None

    def get_cad_type(self) -> str:
        """Get the currently active CAD type name, or 'None' if disconnected."""
        return self._cad_type or "None"

    def get_adapter(self, only_if_running: bool = False) -> Any:
        """
        Get the active CAD adapter instance. Auto-detects if none exists.

        Args:
            only_if_running: If True, fails if CAD is not already open.

        Returns:
            CAD adapter instance

        Raises:
            CADConnectionError: If adapter cannot be created or connected
        """
        with self._instance_lock:
            if self._adapter is not None:
                # We already have an adapter. Let's make sure it's connected.
                if self._adapter.is_connected():
                    return self._adapter

                # It exists but is disconnected. Try to reconnect.
                if self._adapter.connect(only_if_running=only_if_running):
                    return self._adapter

                if only_if_running:
                    raise CADConnectionError(
                        self._cad_type or "cad", "CAD application is not running"
                    )

            # No working adapter exists. We must auto-detect.
            self._auto_detect_internal(only_if_running=only_if_running)

            if self._adapter is not None and self._adapter.is_connected():
                return self._adapter

            raise CADConnectionError(
                "cad", "Could not connect to any supported CAD application"
            )

    def _auto_detect_internal(self, only_if_running: bool = False) -> None:
        """Internal auto-detection logic within the locked context."""
        from adapters import AutoCADAdapter

        cad_priorities = ["zwcad", "autocad", "bricscad", "gcad"]

        for ct in cad_priorities:
            try:
                logger.info(
                    f"Auto-detecting {ct} (only_if_running={only_if_running})..."
                )
                adapter = AutoCADAdapter(ct)
                if adapter.connect(only_if_running=only_if_running):
                    self._adapter = adapter
                    self._cad_type = ct
                    logger.info(f"Auto-detected: {ct} is available and active")
                    return
            except Exception as e:
                logger.debug(f"{ct} not available: {e}")
                continue

        # Headless DXF fallback when no GUI CAD is active
        if not only_if_running:
            try:
                from adapters.ezdxf_adapter import EzdxfAdapter

                dxf_adapter = EzdxfAdapter()
                if dxf_adapter.connect():
                    self._adapter = dxf_adapter
                    self._cad_type = "dxf"
                    logger.info("Auto-detected fallback: Headless DXF (ezdxf) active")
                    return
            except Exception as e:
                logger.debug(f"ezdxf headless fallback not available: {e}")

    def set_adapter(self, adapter: Any, cad_type: str = "dxf") -> None:
        """Manually set the active adapter instance (e.g. for headless DXF or testing)."""
        with self._instance_lock:
            self._adapter = adapter
            self._cad_type = cad_type

    def get_cad_instances(self) -> Dict[str, Any]:
        """
        Get the dictionary of all CAD adapter instances.

        Returns:
            Dictionary mapping CAD type to adapter instance
        """
        if self._adapter and self._adapter.is_connected() and self._cad_type:
            return {self._cad_type: self._adapter}
        return {}

    def auto_detect_cad(self, only_if_running: bool = False) -> None:
        """
        Auto-detect and connect to available CAD applications on startup (thread-safe).
        """
        with self._instance_lock:
            self._auto_detect_internal(only_if_running=only_if_running)
            if self._adapter is None:
                logger.warning(
                    "No CAD application detected. Will attempt to connect on first use."
                )

    def shutdown_all(self) -> None:
        """
        Disconnect and cleanup all CAD adapter instances (thread-safe).
        """
        with self._instance_lock:
            if self._adapter is not None:
                try:
                    if self._adapter.is_connected():
                        logger.info(f"Disconnecting {self._cad_type}...")
                        self._adapter.disconnect()
                        logger.info(f"Disconnected {self._cad_type}")
                except Exception as e:
                    logger.error(f"Error disconnecting {self._cad_type}: {e}")

            self._adapter = None
            self._cad_type = None
            logger.info("All adapters shutdown successfully")


# Singleton instance
_registry = AdapterRegistry.get_instance()


# Module-level convenience functions
def get_active_cad_type() -> str:
    """Return the currently active CAD type."""
    return _registry.get_cad_type()


def set_active_cad_type(cad_type: Optional[str]) -> None:
    """Convenience function - stubbed out for backwards compatibility."""
    raise NotImplementedError("Setting active CAD type manually is not supported.")


def get_adapter(cad_type: Optional[str] = None, only_if_running: bool = False) -> Any:
    """Convenience function - delegates to singleton registry."""
    return _registry.get_adapter(only_if_running=only_if_running)


def get_cad_instances() -> Dict[str, Any]:
    """Convenience function - delegates to singleton registry."""
    return _registry.get_cad_instances()


def auto_detect_cad(only_if_running: bool = False) -> None:
    """Convenience function - delegates to singleton registry."""
    _registry.auto_detect_cad(only_if_running=only_if_running)


def shutdown_all() -> None:
    """Convenience function - delegates to singleton registry."""
    _registry.shutdown_all()
