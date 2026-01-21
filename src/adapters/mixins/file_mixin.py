"""
File mixin for AutoCAD adapter.

Handles file operations (save, open, close, new, switch).
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core import CADOperationError, get_config

logger = logging.getLogger(__name__)


class FileMixin:
    """Mixin for file operations."""

    if TYPE_CHECKING:
        document: Any

        def _get_document(self, operation: str = "operation") -> Any: ...
        def _get_application(self, operation: str = "operation") -> Any: ...
        def _validate_document(self) -> bool: ...

    def save_drawing(
        self, filepath: str = "", filename: str = "", format: str = "dwg"
    ) -> bool:
        """Save drawing to file.

        Args:
            filepath: Full path to save file (e.g., 'C:/drawings/myfile.dwg')
            filename: Just the filename (e.g., 'myfile.dwg'). If provided without
                     filepath, uses configured output directory
            format: File format (dwg, dxf, etc.). Default: dwg

        Returns:
            bool: True if successful, False otherwise

        Note:
            - If both filepath and filename provided, filepath takes precedence
            - If only filename provided, saved to config output directory
            - If neither provided, uses current document name
        """
        try:
            document = self._get_document("save_drawing")
            config = get_config()

            # SECURITY: Resolve output directory first (reference for validation)
            output_dir = Path(config.output.directory).expanduser().resolve()

            # ========== Determine Directory (filepath) ==========
            if filepath:
                # If filepath provided, extract directory part
                dir_part = str(Path(filepath).parent)
                if dir_part and dir_part != ".":
                    save_dir = dir_part
                else:
                    save_dir = str(output_dir)
            else:
                save_dir = str(output_dir)

            # Convert to absolute path (required by AutoCAD COM API)
            save_dir_path = Path(save_dir).expanduser().resolve()

            # SECURITY: Verify the directory is within the configured output directory
            try:
                save_dir_path.relative_to(output_dir)
            except ValueError:
                logger.error(
                    f"Security: Attempted to save outside output directory. "
                    f"Requested: {save_dir_path}, Allowed: {output_dir}"
                )
                raise CADOperationError(
                    "save_drawing",
                    f"File path must be within {output_dir}",
                )

            # Create directory if it doesn't exist
            save_dir_path.mkdir(parents=True, exist_ok=True)

            # ========== Determine Filename ==========
            if filepath:
                file_part = str(Path(filepath).name)
                if file_part and file_part != ".":
                    save_filename = file_part
                elif filename:
                    save_filename = filename
                else:
                    save_filename = None
            else:
                save_filename = filename

            # If still no filename, use document name or generate one
            if not save_filename:
                if document.Name:
                    save_filename = document.Name
                else:
                    from datetime import datetime

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_filename = f"drawing_{timestamp}.{format}"

            # ========== Ensure Correct File Extension ==========
            if not save_filename.lower().endswith(f".{format}"):
                save_filename = f"{save_filename}.{format}"

            # ========== Combine Directory + Filename ==========
            final_path = save_dir_path / save_filename

            # SECURITY: Final validation - ensure combined path is still within output directory
            try:
                final_path.resolve().relative_to(output_dir)
            except ValueError:
                logger.error(
                    f"Security: Final path validation failed. "
                    f"Path: {final_path}, Allowed dir: {output_dir}"
                )
                raise CADOperationError(
                    "save_drawing",
                    f"Invalid file path: {final_path}",
                )

            # Save the drawing
            document.SaveAs(str(final_path))
            logger.info(f"Saved drawing to {final_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save drawing: {e}")
            return False

    def open_drawing(self, filepath: str) -> bool:
        """Open a drawing file."""
        try:
            application = self._get_application("open_drawing")
            self.document = application.Documents.Open(filepath)
            logger.info(f"Opened drawing from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to open drawing: {e}")
            return False

    def new_drawing(self) -> bool:
        """Create new blank drawing."""
        try:
            application = self._get_application("new_drawing")
            self.document = application.Documents.Add()
            self._refresh_document_reference()
            logger.info("Created new blank drawing")
            return True
        except Exception as e:
            logger.error(f"Failed to create new drawing: {e}")
            return False

    def _refresh_document_reference(self, auto_create: bool = True) -> bool:
        """Refresh internal document reference to ActiveDocument.

        This ensures self.document always points to the active document
        in the application. Useful after creating or switching documents.

        Args:
            auto_create: If True and no documents open, create a new one (default: True)

        Returns:
            True if successful, False otherwise
        """
        try:
            application = self._get_application("_refresh_document_reference")

            # Case 1: Documents are open, use the active one
            if application.Documents.Count > 0:
                self.document = application.ActiveDocument
                if self.document is not None:
                    logger.debug(f"Document reference refreshed: {self.document.Name}")
                return True

            # Case 2: No documents open
            if auto_create:
                logger.warning("No documents open. Creating a new blank document...")
                self.document = application.Documents.Add()
                if self.document is not None:
                    logger.info(f"Auto-created new document: {self.document.Name}")
                return True
            else:
                logger.warning("No documents open")
                return False

        except Exception as e:
            logger.error(f"Failed to refresh document reference: {e}")
            return False

    def get_open_drawings(self) -> list:
        """Get list of all open drawing filenames.

        Returns:
            List of drawing names (e.g., ["drawing1.dwg", "drawing2.dwg"])
        """
        try:
            application = self._get_application("get_open_drawings")
            drawings = []

            # Use direct iteration instead of Item indexing
            for doc in application.Documents:
                drawings.append(doc.Name)

            logger.info(f"Found {len(drawings)} open drawings: {drawings}")
            return drawings
        except Exception as e:
            logger.error(f"Failed to get open drawings: {e}")
            return []

    def switch_drawing(self, drawing_name: str) -> bool:
        """Switch to a different open drawing.

        Args:
            drawing_name: Name of the drawing to switch to (e.g., "drawing1.dwg")

        Returns:
            True if successful, False otherwise
        """
        try:
            application = self._get_application("switch_drawing")

            # Use direct iteration instead of Item indexing
            for doc in application.Documents:
                if doc.Name == drawing_name:
                    doc.Activate()
                    self.document = doc
                    logger.info(f"Switched to drawing: {drawing_name}")
                    return True

            logger.warning(f"Drawing not found: '{drawing_name}'")
            return False

        except Exception as e:
            logger.error(f"Failed to switch drawing: {e}")
            return False

    def close_drawing(self, save_changes: bool = False) -> bool:
        """Close the current drawing.

        Args:
            save_changes: Whether to save changes before closing (default: False)
                         True = save changes
                         False = discard changes without prompting

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._validate_document() or self.document is None:
                logger.warning("No document to close")
                return False

            document = self.document
            doc_name = document.Name

            # Close document using COM API
            document.Close(save_changes)

            # Try to update connection to remaining open document
            refresh_success = self._refresh_document_reference(auto_create=False)

            if refresh_success and self.document is not None:
                logger.info(
                    f"Closed drawing: {doc_name} (save_changes={save_changes}). "
                    f"Switched to: {self.document.Name}"
                )
            else:
                # No other documents open - attempt to create one to maintain connection
                logger.warning(
                    f"No other documents open after closing {doc_name}. "
                    "Attempting to create a new blank document..."
                )
                try:
                    application = self._get_application("close_drawing_reconnect")
                    self.document = application.Documents.Add()
                    logger.info(
                        f"Closed drawing: {doc_name} (save_changes={save_changes}). "
                        f"Created new document: {self.document.Name}"
                    )
                except Exception as e:
                    self.document = None
                    logger.info(
                        f"Closed drawing: {doc_name} (save_changes={save_changes}). "
                        "Could not create new document."
                    )
                    logger.debug(f"Auto-create error: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to close drawing: {e}")
            return False
