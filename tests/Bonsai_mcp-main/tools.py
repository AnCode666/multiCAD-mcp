# blender_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context, Image
import socket
import json
import asyncio
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, TypedDict, Union
import os
from pathlib import Path
import base64
from urllib.parse import urlparse
from typing import Optional
import sys
from bc3_writer import IFC2BC3Converter


# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlenderMCPServer")

@dataclass
class BlenderConnection:
    host: str
    port: int
    sock: socket.socket = None  # Changed from 'socket' to 'sock' to avoid naming conflict
    
    def connect(self) -> bool:
        """Connect to the Blender addon socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Blender at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Blender: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Blender addon"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Blender: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        # Use a consistent timeout value that matches the addon's timeout
        sock.settimeout(15.0)  # Match the addon's timeout
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        # If we get an empty chunk, the connection might be closed
                        if not chunks:  # If we haven't received anything yet, this is an error
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        # If we get here, it parsed successfully
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    # If we hit a timeout during receiving, break the loop and try to use what we have
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise  # Re-raise to be handled by the caller
        except socket.timeout:
            logger.warning("Socket timeout during chunked receive")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        # Try to use what we have
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                # Try to parse what we have
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                # If we can't parse it, it's incomplete
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Send a command to Blender and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Blender")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # Log the command being sent
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # Set a timeout for receiving - use the same timeout as in receive_full_response
            self.sock.settimeout(15.0)  # Match the addon's timeout
            
            # Receive the response using the improved receive_full_response method
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Blender error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Blender"))
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Blender")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            # Just invalidate the current socket so it will be recreated next time
            self.sock = None
            raise Exception("Timeout waiting for Blender response - try simplifying your request")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Blender lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Blender: {str(e)}")
            # Try to log what was received
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            raise Exception(f"Invalid response from Blender: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Blender: {str(e)}")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            self.sock = None
            raise Exception(f"Communication error with Blender: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    # We don't need to create a connection here since we're using the global connection
    # for resources and tools
    
    try:
        # Just log that we're starting up
        logger.info("BlenderMCP server starting up")
        
        # Try to connect to Blender on startup to verify it's available
        try:
            # This will initialize the global connection if needed
            blender = get_blender_connection()
            logger.info("Successfully connected to Blender on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Blender on startup: {str(e)}")
            logger.warning("Make sure the Blender addon is running before using Blender resources or tools")
        
        # Return an empty context - we're using the global connection
        yield {}
    finally:
        # Clean up the global connection on shutdown
        global _blender_connection
        if _blender_connection:
            logger.info("Disconnecting from Blender on shutdown")
            _blender_connection.disconnect()
            _blender_connection = None
        logger.info("BlenderMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "Bonsai MCP",
    description="IFC manipulation through Blender and MCP",
    lifespan=server_lifespan
)

# Resource endpoints

# Global connection for resources (since resources can't access context)
_blender_connection = None

def get_blender_connection():
    """Get or create a persistent Blender connection"""
    global _blender_connection
    
    # If we have an existing connection, check if it's still valid
    if _blender_connection is not None:
        try:
            # Simple ping to check if connection is still alive
            _blender_connection.send_command("get_ifc_project_info")
            return _blender_connection
        except Exception as e:
            # Connection is dead, close it and create a new one
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _blender_connection.disconnect()
            except:
                pass
            _blender_connection = None
    
    # Create a new connection if needed
    if _blender_connection is None:
        _blender_connection = BlenderConnection(host="localhost", port=9876)
        if not _blender_connection.connect():
            logger.error("Failed to connect to Blender")
            _blender_connection = None
            raise Exception("Could not connect to Blender. Make sure the Blender addon is running.")
        logger.info("Created new persistent connection to Blender")
    
    return _blender_connection

# -------------------------------
# MCP TOOLS
# -------------------------------

@mcp.tool()
def execute_blender_code(ctx: Context, code: str) -> str:
    """
    Execute arbitrary Python code in Blender.
    
    Parameters:
    - code: The Python code to execute
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        
        result = blender.send_command("execute_code", {"code": code})
        return f"Code executed successfully: {result.get('result', '')}"
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return f"Error executing code: {str(e)}"
    

### IFC Tools
@mcp.tool()
def get_ifc_project_info() -> str:
    """
    Get basic information about the IFC project, including name, description, 
    and counts of different entity types.
    
    Returns:
        A JSON-formatted string with project information
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_ifc_project_info")
        
        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting IFC project info: {str(e)}")
        return f"Error getting IFC project info: {str(e)}"

@mcp.tool()
def get_selected_ifc_entities() -> str:
    """
    Get IFC entities corresponding to the currently selected objects in Blender.
    This allows working specifically with objects the user has manually selected in the Blender UI.
    
    Returns:
        A JSON-formatted string with information about the selected IFC entities
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_selected_ifc_entities")
        
        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting selected IFC entities: {str(e)}")
        return f"Error getting selected IFC entities: {str(e)}"

