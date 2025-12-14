"""
Block tools for inserting and listing block definitions and references.
"""

import json
import logging
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import Context

from core import InvalidParameterError
from mcp_tools.decorators import cad_tool, get_current_adapter
from mcp_tools.helpers import parse_coordinate

logger = logging.getLogger(__name__)


# ============================================================
#  Insertar un bloque
# ============================================================

def insert_block(
    adapter,
    block_name: str,
    insertion_point: str,
    scale: float = 1.0,
    rotation: float = 0.0,
    layer: str = "0"
) -> Dict[str, Any]:
    """
    Inserta un bloque en el dibujo CAD.

    Args:
        adapter: Adaptador CAD activo (AutoCADAdapter, ZwCADAdapter, etc.)
        block_name: Nombre del bloque a insertar
        insertion_point: Coordenadas en formato "x,y" o "x,y,z"
        scale: Factor de escala uniforme
        rotation: Rotación en grados
        layer: Capa donde insertar el bloque

    Returns:
        Diccionario con el resultado de la operación
    """

    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        # Normalizar el punto de inserción
        point = parse_coordinate(insertion_point)

        handle = adapter.insert_block(
            block_name=block_name,
            insertion_point=point,
            scale_x=scale,
            scale_y=scale,
            scale_z=scale,
            rotation=rotation,
            layer=layer
        )

        return {
            "success": True,
            "message": f"Block '{block_name}' inserted.",
            "block_name": block_name,
            "handle": handle,
            "insertion_point": insertion_point,
            "scale": scale,
            "rotation": rotation,
            "layer": layer
        }

    except Exception as e:
        logger.error(f"insert_block error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
#  Insertar múltiples bloques (batch)
# ============================================================

def insert_blocks_batch(adapter, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Inserta varios bloques en una sola operación.

    Args:
        adapter: Adaptador CAD
        blocks: Lista de elementos con:
                - block_name
                - insertion_point
                - scale (opcional)
                - rotation (opcional)
                - layer (opcional)

    Returns:
        Resultado agregado de la operación
    """

    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    results = []
    success_count = 0
    fail_count = 0

    for i, b in enumerate(blocks):

        try:
            point = parse_coordinate(b["insertion_point"])

            handle = adapter.insert_block(
                block_name=b["block_name"],
                insertion_point=point,
                scale_x=b.get("scale", 1.0),
                scale_y=b.get("scale", 1.0),
                scale_z=b.get("scale", 1.0),
                rotation=b.get("rotation", 0.0),
                layer=b.get("layer", "0"),
                _skip_refresh=True  # Optimización clave
            )

            results.append({
                "index": i,
                "success": True,
                "handle": handle,
                "block_name": b["block_name"]
            })

            success_count += 1

        except Exception as e:
            fail_count += 1
            results.append({
                "index": i,
                "success": False,
                "block_name": b.get("block_name"),
                "error": str(e)
            })

    # Refrescar vista una sola vez
    adapter.refresh_view()

    return {
        "success": fail_count == 0,
        "inserted": success_count,
        "failed": fail_count,
        "results": results
    }


# ============================================================
#  Listar bloques disponibles
# ============================================================

def list_blocks(adapter) -> Dict[str, Any]:
    """
    Lista todos los bloques no-sistema del dibujo CAD.

    Returns:
        Diccionario con lista de bloques
    """

    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        blocks = adapter.list_blocks()
        return {
            "success": True,
            "count": len(blocks),
            "blocks": blocks
        }
    except Exception as e:
        logger.error(f"list_blocks error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
#  Obtener información de un bloque
# ============================================================

def get_block_info(adapter, block_name: str) -> Dict[str, Any]:
    """
    Obtiene información detallada de un bloque.

    Returns:
        Diccionario con:
        - Name
        - Origin
        - ObjectCount
        - IsXRef
        - Comments
    """

    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        info = adapter.get_block_info(block_name)
        return {"success": True, "info": info}
    except Exception as e:
        logger.error(f"get_block_info error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
#  Obtener referencias (instancias) del bloque
# ============================================================

def get_block_references(adapter, block_name: str) -> Dict[str, Any]:
    """
    Lista todas las referencias de un bloque en el dibujo.

    Returns:
        Lista con:
        - Handle
        - InsertionPoint
        - ScaleFactors
        - Rotation
        - Layer
    """

    if not adapter.is_connected():
        return {"success": False, "error": "No CAD connection."}

    try:
        refs = adapter.get_block_references(block_name)
        return {
            "success": True,
            "count": len(refs),
            "references": refs
        }
    except Exception as e:
        logger.error(f"get_block_references error: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
#  Registros de herramientas
# ============================================================

def register_block_tools(mcp) -> None:
    """Register block-related MCP tools."""

    @cad_tool(mcp, "insert_block")
    def insert_block_tool(
        ctx: Context,
        block_name: str,
        insertion_point: str,
        scale: float = 1.0,
        rotation: float = 0.0,
        layer: str = "0",
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return insert_block(adapter, block_name, insertion_point, scale, rotation, layer)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"insert_block failed: {e}")
            raise

    @cad_tool(mcp, "insert_blocks_batch")
    def insert_blocks_batch_tool(
        ctx: Context,
        blocks: List[Dict[str, Any]],
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return insert_blocks_batch(adapter, blocks)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"insert_blocks_batch failed: {e}")
            raise

    @cad_tool(mcp, "list_blocks")
    def list_blocks_tool(
        ctx: Context,
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return list_blocks(adapter)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"list_blocks failed: {e}")
            raise

    @cad_tool(mcp, "get_block_info")
    def get_block_info_tool(
        ctx: Context,
        block_name: str,
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return get_block_info(adapter, block_name)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"get_block_info failed: {e}")
            raise

    @cad_tool(mcp, "get_block_references")
    def get_block_references_tool(
        ctx: Context,
        block_name: str,
        cad_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        adapter = get_current_adapter()
        try:
            return get_block_references(adapter, block_name)
        except InvalidParameterError:
            raise
        except Exception as e:
            logger.error(f"get_block_references failed: {e}")
            raise
