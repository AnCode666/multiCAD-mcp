"""
Connection mixin for AutoCAD adapter.

Handles connection, disconnection, and validation methods.
"""

import logging
import sys
from typing import TYPE_CHECKING, Any

if sys.platform == "win32":
    import win32com.client
    import pythoncom
    import pywintypes
else:
    raise ImportError("AutoCAD adapter requires Windows OS with COM support")

from core import CADConnectionError

if TYPE_CHECKING:
    from core.config import CADConfig

logger = logging.getLogger(__name__)


class ConnectionMixin:
    """Mixin for connection management."""

    if TYPE_CHECKING:
        # Tell type checker this mixin is used with CADAdapterProtocol
        cad_type: str
        config: "CADConfig"
        application: Any
        document: Any

        def _wait_for(
            self, condition: Any, timeout: float = 20.0, interval: float = 0.1
        ) -> bool: ...

    def connect(self) -> bool:
        """Connect to CAD application with COM initialization (thread-safe)."""
        try:
            logger.info(f"Connecting to {self.cad_type}...")

            # Initialize COM for this thread
            # CoInitialize() may raise if already initialized, which is fine
            try:
                pythoncom.CoInitialize()
            except Exception as e:
                logger.debug(f"CoInitialize: {e} (may already be initialized for thread)")

            # Try to get existing instance
            try:
                self.application = win32com.client.GetActiveObject(self.config.prog_id)
                logger.info(f"{self.cad_type} instance found (active)")
            except Exception:
                # Start new instance
                logger.info(f"{self.cad_type} not running, starting new instance...")
                try:
                    self.application = win32com.client.Dispatch(self.config.prog_id)
                except pywintypes.com_error as com_err:
                    error_code = com_err.args[0] if com_err.args else None
                    if error_code == -2147221005:
                        error_msg = (
                            f"Invalid ProgID '{self.config.prog_id}'. "
                            f"Either {self.cad_type.upper()} is not installed or the ProgID is incorrect. "
                            f"Check config.json and ensure the application is installed."
                        )
                    else:
                        error_msg = str(com_err)
                    logger.error(
                        f"Failed to create {self.cad_type} instance: {error_msg}"
                    )
                    raise CADConnectionError(self.cad_type, error_msg)

                if self.application is not None:
                    # Try to make application visible (not all CAD types support this)
                    try:
                        self.application.Visible = True
                    except (pywintypes.com_error, AttributeError) as e:
                        logger.debug(
                            f"{self.cad_type} doesn't support Visible property or it's read-only: {e}"
                        )
                self._wait_for(
                    lambda: self.application is not None,
                    timeout=self.config.startup_wait_time,
                )
                logger.info(
                    f"New {self.cad_type} instance started "
                    f"(waited {self.config.startup_wait_time}s)"
                )

            # Get active document or create new
            if self.application is not None:
                # Standard AutoCAD/ZWCAD/BricsCAD/GstarCAD handling
                if self.application.Documents.Count > 0:
                    self.document = self.application.ActiveDocument
                    logger.info("Using existing active document")
                else:
                    self.document = self.application.Documents.Add()
                    logger.info("Created new document")

            # Validate connection
            if not self._validate_document():
                raise CADConnectionError(self.cad_type, "Document validation failed")

            logger.info(f"✓ Successfully connected to {self.cad_type}")
            return True

        except pywintypes.com_error as e:
            error_msg = f"COM error: {str(e)}"
            logger.error(f"Failed to connect to {self.cad_type}: {error_msg}")
            raise CADConnectionError(self.cad_type, error_msg)
        except Exception as e:
            logger.error(f"Failed to connect to {self.cad_type}: {e}")
            raise CADConnectionError(self.cad_type, str(e))

    def disconnect(self) -> bool:
        """Disconnect from CAD application with COM cleanup."""
        try:
            if self.application:
                self.application = None
                self.document = None
            pythoncom.CoUninitialize()
            logger.info(f"Disconnected from {self.cad_type}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False

    def __enter__(self):
        """Enter context: connect to CAD application.

        Allows using the adapter as a context manager:
            with AutoCADAdapter("autocad") as adapter:
                adapter.draw_line((0,0), (10,10))
                # Auto-disconnect on exit

        Returns:
            Self (the adapter instance)

        Raises:
            CADConnectionError: If connection fails
        """
        if not self.connect():
            raise CADConnectionError(
                self.cad_type, "Connection failed during context manager initialization"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context: disconnect from CAD application.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        self.disconnect()

    def is_connected(self) -> bool:
        """Check if connected to CAD application."""
        try:
            return (
                self.application is not None
                and self.document is not None
                and self._validate_document()
            )
        except Exception:
            return False

    def _validate_document(self) -> bool:
        """Validate that document is accessible."""
        try:
            if self.document is None:
                return False
            _ = self.document.Name
            return True
        except Exception:
            return False