# Modify the existing list_ifc_entities function to accept a selected_only parameter
@mcp.tool()
def list_ifc_entities(entity_type: str | None = None, limit: int = 50, selected_only: bool = False) -> str:
    """
    List IFC entities of a specific type. Can be filtered to only include objects
    currently selected in the Blender UI.
    
    Args:
        entity_type: Type of IFC entity to list (e.g., "IfcWall")
        limit: Maximum number of entities to return
        selected_only: If True, only return information about selected objects
    
    Returns:
        A JSON-formatted string listing the specified entities
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("list_ifc_entities", {
            "entity_type": entity_type,
            "limit": limit,
            "selected_only": selected_only
        })
        
        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error listing IFC entities: {str(e)}")
        return f"Error listing IFC entities: {str(e)}"

# Modify the existing get_ifc_properties function to accept a selected_only parameter
@mcp.tool()
def get_ifc_properties(global_id: str | None = None, selected_only: bool = False) -> str:
    """
    Get properties of IFC entities. Can be used to get properties of a specific entity by GlobalId,
    or to get properties of all currently selected objects in Blender.
    
    Args:
        global_id: GlobalId of a specific IFC entity (optional if selected_only is True)
        selected_only: If True, return properties for all selected objects instead of a specific entity
    
    Returns:
        A JSON-formatted string with entity information and properties
    """
    try:
        blender = get_blender_connection()
        
        # Validate parameters
        if not global_id and not selected_only:
            return json.dumps({"error": "Either global_id or selected_only must be specified"}, indent=2)
        
        result = blender.send_command("get_ifc_properties", {
            "global_id": global_id,
            "selected_only": selected_only
        })
        
        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting IFC properties: {str(e)}")
        return f"Error getting IFC properties: {str(e)}"
    
@mcp.tool()
def get_ifc_spatial_structure() -> str:
    """
    Get the spatial structure of the IFC model (site, building, storey, space hierarchy).
    
    Returns:
        A JSON-formatted string representing the hierarchical structure of the IFC model
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_ifc_spatial_structure")
        
        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting IFC spatial structure: {str(e)}")
        return f"Error getting IFC spatial structure: {str(e)}"

@mcp.tool()
def get_ifc_total_structure() -> str:
    """
    Get the complete IFC structure including spatial hierarchy and all building elements.

    This function extends the basic spatial structure to include building elements like walls,
    doors, windows, columns, beams, etc. that are contained within each spatial element.
    It provides a comprehensive view of how the building is organized both spatially and
    in terms of its physical components.

    Returns:
        A JSON-formatted string representing the complete hierarchical structure of the IFC model
        including spatial elements and their contained building elements, plus summary statistics
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_ifc_total_structure")

        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting IFC total structure: {str(e)}")
        return f"Error getting IFC total structure: {str(e)}"

@mcp.tool()
def get_ifc_relationships(global_id: str) -> str:
    """
    Get all relationships for a specific IFC entity.
    
    Args:
        global_id: GlobalId of the IFC entity
    
    Returns:
        A JSON-formatted string with all relationships the entity participates in
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_ifc_relationships", {
            "global_id": global_id
        })
        
        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting IFC relationships: {str(e)}")
        return f"Error getting IFC relationships: {str(e)}"
    
@mcp.tool()
def export_ifc_data(
    entity_type: str | None = None, 
    level_name: str | None = None, 
    output_format: str = "csv",
    ctx: Context | None = None
) -> str:
    """
    Export IFC data to a file in JSON or CSV format.
    
    This tool extracts IFC data and creates a structured export file. You can filter
    by entity type and/or building level, and choose the output format.
    
    Args:
        entity_type: Type of IFC entity to export (e.g., "IfcWall") - leave empty for all entities
        level_name: Name of the building level to filter by (e.g., "Level 1") - leave empty for all levels
        output_format: "json" or "csv" format for the output file
        
    Returns:
        Confirmation message with the export file path or an error message
    """
    try:
        # Get Blender connection
        blender = get_blender_connection()

        # Validate output format
        if output_format not in ["json", "csv"]:
            return "Error: output_format must be 'json' or 'csv'"

        # Execute the export code in Blender
        result = blender.send_command("export_ifc_data", {
            "entity_type": entity_type,
            "level_name": level_name,
            "output_format": output_format
        })
        
        # Check for errors from Blender
        if isinstance(result, dict) and "error" in result:
            return f"Error: {result['error']}"
        
        # Return the result with export summary
        # return result
        return json.dumps(result, indent=2)
    
    except Exception as e:
        logger.error(f"Error exporting IFC data: {str(e)}")
        return f"Error exporting IFC data: {str(e)}"
    
