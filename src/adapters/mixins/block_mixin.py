"""
Block mixin for AutoCAD adapter.

Handles block creation and management operations.
"""

import logging
import math
from typing import List, Any, Dict, TYPE_CHECKING

from core import CADInterface, CADOperationError, InvalidParameterError, Coordinate

if TYPE_CHECKING:
    from core import Point

logger = logging.getLogger(__name__)


class BlockMixin:
    """Mixin for block operations."""

    if TYPE_CHECKING:

        def _validate_connection(self) -> None: ...

        def _get_application(self, operation: str = "operation") -> Any: ...

        def _get_document(self, operation: str = "operation") -> Any: ...

        def _to_variant_array(self, point: Point) -> Any: ...

        def _objects_to_variant_array(self, objects: List[Any]) -> Any: ...

        def _to_radians(self, degrees: float) -> float: ...

        def _track_entity(self, entity: Any, entity_type: str) -> None: ...

        def _safe_get_property(
            self, obj: Any, property_name: str, default: Any = None
        ) -> Any: ...

        def refresh_view(self) -> None: ...

    def create_block_from_entities(
        self,
        block_name: str,
        entity_handles: List[str],
        insertion_point: Coordinate = (0.0, 0.0, 0.0),
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a block from specified entities.

        Args:
            block_name: Name for the new block
            entity_handles: List of entity handles to include in block
            insertion_point: Base point for block definition (default: 0,0,0)
            description: Optional block description

        Returns:
            Dictionary with operation status and details

        Raises:
            CADOperationError: If block creation fails
            InvalidParameterError: If parameters are invalid
        """
        try:
            self._validate_connection()
            app = self._get_application("create_block_from_entities")
            document = app.ActiveDocument

            # Validate block name
            if not block_name or not isinstance(block_name, str):
                raise InvalidParameterError(
                    "block_name", block_name, "Block name must be a non-empty string"
                )

            # Check if block already exists
            try:
                _ = document.Blocks.Item(block_name)
                # If we get here, block exists
                raise CADOperationError(
                    "create_block",
                    f"Block '{block_name}' already exists. Choose a different name.",
                )
            except CADOperationError:
                # Re-raise our error
                raise
            except Exception:
                # Block doesn't exist (Item() raised exception), continue
                pass

            # Convert insertion point
            insert_pt = CADInterface.normalize_coordinate(insertion_point)
            insert_pt_variant = self._to_variant_array(insert_pt)

            # Create block definition
            block_def = document.Blocks.Add(insert_pt_variant, block_name)

            # Set description if provided
            if description:
                try:
                    block_def.Comments = description
                except Exception as e:
                    logger.warning(f"Could not set block description: {e}")

            # Get entities from handles
            entities = []
            failed_handles = []
            for handle in entity_handles:
                try:
                    entity = document.HandleToObject(handle)
                    entities.append(entity)
                except Exception as e:
                    logger.warning(f"Could not get entity with handle {handle}: {e}")
                    failed_handles.append(handle)

            if not entities:
                raise CADOperationError(
                    "create_block",
                    f"No valid entities found from {len(entity_handles)} handles provided",
                )

            # Convert entities to variant array
            entities_variant = self._objects_to_variant_array(entities)

            # Copy entities to block definition
            try:
                document.CopyObjects(entities_variant, block_def)
            except Exception as e:
                raise CADOperationError(
                    "create_block",
                    f"Failed to copy entities to block: {str(e)}",
                )

            logger.info(
                f"Created block '{block_name}' with {len(entities)} entities "
                f"at insertion point {insert_pt}"
            )

            return {
                "success": True,
                "block_name": block_name,
                "total_handles": len(entity_handles),
                "entities_added": len(entities),
                "failed_handles": failed_handles,
                "insertion_point": insert_pt,
            }

        except (CADOperationError, InvalidParameterError):
            raise
        except Exception as e:
            logger.error(f"Failed to create block from entities: {e}")
            raise CADOperationError("create_block", str(e))

    def create_block_from_selection(
        self,
        block_name: str,
        insertion_point: Coordinate = (0.0, 0.0, 0.0),
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a block from currently selected entities.

        Args:
            block_name: Name for the new block
            insertion_point: Base point for block definition (default: 0,0,0)
            description: Optional block description

        Returns:
            Dictionary with operation status and details

        Raises:
            CADOperationError: If block creation fails or no entities selected
            InvalidParameterError: If parameters are invalid
        """
        try:
            self._validate_connection()
            app = self._get_application("create_block_from_selection")
            document = app.ActiveDocument

            # Validate block name
            if not block_name or not isinstance(block_name, str):
                raise InvalidParameterError(
                    "block_name", block_name, "Block name must be a non-empty string"
                )

            # Check if block already exists
            try:
                _ = document.Blocks.Item(block_name)
                # If we get here, block exists
                raise CADOperationError(
                    "create_block",
                    f"Block '{block_name}' already exists. Choose a different name.",
                )
            except CADOperationError:
                # Re-raise our error
                raise
            except Exception:
                # Block doesn't exist (Item() raised exception), continue
                pass

            # Get currently selected entities
            try:
                selection_set = document.PickfirstSelectionSet
                entity_count = selection_set.Count

                if entity_count == 0:
                    raise CADOperationError(
                        "create_block",
                        "No entities selected. Please select entities in the drawing first.",
                    )

                # Convert selection to list of entities
                entities = []
                for i in range(entity_count):
                    entities.append(selection_set.Item(i))

                logger.debug(f"Retrieved {len(entities)} entities from selection")

            except Exception as e:
                raise CADOperationError(
                    "create_block",
                    f"Failed to get selected entities: {str(e)}",
                )

            # Convert insertion point
            insert_pt = CADInterface.normalize_coordinate(insertion_point)
            insert_pt_variant = self._to_variant_array(insert_pt)

            # Create block definition
            block_def = document.Blocks.Add(insert_pt_variant, block_name)

            # Set description if provided
            if description:
                try:
                    block_def.Comments = description
                except Exception as e:
                    logger.warning(f"Could not set block description: {e}")

            # Convert entities to variant array
            entities_variant = self._objects_to_variant_array(entities)

            # Copy entities to block definition
            try:
                document.CopyObjects(entities_variant, block_def)
            except Exception as e:
                raise CADOperationError(
                    "create_block",
                    f"Failed to copy entities to block: {str(e)}",
                )

            logger.info(
                f"Created block '{block_name}' from {len(entities)} selected entities "
                f"at insertion point {insert_pt}"
            )

            return {
                "success": True,
                "block_name": block_name,
                "entities_added": len(entities),
                "insertion_point": insert_pt,
            }

        except (CADOperationError, InvalidParameterError):
            raise
        except Exception as e:
            logger.error(f"Failed to create block from selection: {e}")
            raise CADOperationError("create_block", str(e))

    def insert_block(
        self,
        block_name: str,
        insertion_point: Coordinate,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        scale_z: float = 1.0,
        rotation: float = 0.0,
        layer: str = "0",
        _skip_refresh: bool = False,
    ) -> str:
        """Insert a block reference in the drawing.

        Args:
            block_name: Name of the block to insert
            insertion_point: Point where to insert the block (x,y) or (x,y,z)
            scale_x: X scale factor (default: 1.0)
            scale_y: Y scale factor (default: 1.0)
            scale_z: Z scale factor (default: 1.0)
            rotation: Rotation angle in degrees (default: 0.0)
            layer: Layer to place the block on (default: "0")
            _skip_refresh: Internal flag to skip view refresh (used for batch operations)

        Returns:
            Handle of the inserted block reference

        Raises:
            CADOperationError: If block doesn't exist or insertion fails
        """
        try:
            document = self._get_document("insert_block")

            # Normalize insertion point to 3D
            point = CADInterface.normalize_coordinate(insertion_point)
            point_array = self._to_variant_array(point)

            # Convert rotation to radians
            rotation_rad = self._to_radians(rotation)

            # Check if block exists
            block_exists = False
            try:
                for block in document.Blocks:
                    if block.Name == block_name:
                        block_exists = True
                        break
            except Exception as e:
                logger.warning(f"Failed to verify block existence: {e}")

            if not block_exists:
                available_blocks = self.list_blocks()
                raise CADOperationError(
                    "insert_block",
                    f"Block '{block_name}' not found. Available blocks: {', '.join(available_blocks)}",
                )

            # Insert the block
            block_ref = document.ModelSpace.InsertBlock(
                point_array,
                block_name,
                scale_x,
                scale_y,
                scale_z,
                rotation_rad,
            )

            # Apply layer property
            if layer != "0":
                try:
                    block_ref.Layer = layer
                except Exception as e:
                    logger.warning(f"Failed to set block layer to '{layer}': {e}")

            self._track_entity(block_ref, "block")

            if not _skip_refresh:
                self.refresh_view()

            logger.info(
                f"Inserted block '{block_name}' at {insertion_point} "
                f"(scale: {scale_x},{scale_y},{scale_z}, rotation: {rotation}°)"
            )
            return str(block_ref.Handle)

        except CADOperationError:
            raise
        except Exception as e:
            logger.error(f"Failed to insert block '{block_name}': {e}")
            raise CADOperationError("insert_block", str(e))

    def list_blocks(self) -> List[str]:
        """Get list of all block definitions in the drawing.

        Returns:
            List of block names (excludes system blocks that start with *)

        Note:
            System blocks (like *Model_Space, *Paper_Space) are filtered out
        """
        try:
            document = self._get_document("list_blocks")
            blocks: List[str] = []

            for block in document.Blocks:
                try:
                    block_name = str(block.Name)
                    # Filter out system blocks (start with *)
                    if not block_name.startswith("*"):
                        blocks.append(block_name)
                except Exception as e:
                    logger.debug(f"Failed to get block name: {e}")
                    continue

            logger.info(f"Found {len(blocks)} blocks in drawing")
            return blocks

        except Exception as e:
            logger.error(f"Failed to list blocks: {e}")
            return []

    def get_block_info(self, block_name: str) -> Dict[str, Any]:
        """Get detailed information about a block definition.

        Args:
            block_name: Name of the block

        Returns:
            Dictionary with block information:
            - Name: Block name
            - Origin: Block insertion base point (x, y, z)
            - ObjectCount: Number of entities in the block
            - IsXRef: Whether the block is an external reference
            - Comments: Block comments/description
        """
        try:
            document = self._get_document("get_block_info")

            # Find the block
            block_obj = None
            for block in document.Blocks:
                if block.Name == block_name:
                    block_obj = block
                    break

            if block_obj is None:
                logger.warning(f"Block '{block_name}' not found")
                return {}

            # Get block origin
            try:
                origin = block_obj.Origin
                origin_coords = (
                    (origin[0], origin[1], origin[2]) if origin else (0, 0, 0)
                )
            except Exception:
                origin_coords = (0, 0, 0)

            # Get block properties
            block_info = {
                "Name": str(block_obj.Name),
                "Origin": origin_coords,
                "ObjectCount": self._safe_get_property(block_obj, "Count", 0),
                "IsXRef": self._safe_get_property(block_obj, "IsXRef", False),
                "Comments": self._safe_get_property(block_obj, "Comments", ""),
            }

            return block_info

        except Exception as e:
            logger.error(f"Failed to get block info for '{block_name}': {e}")
            return {}

    def get_block_references(self, block_name: str) -> List[Dict[str, Any]]:
        """Get all references (instances) of a specific block in the drawing.

        Args:
            block_name: Name of the block to find references for

        Returns:
            List of dictionaries with reference information:
            - Handle: Block reference handle
            - InsertionPoint: Insertion point (x, y, z)
            - ScaleFactors: Scale factors (x, y, z)
            - Rotation: Rotation angle in degrees
            - Layer: Layer name
        """
        try:
            document = self._get_document("get_block_references")
            references: List[Dict[str, Any]] = []

            # Iterate through all entities in ModelSpace
            for entity in document.ModelSpace:
                try:
                    # Check if entity is a block reference
                    if entity.ObjectName == "AcDbBlockReference":
                        # Check if it's the block we're looking for
                        if entity.Name == block_name:
                            # Get insertion point
                            try:
                                ins_point = entity.InsertionPoint
                                insertion_point = (
                                    ins_point[0],
                                    ins_point[1],
                                    ins_point[2],
                                )
                            except Exception:
                                insertion_point = (0, 0, 0)

                            # Get scale factors
                            scale_x = self._safe_get_property(
                                entity, "XScaleFactor", 1.0
                            )
                            scale_y = self._safe_get_property(
                                entity, "YScaleFactor", 1.0
                            )
                            scale_z = self._safe_get_property(
                                entity, "ZScaleFactor", 1.0
                            )

                            # Get rotation (convert from radians to degrees)
                            rotation_rad = self._safe_get_property(
                                entity, "Rotation", 0.0
                            )
                            rotation_deg = rotation_rad * 180.0 / math.pi

                            ref_info = {
                                "Handle": str(entity.Handle),
                                "InsertionPoint": insertion_point,
                                "ScaleFactors": (scale_x, scale_y, scale_z),
                                "Rotation": round(rotation_deg, 2),
                                "Layer": str(
                                    self._safe_get_property(entity, "Layer", "0")
                                ),
                            }
                            references.append(ref_info)

                except Exception as e:
                    logger.debug(f"Error processing entity: {e}")
                    continue

            logger.info(f"Found {len(references)} references of block '{block_name}'")
            return references

        except Exception as e:
            logger.error(f"Failed to get block references for '{block_name}': {e}")
            return []