@mcp.tool()
def place_ifc_object(
    type_name: str, 
    x: float, 
    y: float, 
    z: float, 
    rotation: float = 0.0,
    ctx: Context| None = None
) -> str:
    """
    Place an IFC object at a specified location with optional rotation.
    
    This tool allows you to create and position IFC elements in the model.
    The object is placed using the specified IFC type and positioned
    at the given coordinates with optional rotation around the Z axis.
    
    Args:
        type_name: Name of the IFC element type to place (must exist in the model)
        x: X-coordinate in model space
        y: Y-coordinate in model space
        z: Z-coordinate in model space
        rotation: Rotation angle in degrees around the Z axis (default: 0)
        
    Returns:
        A message with the result of the placement operation
    """
    try:
        # Get Blender connection
        blender = get_blender_connection()
        
        # Send command to place the object
        result = blender.send_command("place_ifc_object", {
            "type_name": type_name,
            "location": [x, y, z],
            "rotation": rotation
        })
        
        # Check for errors
        if isinstance(result, dict) and "error" in result:
            return f"Error placing object: {result['error']}"
        
        # Format success message
        if isinstance(result, dict) and result.get("success"):
            return (f"Successfully placed '{type_name}' object at ({x}, {y}, {z}) "
                   f"with {rotation}° rotation.\nObject name: {result.get('blender_name')}, "
                   f"Global ID: {result.get('global_id')}")
        
        # Return the raw result as string if it's not a success or error dict
        return f"Placement result: {json.dumps(result, indent=2)}"
    
    except Exception as e:
        logger.error(f"Error placing IFC object: {str(e)}")
        return f"Error placing IFC object: {str(e)}"
    
@mcp.tool()
def get_user_view() -> Image:
    """
    Capture and return the current Blender viewport as an image.
    Shows what the user is currently seeing in Blender.

    Focus mostly on the 3D viewport. Use the UI to assist in your understanding of the scene but only refer to it if specifically prompted.
    
    Args:
        max_dimension: Maximum dimension (width or height) in pixels for the returned image
        compression_quality: Image compression quality (1-100, higher is better quality but larger)
    
    Returns:
        An image of the current Blender viewport
    """
    max_dimension = 800
    compression_quality = 85

    # Use PIL to compress the image
    from PIL import Image as PILImage
    import io

    try:
        # Get the global connection
        blender = get_blender_connection()
        
        # Request current view
        result = blender.send_command("get_current_view")
        
        if "error" in result:
            # logger.error(f"Error getting view from Blender: {result.get('error')}")
            raise Exception(f"Error getting current view: {result.get('error')}")
        
        # Extract image information
        if "data" not in result or "width" not in result or "height" not in result:
            # logger.error("Incomplete image data returned from Blender")
            raise Exception("Incomplete image data returned from Blender")
        
        # Decode the base64 image data
        image_data = base64.b64decode(result["data"])
        original_width = result["width"]
        original_height = result["height"]
        original_format = result.get("format", "png")
        
        # Compression is only needed if the image is large
        if original_width > 800 or original_height > 800 or len(image_data) > 1000000:
            # logger.info(f"Compressing image (original size: {len(image_data)} bytes)")
            
            # Open image from binary data
            img = PILImage.open(io.BytesIO(image_data))
            
            # Resize if needed
            if original_width > max_dimension or original_height > max_dimension:
                # Calculate new dimensions maintaining aspect ratio
                if original_width > original_height:
                    new_width = max_dimension
                    new_height = int(original_height * (max_dimension / original_width))
                else:
                    new_height = max_dimension
                    new_width = int(original_width * (max_dimension / original_height))
                
                # Resize using high-quality resampling
                img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # Save as JPEG with compression
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=compression_quality, optimize=True)
            compressed_data = output.getvalue()

            # logger.info(f"Image compressed from {len(image_data)} to {len(compressed_data)} bytes")
            
            # Return compressed image
            return Image(data=compressed_data, format="jpeg")
        else:
            # Image is small enough, return as-is
            return Image(data=image_data, format=original_format)
            
    except Exception as e:
        # logger.error(f"Error processing viewport image: {str(e)}")
        raise Exception(f"Error processing viewport image: {str(e)}")

@mcp.tool()
def get_ifc_quantities() -> str:
    """
    Extract and get basic qtos about the IFC project.
    
    Returns:
        A JSON-formatted string with project quantities information
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_ifc_quantities")
        
        # Return the formatted JSON of the results
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting IFC project quantities: {str(e)}")
        return f"Error getting IFC project quantities: {str(e)}"

@mcp.tool()
def export_bc3_budget(language: str = 'es') -> str:
    """
    Export a BC3 budget file (FIEBDC-3/2016) based on the IFC model loaded in Blender.

    This tool creates a complete construction budget in BC3 format by:
    1. Extracting the complete IFC spatial structure (Project → Site → Building → Storey)
    2. Extracting IFC quantities and measurements for all building elements
    3. Converting to BC3 hierarchical format with IFC2BC3Converter:
       - Generates budget chapters from IFC spatial hierarchy
       - Groups building elements by type and categories defined in external JSON
       - Assigns unit prices from language-specific JSON database
       - Creates detailed measurements sorted alphabetically
    4. Exports to BC3 file with windows-1252 encoding

    Features:
    - Multi-language support (Spanish/English) for descriptions and labels
    - Automatic element categorization using external JSON configuration
    - Optimized conversion with O(1) lookups and batch operations
    - Detailed measurements with dimensions (units, length, width, height)
    - Full FIEBDC-3/2016 format compliance

    Configuration files (in resources/bc3_helper_files/):
    - precios_unitarios.json / unit_prices.json: Unit prices per IFC type
    - spatial_labels_es.json / spatial_labels_en.json: Spatial element translations
    - element_categories.json: IFC type to category mappings

    Args:
        language: Language for the budget file ('es' for Spanish, 'en' for English). Default is 'es'.

    Returns:
        A confirmation message with the path to the generated BC3 file in the exports/ folder.
    """
    try:
        # Get IFC data
        logger.info("Getting IFC data...")
        ifc_total_structure = get_ifc_total_structure()
        ifc_quantities = get_ifc_quantities()

        # Validate that we got valid JSON responses
        # If there's an error, these functions return error strings starting with "Error"
        if isinstance(ifc_total_structure, str) and ifc_total_structure.startswith("Error"):
            return f"Failed to get IFC structure: {ifc_total_structure}"

        if isinstance(ifc_quantities, str) and ifc_quantities.startswith("Error"):
            return f"Failed to get IFC quantities: {ifc_quantities}"

        # Try to parse the JSON to ensure it's valid
        try:
            structure_data = json.loads(ifc_total_structure) if isinstance(ifc_total_structure, str) else ifc_total_structure
            quantities_data = json.loads(ifc_quantities) if isinstance(ifc_quantities, str) else ifc_quantities
        except json.JSONDecodeError as e:
            return f"Invalid JSON data received from Blender. Structure error: {str(e)}"

        converter = IFC2BC3Converter(structure_data, quantities_data, language=language)
        output_path = converter.export()

        return f"BC3 file successfully created at: {output_path}"

    except Exception as e:
        logger.error(f"Error creating BC3 budget: {str(e)}")
        return f"Error creating BC3 budget: {str(e)}"

# WIP, not ready to be implemented:  
# @mcp.tool()
# def create_plan_view(height_offset: float = 0.5, view_type: str = "top", 
#                     resolution_x: int = 400, resolution_y: int = 400,
#                     output_path: str = None) -> Image:
#     """
#     Create a plan view (top-down view) at the specified height above the first building story.
    
#     Args:
#         height_offset: Height in meters above the building story (default 0.5m)
#         view_type: Type of view - "top", "front", "right", "left" (note: only "top" is fully implemented)
#         resolution_x: Horizontal resolution of the render in pixels - Keep it small, max 800 x 800, recomended 400 x 400
#         resolution_y: Vertical resolution of the render in pixels
#         output_path: Optional path to save the rendered image
    
#     Returns:
#         A rendered image showing the plan view of the model
#     """
#     try:
#         # Get the global connection
#         blender = get_blender_connection()
        
#         # Request an orthographic render
#         result = blender.send_command("create_orthographic_render", {
#             "view_type": view_type,
#             "height_offset": height_offset,
#             "resolution_x": resolution_x,
#             "resolution_y": resolution_y,
#             "output_path": output_path  # Can be None to use a temporary file
#         })
        
#         if "error" in result:
#             raise Exception(f"Error creating plan view: {result.get('error', 'Unknown error')}")
        
#         if "data" not in result:
#             raise Exception("No image data returned from Blender")
        
#         # Decode the base64 image data
#         image_data = base64.b64decode(result["data"])
        
#         # Return as an Image object
#         return Image(data=image_data, format="png")
#     except Exception as e:
#         logger.error(f"Error creating plan view: {str(e)}")
#         raise Exception(f"Error creating plan view: {str(e)}")


@mcp.tool()
def export_drawing_png(
    height_offset: float = 0.5,
    view_type: str = "top",
    resolution_x: int = 1920,
    resolution_y: int = 1080,
    storey_name: str | None = None,
    output_path: str | None = None
) -> dict:
    """Export drawings as PNG images with custom resolution.
    
    Creates a drawing, with the view type specified, of the IFC building at the specified 
    height above the floor level. Supports custom resolution for high-quality architectural drawings.
    
    Args:
        height_offset: Height in meters above the storey level for the camera position (default 0.5m)
        view_type: Type of view - "top" for plan view, "front", "right" and "left" for elevation views, and "isometric" for 3D view
        resolution_x: Horizontal resolution in pixels (default 1920, max recommended 4096)
        resolution_y: Vertical resolution in pixels (default 1080, max recommended 4096)
        storey_name: Specific storey name to add to the file name (if None, prints default in the file name)
        output_path: Optional file path to save the PNG (if None, returns as base64 image)
    
    Returns:
        metadata and the path of the file image of the drawing at the specified resolution
    """
    try:
        # Validate resolution limits for performance
        if resolution_x > 4096 or resolution_y > 4096:
            raise Exception("Resolution too high. Maximum recommended: 4096x4096 pixels")
        
        if resolution_x < 100 or resolution_y < 100:
            raise Exception("Resolution too low. Minimum: 100x100 pixels")
        
        # Get the global connection
        blender = get_blender_connection()
        
        # Request drawing render
        result = blender.send_command("export_drawing_png", {
            "view_type": view_type,
            "height_offset": height_offset,
            "resolution_x": resolution_x,
            "resolution_y": resolution_y,
            "storey_name": storey_name,
            "output_path": output_path
        })
        
        if "error" in result:
            raise Exception(f"Error creating {view_type} drawing: {result.get('error', 'Unknown error')}")
        
        if "data" not in result:
            raise Exception("No image data returned from Blender")
        
        # Decode the base64 image data
        image_data = base64.b64decode(result["data"])
        
        # Ensure output path exists
        if not output_path:
            os.makedirs("./exports/drawings", exist_ok=True)
            # Generate filename based on view type
            view_name = {
                "top": "plan_view",
                "front": "front_elevation", 
                "right": "right_elevation",
                "left": "left_elevation",
                "isometric": "isometric_view"
            }.get(view_type, view_type)
            filename = f"{view_name}_{storey_name or 'default'}.png"
            output_path = os.path.join("./exports/drawings", filename)
        
        # Save to file
        with open(output_path, "wb") as f:
            f.write(image_data)
        
        # Return only metadata
        return {
            "status": "success",
            "file_path": os.path.abspath(output_path),
            # Opcional: si tienes un servidor de archivos, podrías devolver también una URL
            # "url": f"http://localhost:8000/files/{filename}"
        }
        
    except Exception as e:
        logger.error(f"Error exporting drawing: {str(e)}")
        return { "status": "error", "message": str(e) }

@mcp.tool()
def get_ifc_georeferencing_info(include_contexts: bool = False) -> str:
    """
    Checks whether the IFC currently opened in Bonsai/BlenderBIM is georeferenced
    and returns the key georeferencing information.

    Parameters
    ----------
    include_contexts : bool
        If True, adds a breakdown of the RepresentationContexts and operations.
        

    Returns
    --------
    str (JSON pretty-printed)
        {
          "georeferenced": true|false,
          "crs": {
            "name": str|null,
            "geodetic_datum": str|null,
            "vertical_datum": str|null,
            "map_unit": str|null
          },
          "map_conversion": {
            "eastings": float|null,
            "northings": float|null,
            "orthogonal_height": float|null,
            "scale": float|null,
            "x_axis_abscissa": float|null,
            "x_axis_ordinate": float|null
          },
          "world_coordinate_system": {
            "origin": [x, y, z]|null
          },
          "true_north": {
            "direction_ratios": [x, y]|null
          },
          "site": {
            "local_placement_origin": [x, y, z]|null,
            "ref_latitude": [deg, min, sec, millionth]|null,
            "ref_longitude": [deg, min, sec, millionth]|null,
            "ref_elevation": float|null
          },
          "contexts": [...],              # only if include_contexts = true
          "warnings": [ ... ]             # Informational message
        }

    Notes
    -----
    - This tool acts as a wrapper: it sends the "get_ifc_georeferencing_info"
      command to the Blender add-on. The add-on must implement that logic
      (reading IfcProject/IfcGeometricRepresentationContext, IfcMapConversion,
      TargetCRS, IfcSite.RefLatitude/RefLongitude/RefElevation, etc.).
    - It always returns a JSON string with indentation for easier reading.
    """
    blender = get_blender_connection()
    params = {
        "include_contexts": bool(include_contexts)
    }

    try:
        result = blender.send_command("get_ifc_georeferencing_info", params)
        # Ensures that the result is serializable and easy to read
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("get_ifc_georeferencing_info error")
        return json.dumps(
            {
                "georeferenced": False,
                "error": "Unable to retrieve georeferencing information from the IFC model.",
                "details": str(e)
            },
            ensure_ascii=False,
            indent=2
        )

@mcp.tool()
def georeference_ifc_model(
    crs_mode: str,
    epsg: int = None,
    crs_name: str = None,
    geodetic_datum: str = None,
    map_projection: str = None,
    map_zone: str = None,
    eastings: float = None,
    northings: float = None,
    orthogonal_height: float = 0.0,
    scale: float = 1.0,
    x_axis_abscissa: float = None,
    x_axis_ordinate: float = None,
    true_north_azimuth_deg: float = None,
    context_filter: str = "Model",
    context_index: int = None,
    site_ref_latitude: list = None,      # [deg, min, sec, millionth]
    site_ref_longitude: list = None,     # [deg, min, sec, millionth]
    site_ref_elevation: float = None,
    site_ref_latitude_dd: float = None,  # Decimal degrees (optional)
    site_ref_longitude_dd: float = None, # Decimal degrees (optional)
    overwrite: bool = False,
    dry_run: bool = False,
    write_path: str = None,
) -> str:
    """
    Georeferences the IFC currently opened in Bonsai/BlenderBIM by creating or 
    updating IfcProjectedCRS and IfcMapConversion. Optionally updates IfcSite 
    and writes the file to disk.
    """
    import json
    blender = get_blender_connection()

    # Build params excluding None values to keep the payload clean
    params = {
        "crs_mode": crs_mode,
        "epsg": epsg,
        "crs_name": crs_name,
        "geodetic_datum": geodetic_datum,
        "map_projection": map_projection,
        "map_zone": map_zone,
        "eastings": eastings,
        "northings": northings,
        "orthogonal_height": orthogonal_height,
        "scale": scale,
        "x_axis_abscissa": x_axis_abscissa,
        "x_axis_ordinate": x_axis_ordinate,
        "true_north_azimuth_deg": true_north_azimuth_deg,
        "context_filter": context_filter,
        "context_index": context_index,
        "site_ref_latitude": site_ref_latitude,
        "site_ref_longitude": site_ref_longitude,
        "site_ref_elevation": site_ref_elevation,
        "site_ref_latitude_dd": site_ref_latitude_dd,
        "site_ref_longitude_dd": site_ref_longitude_dd,
        "overwrite": overwrite,
        "dry_run": dry_run,
        "write_path": write_path,
    }
    params = {k: v for k, v in params.items() if v is not None}

    try:
        result = blender.send_command("georeference_ifc_model", params)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("georeference_ifc_model error")
        return json.dumps(
            {"success": False, "error": "Could not georeference the model.", "details": str(e)},
            ensure_ascii=False,
            indent=2,
        )

@mcp.tool()
def generate_ids(
    title: str,
    specs: Union[List[dict], str],  # accepts a list of dicts or a JSON string
    description: str = "",
    author: str = "",
    ids_version: Union[str, float] = "",    # IDS version (Not IFC version)
    purpose: str = "",
    milestone: str = "",
    date_iso: str = None,
    output_path: str = None,    
) -> str:
    """
    Creates an .ids file in Blender/Bonsai by calling the add-on handler 'generate_ids'.

    Parameters:
      - title (str): Title of the IDS.
      - specs (list | JSON str): List of 'specs' containing 'applicability' and 'requirements'.
        Each facet is a dict with at least a 'type' field ("Entity", "Attribute", "Property",
        "Material", "Classification", "PartOf") and its corresponding attributes.
      - description, author, ids_version, date_iso, purpose, milestone: IDS metadata fields.
      - output_path (str): Full path to the .ids file to be created. If omitted, the add-on will generate a default name.

    Returns:
      - JSON (str) with the handler result: {"ok": bool, "output_path": "...", "message": "..."} 
        or {"ok": False, "error": "..."}
    """

    blender = get_blender_connection()

    # Allow 'specs' to be received as JSON text (convenient when the client builds it as a string)
    if isinstance(specs, str):
        try:
            specs = json.loads(specs)
        except Exception as e:
            return json.dumps(
                {"ok": False, "error": "Argument 'specs' is not a valid JSON", "details": str(e)},
                ensure_ascii=False, indent=2
            )

    # Basic validations to avoid sending garbage to the add-on
    if not isinstance(title, str) or not title.strip():
        return json.dumps({"ok": False, "error": "Empty or invalid 'title' parameter."},
                          ensure_ascii=False, indent=2)
    if not isinstance(specs, list) or not specs:
        return json.dumps({"ok": False, "error": "You must provide at least one 'spec' in 'specs'."},
                          ensure_ascii=False, indent=2)

    # Safe coercion of ids_version to str
    if ids_version is not None and not isinstance(ids_version, str):
        ids_version = str(ids_version)

    params: dict[str, Any] = {
        "title": title,
        "specs": specs,
        "description": description,
        "author": author,
        "ids_version": ids_version,   # ← the handler maps it to the 'version' field of the IDS
        "date_iso": date_iso,
        "output_path": output_path,
        "purpose": purpose,
        "milestone": milestone,
    }

    # Cleanup: remove keys with None values to keep the payload clean
    params = {k: v for k, v in params.items() if v is not None}

    try:
        # Assignment name must match EXACTLY the one in addon.py
        result = blender.send_command("generate_ids", params)
        # Returns JSON 
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": "Fallo al crear IDS", "details": str(e)},
                          ensure_ascii=False, indent=2)


# -------------------------------
# MCP RESOURCES
# -------------------------------

# Base path of the resource files
BASE_PATH = Path("./resources")

@mcp.resource("file://table_of_contents.json")
def formulas_rp() -> str:
    """Read the content of table_of_contents.json file"""
    file_path = BASE_PATH / "table_of_contents.json"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


# -------------------------------
# MCP PROMPTS
# -------------------------------

@mcp.prompt("Technical_building_report")
def technical_building_report(project_name: str, project_location: str, language: str = "english") -> str:
    """
    Generate a comprehensive technical building report based on an IFC model loaded in Blender.
    
    Args:
        project_name: Name of the project/building
        project_location: Building location (city, address)
        language: Report language - "english", "spanish", "french", "german", "italian", "portuguese"
    
    Returns:
        Structured technical report following basic project standards in the selected language.
    """
    
    # Language-specific instructions
    language_instructions = {
        "english": {
            "role": "You are a technical architect specialized in creating technical reports for basic building projects.",
            "objective": f"Your objective is to generate a comprehensive technical report for the building \"{project_name}\" located in \"{project_location}\", using data from the IFC model loaded in Blender.",
            "workflow_title": "## MANDATORY WORKFLOW:",
            "report_language": "Write the entire report in English."
        },
        "spanish": {
            "role": "Eres un arquitecto técnico especializado en la creación de memorias técnicas de proyectos básicos de edificación.",
            "objective": f"Tu objetivo es generar una memoria técnica completa del edificio \"{project_name}\" localizado en \"{project_location}\", utilizando los datos del modelo IFC cargado en Blender.",
            "workflow_title": "## FLUJO DE TRABAJO OBLIGATORIO:",
            "report_language": "Redacta todo el informe en español."
        },
        "french": {
            "role": "Vous êtes un architecte technique spécialisé dans la création de rapports techniques pour les projets de bâtiment de base.",
            "objective": f"Votre objectif est de générer un rapport technique complet pour le bâtiment \"{project_name}\" situé à \"{project_location}\", en utilisant les données du modèle IFC chargé dans Blender.",
            "workflow_title": "## FLUX DE TRAVAIL OBLIGATOIRE:",
            "report_language": "Rédigez tout le rapport en français."
        },
        "german": {
            "role": "Sie sind ein technischer Architekt, der sich auf die Erstellung technischer Berichte für grundlegende Bauprojekte spezialisiert hat.",
            "objective": f"Ihr Ziel ist es, einen umfassenden technischen Bericht für das Gebäude \"{project_name}\" in \"{project_location}\" zu erstellen, unter Verwendung der Daten aus dem in Blender geladenen IFC-Modell.",
            "workflow_title": "## OBLIGATORISCHER ARBEITSABLAUF:",
            "report_language": "Verfassen Sie den gesamten Bericht auf Deutsch."
        },
        "italian": {
            "role": "Sei un architetto tecnico specializzato nella creazione di relazioni tecniche per progetti edilizi di base.",
            "objective": f"Il tuo obiettivo è generare una relazione tecnica completa per l'edificio \"{project_name}\" situato a \"{project_location}\", utilizzando i dati del modello IFC caricato in Blender.",
            "workflow_title": "## FLUSSO DI LAVORO OBBLIGATORIO:",
            "report_language": "Scrivi tutto il rapporto in italiano."
        },
        "portuguese": {
            "role": "Você é um arquiteto técnico especializado na criação de relatórios técnicos para projetos básicos de construção.",
            "objective": f"Seu objetivo é gerar um relatório técnico abrangente para o edifício \"{project_name}\" localizado em \"{project_location}\", usando dados do modelo IFC carregado no Blender.",
            "workflow_title": "## FLUXO DE TRABALHO OBRIGATÓRIO:",
            "report_language": "Escreva todo o relatório em português."
        }
    }
    
    # Get language instructions (default to English if language not supported)
    lang_config = language_instructions.get(language.lower(), language_instructions["english"])
    
    return f"""
{lang_config["role"]} {lang_config["objective"]}

**LANGUAGE REQUIREMENT:** {lang_config["report_language"]}

{lang_config["workflow_title"]}

### 1. INITIAL IFC MODEL ANALYSIS
- **Use MCP tool:** `get_ifc_project_info` to get basic project information
- **Use MCP tool:** `get_ifc_spatial_structure` to understand the building's spatial structure
- **Use MCP tool:** `get_user_view` to capture a general view of the model

### 2. OBTAIN TABLE OF CONTENTS
- **Access MCP resource:** `file://table_of_contents.json` to get the complete technical report structure

### 3. DETAILED ANALYSIS BY SECTIONS

#### 3.1 For "General Building Data" Section:
- **Use:** `get_ifc_quantities` to obtain areas and volumes
- **Use:** `list_ifc_entities` with entity_type="IfcSpace" for spaces
- **Use:** `list_ifc_entities` with entity_type="IfcBuildingStorey" for floors

#### 3.2 For "Architectural Solution" Section:
- **Use:** `list_ifc_entities` with entity_type="IfcWall" for walls
- **Use:** `list_ifc_entities` with entity_type="IfcDoor" for doors
- **Use:** `list_ifc_entities` with entity_type="IfcWindow" for windows
- **Use:** `get_user_view` to capture representative views

#### 3.3 For "Construction Systems" Section:
- **Use:** `list_ifc_entities` with entity_type="IfcBeam" for beams
- **Use:** `list_ifc_entities` with entity_type="IfcColumn" for columns
- **Use:** `list_ifc_entities` with entity_type="IfcSlab" for slabs
- **Use:** `list_ifc_entities` with entity_type="IfcRoof" for roofs
- **Use:** `get_ifc_properties` to obtain material properties

#### 3.4 For Building Services:
- **Use:** `list_ifc_entities` with entity_type="IfcPipeSegment" for plumbing
- **Use:** `list_ifc_entities` with entity_type="IfcCableSegment" for electrical
- **Use:** `list_ifc_entities` with entity_type="IfcDuctSegment" for HVAC

#### 3.5 For drawings and Graphic Documentation:
- **Use:** `export_drawing_png` 5 times, using as parameter each time "top", "front", "right", "left" and "isometric", to generate architectural drawings.
- **Configure:** resolution_x=1920, resolution_y=1080 for adequate quality
- **Use:** `get_user_view` for complementary 3D views

### 4. TECHNICAL REPORT STRUCTURE

Organize the document following exactly the structure from the `table_of_contents.json` resource:

**TECHNICAL REPORT – BASIC PROJECT: {project_name}**

**Location:** {project_location}

#### 1. INTRODUCTION
- Define object and scope based on IFC model data
- Justify the adopted architectural solution

#### 2. GENERAL BUILDING DATA
- **Location:** {project_location}
- **Areas:** Extract from quantities and spaces analysis
- **Distribution:** Based on IFC spatial structure
- **Regulations:** Identify applicable regulations according to use and location

#### 3-11. DEVELOPMENT OF ALL SECTIONS
- Complete each section according to the index, using data extracted from the IFC model
- Include summary tables of areas, materials and construction elements
- Generate technical conclusions based on evidence

### 5. MANDATORY GRAPHIC DOCUMENTATION
- **2D drawings:**Include the 4 2D drawings generated before in the 3.5 section with the Tool `export_drawing_png` ("top", "front", "right", "left")
- **3D views:** Include the isometric 3D view generated before in the 3.5 section with the Tool `export_drawing_png`
- **Organize:** All images in section 11. Annexes

### 6. TECHNICAL TABLES AND CHARTS
- **Areas summary table:** Extracted from quantities
- **Elements listing:** By typologies (walls, columns, beams, etc.)
- **Material properties:** From IFC properties

## RESPONSE FORMAT:

### MARKDOWN STRUCTURE:
```markdown
# TECHNICAL REPORT – BASIC PROJECT
## {project_name}

### Project Data:
- **Location:** {project_location}
- **Date:** [current date]
- **IFC Model:** [model information]

[Complete development of all index sections]
```

### QUALITY CRITERIA:
- **Technical precision:** All numerical data extracted directly from IFC model
- **Completeness:** Cover all index sections mandatory
- **Professional format:** Markdown tables, structured text, integrated images
- **Consistency:** Verify data consistency between sections

## CRITICAL VALIDATIONS:
1. **Verify Blender connection:** Confirm IFC model is loaded
2. **Complete all sections:** Do not omit any index section
3. **Include graphic documentation:** drawings and 3D views mandatory
4. **Quantitative data:** Areas, volumes and quantities verified
5. **Regulatory consistency:** Applicable regulations according to use and location

**IMPORTANT:** If any MCP tool fails or doesn't return data, document the limitation and indicate that section requires manual completion in executive project phase.

Proceed to generate the technical report following this detailed workflow.
"""


# Main execution

def main():
    """Run the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()
