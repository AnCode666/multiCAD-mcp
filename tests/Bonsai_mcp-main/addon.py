import bpy
import mathutils
import json
import threading
import socket
import time
import requests
import tempfile
import traceback
import os
import shutil
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty
import base64

import bpy

import ifcopenshell
from bonsai.bim.ifc import IfcStore

bl_info = {
    "name": "Bonsai MCP",
    "author": "JotaDeRodriguez",
    "version": (0, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Bonsai MCP",
    "description": "Connect Claude to Blender via MCP. Aimed at IFC projects",
    "category": "Interface",
}


class BlenderMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None
    
    def start(self):
        if self.running:
            print("Server is already running")
            return
            
        self.running = True
        
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            
            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            print(f"BlenderMCP server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()
            
    def stop(self):
        self.running = False
        
        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Wait for thread to finish
        if self.server_thread:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
            except:
                pass
            self.server_thread = None
        
        print("BlenderMCP server stopped")
    
    def _server_loop(self):
        """Main server loop in a separate thread"""
        print("Server thread started")
        self.socket.settimeout(1.0)  # Timeout to allow for stopping
        
        while self.running:
            try:
                # Accept new connection
                try:
                    client, address = self.socket.accept()
                    print(f"Connected to client: {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # Just check running condition
                    continue
                except Exception as e:
                    print(f"Error accepting connection: {str(e)}")
                    time.sleep(0.5)
            except Exception as e:
                print(f"Error in server loop: {str(e)}")
                if not self.running:
                    break
                time.sleep(0.5)
        
        print("Server thread stopped")
    
    def _handle_client(self, client):
        """Handle connected client"""
        print("Client handler started")
        client.settimeout(None)  # No timeout
        buffer = b''
        
        try:
            while self.running:
                # Receive data
                try:
                    data = client.recv(8192)
                    if not data:
                        print("Client disconnected")
                        break
                    
                    buffer += data
                    try:
                        # Try to parse command
                        command = json.loads(buffer.decode('utf-8'))
                        buffer = b''
                        
                        # Execute command in Blender's main thread
                        def execute_wrapper():
                            try:
                                response = self.execute_command(command)
                                response_json = json.dumps(response)
                                try:
                                    client.sendall(response_json.encode('utf-8'))
                                except:
                                    print("Failed to send response - client disconnected")
                            except Exception as e:
                                print(f"Error executing command: {str(e)}")
                                traceback.print_exc()
                                try:
                                    error_response = {
                                        "status": "error",
                                        "message": str(e)
                                    }
                                    client.sendall(json.dumps(error_response).encode('utf-8'))
                                except:
                                    pass
                            return None
                        
                        # Schedule execution in main thread
                        bpy.app.timers.register(execute_wrapper, first_interval=0.0)
                    except json.JSONDecodeError:
                        # Incomplete data, wait for more
                        pass
                except Exception as e:
                    print(f"Error receiving data: {str(e)}")
                    break
        except Exception as e:
            print(f"Error in client handler: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass
            print("Client handler stopped")

    def execute_command(self, command):
        """Execute a command in the main Blender thread"""
        try:
            cmd_type = command.get("type")
            params = command.get("params", {})
            
            # Ensure we're in the right context
            if cmd_type in ["create_object", "modify_object", "delete_object"]:
                override = bpy.context.copy()
                override['area'] = [area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'][0]
                with bpy.context.temp_override(**override):
                    return self._execute_command_internal(command)
            else:
                return self._execute_command_internal(command)
                
        except Exception as e:
            print(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _execute_command_internal(self, command):
        """Internal command execution with proper context"""
        cmd_type = command.get("type")
        params = command.get("params", {})

        
        # Base handlers that are always available
        handlers = {
            "execute_code": self.execute_code,
            "get_ifc_project_info": self.get_ifc_project_info,
            "list_ifc_entities": self.list_ifc_entities,
            "get_ifc_properties": self.get_ifc_properties,
            "get_ifc_spatial_structure": self.get_ifc_spatial_structure,
            "get_ifc_total_structure": self.get_ifc_total_structure,
            "get_ifc_relationships": self.get_ifc_relationships,
            "get_selected_ifc_entities": self.get_selected_ifc_entities,
            "get_current_view": self.get_current_view,
            "export_ifc_data": self.export_ifc_data,
            "place_ifc_object": self.place_ifc_object,
            "get_ifc_quantities": self.get_ifc_quantities,
            "export_drawing_png": self.export_drawing_png,
            "get_ifc_georeferencing_info": self.get_ifc_georeferencing_info,
            "georeference_ifc_model": self.georeference_ifc_model,
            "generate_ids": self.generate_ids,
        }
        

        handler = handlers.get(cmd_type)
        if handler:
            try:
                print(f"Executing handler for {cmd_type}")
                result = handler(**params)
                print(f"Handler execution complete")
                return {"status": "success", "result": result}
            except Exception as e:
                print(f"Error in handler: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    
    def execute_code(self, code):
        """Execute arbitrary Blender Python code"""
        # This is powerful but potentially dangerous - use with caution
        try:
            # Create a local namespace for execution
            namespace = {"bpy": bpy}
            exec(code, namespace)
            return {"executed": True}
        except Exception as e:
            raise Exception(f"Code execution error: {str(e)}")
        

    @staticmethod
    def get_selected_ifc_entities():
        """
        Get the IFC entities corresponding to the currently selected Blender objects.
        
        Returns:
            List of IFC entities for the selected objects
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            # Get currently selected objects
            selected_objects = bpy.context.selected_objects
            if not selected_objects:
                return {"selected_count": 0, "message": "No objects selected in Blender"}
            
            # Collect IFC entities from selected objects
            selected_entities = []
            for obj in selected_objects:
                if hasattr(obj, "BIMObjectProperties") and obj.BIMObjectProperties.ifc_definition_id:
                    entity_id = obj.BIMObjectProperties.ifc_definition_id
                    entity = file.by_id(entity_id)
                    if entity:
                        entity_info = {
                            "id": entity.GlobalId if hasattr(entity, "GlobalId") else f"Entity_{entity.id()}",
                            "ifc_id": entity.id(),
                            "type": entity.is_a(),
                            "name": entity.Name if hasattr(entity, "Name") else None,
                            "blender_name": obj.name
                        }
                        selected_entities.append(entity_info)
            
            return {
                "selected_count": len(selected_entities),
                "selected_entities": selected_entities
            }
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
        
    ### SPECIFIC IFC METHODS ###
        
    @staticmethod
    def get_ifc_project_info():
        """
        Get basic information about the IFC project.
        
        Returns:
            Dictionary with project name, description, and basic metrics
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            # Get project information
            projects = file.by_type("IfcProject")
            if not projects:
                return {"error": "No IfcProject found in the model"}
            
            project = projects[0]
            
            # Basic project info
            info = {
                "id": project.GlobalId,
                "name": project.Name if hasattr(project, "Name") else "Unnamed Project",
                "description": project.Description if hasattr(project, "Description") else None,
                "entity_counts": {}
            }
            
            # Count entities by type
            entity_types = ["IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcBeam", "IfcColumn", "IfcSpace", "IfcBuildingStorey"]
            for entity_type in entity_types:
                entities = file.by_type(entity_type)
                info["entity_counts"][entity_type] = len(entities)
            
            return info
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    @staticmethod
    def list_ifc_entities(entity_type=None, limit=50, selected_only=False):
        """
        List IFC entities of a specific type.
        
        Parameters:
            entity_type: Type of IFC entity to list (e.g., "IfcWall")
            limit: Maximum number of entities to return
        
        Returns:
            List of entities with basic properties
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            # If we're only looking at selected objects
            if selected_only:
                selected_result = BlenderMCPServer.get_selected_ifc_entities()
                
                # Check for errors
                if "error" in selected_result:
                    return selected_result
                    
                # If no objects are selected, return early
                if selected_result["selected_count"] == 0:
                    return selected_result
                    
                # If entity_type is specified, filter the selected entities
                if entity_type:
                    filtered_entities = [
                        entity for entity in selected_result["selected_entities"]
                        if entity["type"] == entity_type
                    ]
                    
                    return {
                        "type": entity_type,
                        "selected_count": len(filtered_entities),
                        "entities": filtered_entities[:limit]
                    }
                else:
                    # Group selected entities by type
                    entity_types = {}
                    for entity in selected_result["selected_entities"]:
                        entity_type = entity["type"]
                        if entity_type in entity_types:
                            entity_types[entity_type].append(entity)
                        else:
                            entity_types[entity_type] = [entity]
                    
                    return {
                        "selected_count": selected_result["selected_count"],
                        "entity_types": [
                            {"type": t, "count": len(entities), "entities": entities[:limit]}
                            for t, entities in entity_types.items()
                        ]
                    }
            
            # Original functionality for non-selected mode
            if not entity_type:
                # If no type specified, list available entity types
                entity_types = {}
                for entity in file.wrapped_data.entities:
                    entity_type = entity.is_a()
                    if entity_type in entity_types:
                        entity_types[entity_type] += 1
                    else:
                        entity_types[entity_type] = 1
                
                return {
                    "available_types": [{"type": k, "count": v} for k, v in entity_types.items()]
                }
            
            # Get entities of the specified type
            entities = file.by_type(entity_type)
            
            # Prepare the result
            result = {
                "type": entity_type,
                "total_count": len(entities),
                "entities": []
            }
            
            # Add entity data (limited)
            for i, entity in enumerate(entities):
                if i >= limit:
                    break
                    
                entity_data = {
                    "id": entity.GlobalId if hasattr(entity, "GlobalId") else f"Entity_{entity.id()}",
                    "name": entity.Name if hasattr(entity, "Name") else None
                }
                
                result["entities"].append(entity_data)
            
            return result
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    @staticmethod
    def get_ifc_properties(global_id=None, selected_only=False):
        """
        Get all properties of a specific IFC entity.
        
        Parameters:
            global_id: GlobalId of the IFC entity
        
        Returns:
            Dictionary with entity information and properties
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            # If we're only looking at selected objects
            if selected_only:
                selected_result = BlenderMCPServer.get_selected_ifc_entities()
                
                # Check for errors
                if "error" in selected_result:
                    return selected_result
                
                # If no objects are selected, return early
                if selected_result["selected_count"] == 0:
                    return selected_result
                
                # Process each selected entity
                result = {
                    "selected_count": selected_result["selected_count"],
                    "entities": []
                }
                
                for entity_info in selected_result["selected_entities"]:
                    # Find entity by GlobalId
                    entity = file.by_guid(entity_info["id"])
                    if not entity:
                        continue
                    
                    # Get basic entity info
                    entity_data = {
                        "id": entity.GlobalId,
                        "type": entity.is_a(),
                        "name": entity.Name if hasattr(entity, "Name") else None,
                        "description": entity.Description if hasattr(entity, "Description") else None,
                        "blender_name": entity_info["blender_name"],
                        "property_sets": {}
                    }
                    
                    # Get all property sets
                    psets = ifcopenshell.util.element.get_psets(entity)
                    for pset_name, pset_data in psets.items():
                        entity_data["property_sets"][pset_name] = pset_data
                    
                    result["entities"].append(entity_data)
                
                return result
                
            # If we're looking at a specific entity
            elif global_id:
                # Find entity by GlobalId
                entity = file.by_guid(global_id)
                if not entity:
                    return {"error": f"No entity found with GlobalId: {global_id}"}
                
                # Get basic entity info
                entity_info = {
                    "id": entity.GlobalId,
                    "type": entity.is_a(),
                    "name": entity.Name if hasattr(entity, "Name") else None,
                    "description": entity.Description if hasattr(entity, "Description") else None,
                    "property_sets": {}
                }
                
                # Get all property sets
                psets = ifcopenshell.util.element.get_psets(entity)
                for pset_name, pset_data in psets.items():
                    entity_info["property_sets"][pset_name] = pset_data
                
                return entity_info
            else:
                return {"error": "Either global_id or selected_only must be specified"}
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    @staticmethod
    def get_ifc_spatial_structure():
        """
        Get the spatial structure of the IFC model (site, building, storey, space hierarchy).
        
        Returns:
            Hierarchical structure of the IFC model's spatial elements
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            # Start with projects
            projects = file.by_type("IfcProject")
            if not projects:
                return {"error": "No IfcProject found in the model"}
            
            def get_children(parent):
                """Get immediate children of the given element"""
                if hasattr(parent, "IsDecomposedBy"):
                    rel_aggregates = parent.IsDecomposedBy
                    children = []
                    for rel in rel_aggregates:
                        children.extend(rel.RelatedObjects)
                    return children
                return []
                
            def create_structure(element):
                """Recursively create the structure for an element"""
                result = {
                    "id": element.GlobalId,
                    "type": element.is_a(),
                    "name": element.Name if hasattr(element, "Name") else None,
                    "children": []
                }
                
                for child in get_children(element):
                    result["children"].append(create_structure(child))
                
                return result
            
            # Create the structure starting from the project
            structure = create_structure(projects[0])
            
            return structure
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    @staticmethod
    def get_ifc_total_structure():
        """
        Get the complete IFC structure including spatial hierarchy and building elements.
        This function extends the spatial structure to include building elements like walls,
        doors, windows, etc. that are contained in each spatial element.

        Returns:
            Complete hierarchical structure with spatial elements and their contained building elements
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}

            # Start with projects
            projects = file.by_type("IfcProject")
            if not projects:
                return {"error": "No IfcProject found in the model"}

            def get_spatial_children(parent):
                """Get immediate spatial children of the given element"""
                if hasattr(parent, "IsDecomposedBy"):
                    rel_aggregates = parent.IsDecomposedBy
                    children = []
                    for rel in rel_aggregates:
                        children.extend(rel.RelatedObjects)
                    return children
                return []

            def get_contained_elements(spatial_element):
                """Get building elements contained in this spatial element"""
                contained_elements = []

                # Check for IfcRelContainedInSpatialStructure relationships
                if hasattr(spatial_element, "ContainsElements"):
                    for rel in spatial_element.ContainsElements:
                        for element in rel.RelatedElements:
                            element_info = {
                                "id": element.GlobalId,
                                "type": element.is_a(),
                                "name": element.Name if hasattr(element, "Name") else None,
                                "description": element.Description if hasattr(element, "Description") else None
                            }
                            contained_elements.append(element_info)

                return contained_elements

            def create_total_structure(element):
                """Recursively create the complete structure for an element"""
                result = {
                    "id": element.GlobalId,
                    "type": element.is_a(),
                    "name": element.Name if hasattr(element, "Name") else None,
                    "description": element.Description if hasattr(element, "Description") else None,
                    "children": [],
                    "building_elements": []
                }

                # Add spatial children (other spatial elements)
                for child in get_spatial_children(element):
                    result["children"].append(create_total_structure(child))

                # Add contained building elements (walls, doors, windows, etc.)
                result["building_elements"] = get_contained_elements(element)

                return result

            # Create the complete structure starting from the project
            total_structure = create_total_structure(projects[0])

            return total_structure

        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    @staticmethod
    def get_ifc_relationships(global_id):
        """
        Get all relationships for a specific IFC entity.
        
        Parameters:
            global_id: GlobalId of the IFC entity
        
        Returns:
            Dictionary with all relationships the entity participates in
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            # Find entity by GlobalId
            entity = file.by_guid(global_id)
            if not entity:
                return {"error": f"No entity found with GlobalId: {global_id}"}
            
            # Basic entity info
            entity_info = {
                "id": entity.GlobalId,
                "type": entity.is_a(),
                "name": entity.Name if hasattr(entity, "Name") else None,
                "relationships": {
                    "contains": [],
                    "contained_in": [],
                    "connects": [],
                    "connected_by": [],
                    "defines": [],
                    "defined_by": []
                }
            }
            
            # Check if entity contains other elements
            if hasattr(entity, "IsDecomposedBy"):
                for rel in entity.IsDecomposedBy:
                    for obj in rel.RelatedObjects:
                        entity_info["relationships"]["contains"].append({
                            "id": obj.GlobalId,
                            "type": obj.is_a(),
                            "name": obj.Name if hasattr(obj, "Name") else None
                        })
            
            # Check if entity is contained in other elements
            if hasattr(entity, "Decomposes"):
                for rel in entity.Decomposes:
                    rel_obj = rel.RelatingObject
                    entity_info["relationships"]["contained_in"].append({
                        "id": rel_obj.GlobalId,
                        "type": rel_obj.is_a(),
                        "name": rel_obj.Name if hasattr(rel_obj, "Name") else None
                    })
            
            # For physical connections (depends on entity type)
            if hasattr(entity, "ConnectedTo"):
                for rel in entity.ConnectedTo:
                    for obj in rel.RelatedElement:
                        entity_info["relationships"]["connects"].append({
                            "id": obj.GlobalId,
                            "type": obj.is_a(),
                            "name": obj.Name if hasattr(obj, "Name") else None,
                            "connection_type": rel.ConnectionType if hasattr(rel, "ConnectionType") else None
                        })
            
            if hasattr(entity, "ConnectedFrom"):
                for rel in entity.ConnectedFrom:
                    obj = rel.RelatingElement
                    entity_info["relationships"]["connected_by"].append({
                        "id": obj.GlobalId,
                        "type": obj.is_a(),
                        "name": obj.Name if hasattr(obj, "Name") else None,
                        "connection_type": rel.ConnectionType if hasattr(rel, "ConnectionType") else None
                    })
            
            return entity_info
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
        

    @staticmethod
    def export_ifc_data(entity_type=None, level_name=None, output_format="csv"):
        """Export IFC data to a structured file"""
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            data_list = []
            
            # Filter objects based on type
            if entity_type:
                objects = file.by_type(entity_type)
            else:
                objects = file.by_type("IfcElement")
            
            # Create a data dictionary for each object
            for obj in objects:
                obj_data = {}
                
                # Get level/storey information
                container_level = None
                try:
                    containing_structure = ifcopenshell.util.element.get_container(obj)
                    if containing_structure and containing_structure.is_a("IfcBuildingStorey"):
                        container_level = containing_structure.Name
                except Exception as e:
                    pass
                
                # Skip if we're filtering by level and this doesn't match
                if level_name and container_level != level_name:
                    continue
                    
                # Basic information
                obj_data['ExpressId'] = obj.id()
                obj_data['GlobalId'] = obj.GlobalId if hasattr(obj, "GlobalId") else None
                obj_data['IfcClass'] = obj.is_a()
                obj_data['Name'] = obj.Name if hasattr(obj, "Name") else None
                obj_data['Description'] = obj.Description if hasattr(obj, "Description") else None
                obj_data['LevelName'] = container_level
                
                # Get predefined type if available
                try:
                    obj_data['PredefinedType'] = ifcopenshell.util.element.get_predefined_type(obj)
                except:
                    obj_data['PredefinedType'] = None
                    
                # Get type information
                try:
                    type_obj = ifcopenshell.util.element.get_type(obj)
                    obj_data['TypeName'] = type_obj.Name if type_obj and hasattr(type_obj, "Name") else None
                    obj_data['TypeClass'] = type_obj.is_a() if type_obj else None
                except:
                    obj_data['TypeName'] = None
                    obj_data['TypeClass'] = None
                
                # Get property sets (simplify structure for export)
                try:
                    property_sets = ifcopenshell.util.element.get_psets(obj)
                    # Flatten property sets for better export compatibility
                    for pset_name, pset_data in property_sets.items():
                        for prop_name, prop_value in pset_data.items():
                            obj_data[f"{pset_name}.{prop_name}"] = prop_value
                except Exception as e:
                    pass
                    
                data_list.append(obj_data)
            
            if not data_list:
                return "No data found matching the specified criteria"
            
            # Determine output directory - try multiple options to ensure it works in various environments
            output_dirs = [
                "C:\\Users\\Public\\Documents" if os.name == "nt" else None,  # Public Documents
                "/usr/share" if os.name != "nt" else None,  # Unix share directory
                "/tmp",  # Unix temp directory
                "C:\\Temp" if os.name == "nt" else None,  # Windows temp directory
            ]
            
            output_dir = None
            for dir_path in output_dirs:
                if dir_path and os.path.exists(dir_path) and os.access(dir_path, os.W_OK):
                    output_dir = dir_path
                    break
                    
            if not output_dir:
                return {"error": "Could not find a writable directory for output"}
            
            # Create filename based on filters
            filters = []
            if entity_type:
                filters.append(entity_type)
            if level_name:
                filters.append(level_name)
            filter_str = "_".join(filters) if filters else "all"
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"ifc_export_{filter_str}_{timestamp}.{output_format}"
            filepath = os.path.join(output_dir, filename)
            
            # Export based on format
            if output_format == "json":
                with open(filepath, 'w') as f:
                    json.dump(data_list, f, indent=2)
            elif output_format == "csv":
                import pandas as pd
                df = pd.DataFrame(data_list)
                df.to_csv(filepath, index=False)
            
            # Summary info for the response
            entity_count = len(data_list)
            entity_types = set(item['IfcClass'] for item in data_list)
            levels = set(item['LevelName'] for item in data_list if item['LevelName'])
            
            return {
                "success": True,
                "message": f"Data exported successfully to {filepath}",
                "filepath": filepath,
                "format": output_format,
                "summary": {
                    "entity_count": entity_count,
                    "entity_types": list(entity_types),
                    "levels": list(levels)
                }
            }
        
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
        
    
    @staticmethod
    def place_ifc_object(type_name, location, rotation=None):
        """
        Place an IFC object at specified location with optional rotation
        
        Args:
            type_name: Name of the IFC element type
            location: [x, y, z] list or tuple for position
            rotation: Value in degrees for rotation around Z axis (optional)
        
        Returns:
            Dictionary with information about the created object
        """
        try:
            import ifcopenshell
            from bonsai.bim.ifc import IfcStore
            import math
            
            # Convert location to tuple if it's not already
            if isinstance(location, list):
                location = tuple(location)
                
            def find_type_by_name(name):
                file = IfcStore.get_file()
                for element in file.by_type("IfcElementType"):
                    if element.Name == name:
                        return element.id()
                return None

            # Find the type ID
            type_id = find_type_by_name(type_name)
            if not type_id:
                return {"error": f"Type '{type_name}' not found. Please check if this type exists in the model."}
                
            # Store original context
            original_context = bpy.context.copy()
            
            # Ensure we're in 3D View context
            override = bpy.context.copy()
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    override["area"] = area
                    override["region"] = area.regions[-1]
                    break
            
            # Set cursor location
            bpy.context.scene.cursor.location = location
            
            # Get properties to set up parameters
            props = bpy.context.scene.BIMModelProperties
            
            # Store original rl_mode and set to CURSOR to use cursor's Z position
            original_rl_mode = props.rl_mode
            props.rl_mode = 'CURSOR'
            
            # Create the object using the override context
            with bpy.context.temp_override(**override):
                bpy.ops.bim.add_occurrence(relating_type_id=type_id)
            
            # Get the newly created object
            obj = bpy.context.active_object
            if not obj:
                props.rl_mode = original_rl_mode
                return {"error": "Failed to create object"}
            
            # Force the Z position explicitly
            obj.location.z = location[2]
            
            # Apply rotation if provided
            if rotation is not None:
                # Convert degrees to radians for Blender's rotation_euler
                full_rotation = (0, 0, math.radians(float(rotation)))
                obj.rotation_euler = full_rotation
            
            # Sync the changes back to IFC
            # Use the appropriate method depending on what's available
            if hasattr(bpy.ops.bim, "update_representation"):
                bpy.ops.bim.update_representation(obj=obj.name)
            
            # Restore original rl_mode
            props.rl_mode = original_rl_mode
            
            # Get the IFC entity for the new object
            entity_id = obj.BIMObjectProperties.ifc_definition_id
            if entity_id:
                file = IfcStore.get_file()
                entity = file.by_id(entity_id)
                global_id = entity.GlobalId if hasattr(entity, "GlobalId") else None
            else:
                global_id = None
            
            # Return information about the created object
            return {
                "success": True,
                "blender_name": obj.name,
                "global_id": global_id,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "type_name": type_name
            }
            
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
    

    ### Ability to see
    @staticmethod
    def get_current_view():
        """Capture and return the current viewport as an image"""
        try:
            # Find a 3D View
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    break
            else:
                return {"error": "No 3D View available"}
            
            # Create temporary file to save the viewport screenshot
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Find appropriate region
            for region in area.regions:
                if region.type == 'WINDOW':
                    break
            else:
                return {"error": "No appropriate region found in 3D View"}
            
            # Use temp_override instead of the old override dictionary
            with bpy.context.temp_override(area=area, region=region):
                # Save screenshot
                bpy.ops.screen.screenshot(filepath=temp_path)
            
            # Read the image data and encode as base64
            with open(temp_path, 'rb') as f:
                image_data = f.read()
            
            # Clean up
            os.unlink(temp_path)
            
            # Return base64 encoded image
            return {
                "width": area.width,
                "height": area.height,
                "format": "png",
                "data": base64.b64encode(image_data).decode('utf-8')
            }
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}


    @staticmethod
    def get_ifc_quantities(entity_type=None, selected_only=False):
        """
        Calculate and get quantities (m2, m3, etc.) for IFC elements.
        
        Parameters:
            entity_type: Type of IFC entity to get quantities for (e.g., "IfcWall", "IfcSlab")
            selected_only: If True, only get quantities for selected objects
        
        Returns:
            Dictionary with quantities for the specified elements
        """
        try:
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}

            # Check if BaseQuantities already exist to avoid re-calculating
            quantities_exist = False
            sample_elements = file.by_type("IfcElement")[:10] if file.by_type("IfcElement") else []

            for elem in sample_elements:
                psets = ifcopenshell.util.element.get_psets(elem)
                if any(qset in psets for qset in ["BaseQuantities", "Qto_WallBaseQuantities",
                                                   "Qto_SlabBaseQuantities", "Qto_BeamBaseQuantities"]):
                    quantities_exist = True
                    break

            # Only calculate quantities if they don't exist yet
            if not quantities_exist:
                try:
                    bpy.ops.bim.perform_quantity_take_off()
                except Exception as e:
                    return {"error": f"Failed to calculate quantities: {str(e)}"}

            elements_data = []
            
            # If we're only looking at selected objects
            if selected_only:
                selected_result = BlenderMCPServer.get_selected_ifc_entities()
                
                # Check for errors
                if "error" in selected_result:
                    return selected_result
                
                # If no objects are selected, return early
                if selected_result["selected_count"] == 0:
                    return selected_result
                
                # Process each selected entity
                for entity_info in selected_result["selected_entities"]:
                    # Find entity by GlobalId
                    entity = file.by_guid(entity_info["id"])
                    if not entity:
                        continue
                    
                    # Filter by type if specified
                    if entity_type and entity.is_a() != entity_type:
                        continue
                    
                    # Extract quantities
                    element_data = extract_quantities(entity, entity_info["blender_name"])
                    if element_data:
                        elements_data.append(element_data)
                        
            else:
                # Get entities based on type or default to common element types
                if entity_type:
                    entities = file.by_type(entity_type)
                else:
                    # Get common element types that have quantities
                    entity_types = ["IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", "IfcWindow"]
                    entities = []
                    for etype in entity_types:
                        entities.extend(file.by_type(etype))
                
                # Process each entity
                for entity in entities:
                    element_data = extract_quantities(entity)
                    if element_data:
                        elements_data.append(element_data)
            
            # Summary statistics
            summary = {
                "total_elements": len(elements_data),
                "element_types": {}
            }
            
            # Group by element type for summary
            for element in elements_data:
                etype = element["type"]
                if etype not in summary["element_types"]:
                    summary["element_types"][etype] = {"count": 0, "total_area": 0, "total_volume": 0}
                
                summary["element_types"][etype]["count"] += 1
                if element["quantities"].get("area"):
                    summary["element_types"][etype]["total_area"] += element["quantities"]["area"]
                if element["quantities"].get("volume"):
                    summary["element_types"][etype]["total_volume"] += element["quantities"]["volume"]
            
            return {
                "success": True,
                "elements": elements_data,
                "summary": summary
            }
            
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def export_drawing_png(view_type="top", height_offset=0.5, resolution_x=1920, 
                             resolution_y=1080, storey_name=None, output_path=None):
        """
        Export drawings as PNG images with custom resolution.
        
        Creates 2D and 3D views of IFC building, particularly useful for architectural drawings.
        
        Args:
            view_type: "top" for plan view, "front", "right", "left" for elevations, "isometric" for 3D view
            height_offset: Height in meters above storey level for camera position  
            resolution_x: Horizontal resolution in pixels
            resolution_y: Vertical resolution in pixels
            storey_name: Specific storey name to render (None for all/ground floor)
            output_path: File path to save PNG (None for temp file)
        
        Returns:
            Dict with base64 encoded image data and metadata
        """
        try:
            import tempfile
            import os
            
            # Validate parameters
            if resolution_x > 4096 or resolution_y > 4096:
                return {"error": "Resolution too high. Maximum: 4096x4096"}
            
            if resolution_x < 100 or resolution_y < 100:
                return {"error": "Resolution too low. Minimum: 100x100"}
            
            # Check if IFC file is loaded
            file = IfcStore.get_file()
            if file is None:
                return {"error": "No IFC file is currently loaded"}
            
            # Store original render settings
            scene = bpy.context.scene
            original_engine = scene.render.engine
            original_res_x = scene.render.resolution_x
            original_res_y = scene.render.resolution_y
            original_filepath = scene.render.filepath
            
            # Set up render settings for drawing
            scene.render.engine = 'BLENDER_WORKBENCH'  # Fast, good for architectural drawings
            scene.render.resolution_x = resolution_x
            scene.render.resolution_y = resolution_y
            scene.render.resolution_percentage = 100
            
            # Store original camera if exists
            original_camera = bpy.context.scene.camera
            
            # Create temporary camera for orthographic rendering
            bpy.ops.object.camera_add()
            camera = bpy.context.object
            camera.name = "TempDrawingCamera"
            bpy.context.scene.camera = camera
            
            # Set camera to orthographic
            camera.data.type = 'ORTHO'
            camera.data.ortho_scale = 50  # Adjust based on building size
            
            # Position camera based on view type and storey
            if view_type == "top":
                # Find building bounds to position camera appropriately
                all_objects = [obj for obj in bpy.context.scene.objects 
                              if obj.type == 'MESH' and obj.visible_get()]
                
                if all_objects:
                    # Calculate bounding box of all visible objects
                    min_x = min_y = min_z = float('inf')
                    max_x = max_y = max_z = float('-inf')
                    
                    for obj in all_objects:
                        bbox = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
                        for corner in bbox:
                            min_x = min(min_x, corner.x)
                            max_x = max(max_x, corner.x)
                            min_y = min(min_y, corner.y)  
                            max_y = max(max_y, corner.y)
                            min_z = min(min_z, corner.z)
                            max_z = max(max_z, corner.z)
                    
                    # Position camera above the building
                    center_x = (min_x + max_x) / 2
                    center_y = (min_y + max_y) / 2
                    
                    # For plan view, position camera above
                    camera_height = max_z + height_offset
                    camera.location = (center_x, center_y, camera_height)
                    camera.rotation_euler = (0, 0, 0)  # Look down
                    
                    # Adjust orthographic scale based on building size
                    building_width = max(max_x - min_x, max_y - min_y) * 1.2  # Add 20% margin
                    camera.data.ortho_scale = building_width
                else:
                    # Default position if no objects found
                    camera.location = (0, 0, 10)
                    camera.rotation_euler = (0, 0, 0)
            
            elif view_type in ["front", "right", "left"]:
                # For elevations, position camera accordingly
                # This is a simplified implementation - could be enhanced
                all_objects = [obj for obj in bpy.context.scene.objects 
                              if obj.type == 'MESH' and obj.visible_get()]
                
                if all_objects:
                    # Calculate bounds
                    min_x = min_y = min_z = float('inf')
                    max_x = max_y = max_z = float('-inf')
                    
                    for obj in all_objects:
                        bbox = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
                        for corner in bbox:
                            min_x = min(min_x, corner.x)
                            max_x = max(max_x, corner.x)
                            min_y = min(min_y, corner.y)
                            max_y = max(max_y, corner.y)
                            min_z = min(min_z, corner.z)
                            max_z = max(max_z, corner.z)
                    
                    center_x = (min_x + max_x) / 2
                    center_y = (min_y + max_y) / 2
                    center_z = (min_z + max_z) / 2
                    
                    building_depth = max(max_x - min_x, max_y - min_y) * 2
                    
                    if view_type == "front":
                        camera.location = (center_x, center_y - building_depth, center_z)
                        camera.rotation_euler = (1.5708, 0, 0)  # 90 degrees X rotation
                    elif view_type == "right":
                        camera.location = (center_x + building_depth, center_y, center_z)
                        camera.rotation_euler = (1.5708, 0, 1.5708)  # Look from right
                    elif view_type == "left":
                        camera.location = (center_x - building_depth, center_y, center_z)
                        camera.rotation_euler = (1.5708, 0, -1.5708)  # Look from left
                    
                    # Adjust scale for elevations
                    building_height = max_z - min_z
                    building_width = max(max_x - min_x, max_y - min_y)
                    camera.data.ortho_scale = max(building_height, building_width) * 1.2
            
            elif view_type == "isometric":
                # For isometric view, use perspective camera positioned diagonally
                camera.data.type = 'PERSP'
                camera.data.lens = 35  # 35mm lens for nice perspective
                
                all_objects = [obj for obj in bpy.context.scene.objects 
                              if obj.type == 'MESH' and obj.visible_get()]
                
                if all_objects:
                    # Calculate bounds
                    min_x = min_y = min_z = float('inf')
                    max_x = max_y = max_z = float('-inf')
                    
                    for obj in all_objects:
                        bbox = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
                        for corner in bbox:
                            min_x = min(min_x, corner.x)
                            max_x = max(max_x, corner.x)
                            min_y = min(min_y, corner.y)
                            max_y = max(max_y, corner.y)
                            min_z = min(min_z, corner.z)
                            max_z = max(max_z, corner.z)
                    
                    center_x = (min_x + max_x) / 2
                    center_y = (min_y + max_y) / 2
                    center_z = (min_z + max_z) / 2
                    
                    # Calculate distance to frame the building nicely
                    building_size = max(max_x - min_x, max_y - min_y, max_z - min_z)
                    distance = building_size * 1.2  # Distance multiplier for good framing
                    
                    # Position camera for isometric view (45° angles)
                    # Classic isometric position: up and back, looking down at 30°
                    import math
                    angle_rad = math.radians(45)
                    
                    camera_x = center_x + distance * math.cos(angle_rad)
                    camera_y = center_y - distance * math.sin(angle_rad)
                    camera_z = center_z + distance * 0.3  # Lower elevation for better facade view
                    
                    camera.location = (camera_x, camera_y, camera_z)
                    
                    # Point camera at building center
                    direction = mathutils.Vector((center_x - camera_x, center_y - camera_y, center_z - camera_z))
                    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
                else:
                    # Default isometric position
                    camera.location = (15, -15, 10)
                    camera.rotation_euler = (1.1, 0, 0.785)  # ~63°, 0°, ~45°
            
            # Set up output file path
            if output_path:
                render_path = output_path
            else:
                temp_dir = tempfile.gettempdir()
                render_path = os.path.join(temp_dir, f"drawing_{view_type}_{int(time.time())}.png")
            
            scene.render.filepath = render_path
            scene.render.image_settings.file_format = 'PNG'
            
            # Render the image
            bpy.ops.render.render(write_still=True)
            
            # Read the rendered image and encode as base64
            if os.path.exists(render_path):
                with open(render_path, 'rb') as f:
                    image_data = f.read()
                
                # Clean up temporary file if we created it
                if not output_path:
                    os.remove(render_path)
                
                # Restore original settings
                scene.render.engine = original_engine
                scene.render.resolution_x = original_res_x
                scene.render.resolution_y = original_res_y
                scene.render.filepath = original_filepath
                bpy.context.scene.camera = original_camera
                
                # Delete temporary camera
                bpy.data.objects.remove(camera, do_unlink=True)
                
                # Return base64 encoded image
                import base64
                return {
                    "success": True,
                    "data": base64.b64encode(image_data).decode('utf-8'),
                    "format": "png",
                    "resolution": f"{resolution_x}x{resolution_y}",
                    "view_type": view_type,
                    "output_path": render_path if output_path else None
                }
            else:
                return {"error": "Failed to create render file"}
                
        except Exception as e:
            # Restore settings on error
            try:
                scene = bpy.context.scene
                scene.render.engine = original_engine
                scene.render.resolution_x = original_res_x
                scene.render.resolution_y = original_res_y 
                scene.render.filepath = original_filepath
                bpy.context.scene.camera = original_camera
                
                # Clean up camera if it exists
                if 'camera' in locals() and camera:
                    bpy.data.objects.remove(camera, do_unlink=True)
            except:
                pass
                
            import traceback
            return {"error": f"Error creating drawing: {str(e)}", 
                    "traceback": traceback.format_exc()}

    @staticmethod
    def get_ifc_georeferencing_info(include_contexts: bool = False):
        """
        Retrieves georeferencing information from the currently opened IFC file (CRS, MapConversion, WCS, TrueNorth, IfcSite).

        Args:
            include_contexts (bool): If True, adds the breakdown of RepresentationContexts and operations

        Returns:
            dict: Structure with:
            {
            "georeferenced": bool,
            "crs": {
                "name": str|None,
                "geodetic_datum": str|None,
                "vertical_datum": str|None,
                "map_unit": str|None
            },
            "map_conversion": {
                "eastings": float|None,
                "northings": float|None,
                "orthogonal_height": float|None,
                "scale": float|None,
                "x_axis_abscissa": float|None,
                "x_axis_ordinate": float|None
            },
            "world_coordinate_system": {"origin": [x,y,z]|None},
            "true_north": {"direction_ratios": [x,y]|None},
            "site": {
                "local_placement_origin": [x,y,z]|None,
                "ref_latitude": [deg,min,sec,millionth]|None,
                "ref_longitude": [deg,min,sec,millionth]|None,
                "ref_elevation": float|None
            },
            "contexts": [...],     # only if include_contexts=True
            "warnings": [...]
            }
        """
        try:
                        
            file = IfcStore.get_file()
            debug = {"entered": True, "has_ifc": file is not None, "projects": 0, "sites": 0, "contexts": 0}
            if file is None:
                return {"error": "No IFC file is currently loaded", "debug": debug}

            warnings = []
            result = {
                "georeferenced": False,
                "crs": {
                    "name": None,
                    "geodetic_datum": None,
                    "vertical_datum": None,
                    "map_unit": None
                },
                "map_conversion": {
                    "eastings": None,
                    "northings": None,
                    "orthogonal_height": None,
                    "scale": None,
                    "x_axis_abscissa": None,
                    "x_axis_ordinate": None
                },
                "world_coordinate_system": {"origin": None},
                "true_north": {"direction_ratios": None},
                "site": {
                    "local_placement_origin": None,
                    "ref_latitude": None,
                    "ref_longitude": None,
                    "ref_elevation": None
                },
                "contexts": [],
                "warnings": warnings,
                "debug":debug,
            }

            # --- IfcProject & RepresentationContexts ---
            projects = file.by_type("IfcProject")
            debug["projects"] = len(projects)
            if projects:
                project = projects[0]
                contexts = getattr(project, "RepresentationContexts", None) or []
                debug["contexts"] = len(contexts)
                for ctx in contexts:
                    ctx_entry = {
                        "context_identifier": getattr(ctx, "ContextIdentifier", None),
                        "context_type": getattr(ctx, "ContextType", None),
                        "world_origin": None,
                        "true_north": None,
                        "has_coordinate_operation": []
                    }

                    # WorldCoordinateSystem → Local origin
                    try:
                        wcs = getattr(ctx, "WorldCoordinateSystem", None)
                        if wcs and getattr(wcs, "Location", None):
                            loc = wcs.Location
                            if getattr(loc, "Coordinates", None):
                                coords = list(loc.Coordinates)
                                result["world_coordinate_system"]["origin"] = coords
                                ctx_entry["world_origin"] = coords
                    except Exception as e:
                        warnings.append(f"WorldCoordinateSystem read error: {str(e)}")

                    # TrueNorth
                    try:
                        if hasattr(ctx, "TrueNorth") and ctx.TrueNorth:
                            tn = ctx.TrueNorth
                            ratios = list(getattr(tn, "DirectionRatios", []) or [])
                            result["true_north"]["direction_ratios"] = ratios
                            ctx_entry["true_north"] = ratios
                    except Exception as e:
                        warnings.append(f"TrueNorth read error: {str(e)}")

                    # HasCoordinateOperation → IfcMapConversion / TargetCRS
                    try:
                        if hasattr(ctx, "HasCoordinateOperation") and ctx.HasCoordinateOperation:
                            for op in ctx.HasCoordinateOperation:
                                op_entry = {"type": op.is_a(), "target_crs": None, "map_conversion": None}

                                # TargetCRS
                                crs = getattr(op, "TargetCRS", None)
                                if crs:
                                    result["crs"]["name"] = getattr(crs, "Name", None)
                                    result["crs"]["geodetic_datum"] = getattr(crs, "GeodeticDatum", None)
                                    result["crs"]["vertical_datum"] = getattr(crs, "VerticalDatum", None)
                                    try:
                                        map_unit = getattr(crs, "MapUnit", None)
                                        result["crs"]["map_unit"] = map_unit.Name if map_unit else None
                                    except Exception:
                                        result["crs"]["map_unit"] = None

                                    op_entry["target_crs"] = {
                                        "name": result["crs"]["name"],
                                        "geodetic_datum": result["crs"]["geodetic_datum"],
                                        "vertical_datum": result["crs"]["vertical_datum"],
                                        "map_unit": result["crs"]["map_unit"]
                                    }

                                # IfcMapConversion
                                if op.is_a("IfcMapConversion"):
                                    mc = {
                                        "eastings": getattr(op, "Eastings", None),
                                        "northings": getattr(op, "Northings", None),
                                        "orthogonal_height": getattr(op, "OrthogonalHeight", None),
                                        "scale": getattr(op, "Scale", None),
                                        "x_axis_abscissa": getattr(op, "XAxisAbscissa", None),
                                        "x_axis_ordinate": getattr(op, "XAxisOrdinate", None)
                                    }
                                    result["map_conversion"].update(mc)
                                    op_entry["map_conversion"] = mc

                                ctx_entry["has_coordinate_operation"].append(op_entry)
                    except Exception as e:
                        warnings.append(f"HasCoordinateOperation read error: {str(e)}")

                    if include_contexts:
                        result["contexts"].append(ctx_entry)
            else:
                warnings.append("IfcProject entity was not found.")

            # --- IfcSite (lat/long/alt local origin of placement) ---
            try:
                sites = file.by_type("IfcSite")
                debug["sites"] = len(sites)
                if sites:
                    site = sites[0]
                    # LocalPlacement
                    try:
                        if getattr(site, "ObjectPlacement", None):
                            placement = site.ObjectPlacement
                            axisPlacement = getattr(placement, "RelativePlacement", None)
                            if axisPlacement and getattr(axisPlacement, "Location", None):
                                loc = axisPlacement.Location
                                if getattr(loc, "Coordinates", None):
                                    result["site"]["local_placement_origin"] = list(loc.Coordinates)
                    except Exception as e:
                        warnings.append(f"IfcSite.ObjectPlacement read error: {str(e)}")

                    # Lat/Long/Alt
                    try:
                        lat = getattr(site, "RefLatitude", None)
                        lon = getattr(site, "RefLongitude", None)
                        ele = getattr(site, "RefElevation", None)
                        result["site"]["ref_latitude"]  = list(lat) if lat else None
                        result["site"]["ref_longitude"] = list(lon) if lon else None
                        result["site"]["ref_elevation"] = ele
                    except Exception as e:
                        warnings.append(f"IfcSite (lat/long/elev) read error: {str(e)}")
                else:
                    warnings.append("IfcSite was not found.")
            except Exception as e:
                warnings.append(f"Error while querying IfcSite: {str(e)}")

            # --- Heuristic to determine georeferencing ---
            geo_flags = [
                any(result["crs"].values()),
                any(v is not None for v in result["map_conversion"].values())          
            ]
            result["georeferenced"] = all(geo_flags)

            return result

        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()} 
    
    @staticmethod
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
        site_ref_latitude: list = None,         # IFC format [deg, min, sec, millionth]
        site_ref_longitude: list = None,        # IFC format [deg, min, sec, millionth]
        site_ref_elevation: float = None,
        site_ref_latitude_dd: float = None,     # Decimal degrees (optional)
        site_ref_longitude_dd: float = None,    # Decimal degrees (optional)
        overwrite: bool = False,
        dry_run: bool = False,
        write_path: str = None,
    ):
        """
        Usage:
        Creates/updates IfcProjectedCRS + IfcMapConversion in the opened IFC.
        Optionally updates IfcSite.RefLatitude/RefLongitude/RefElevation.
        If `pyproj` is available, it can convert Lat/Long (degrees) ⇄ E/N (meters)
        according to the given EPSG.

        Requirements:
        CRS declaration is ALWAYS required:
        - crs_mode="epsg" + epsg=XXXX    OR
        - crs_mode="custom" + (crs_name, geodetic_datum, map_projection [, map_zone])

        Minimum MapConversion information:
        - eastings + northings
        (if missing but lat/long + EPSG + pyproj are available, they are computed)
        """
        import math
        from bonsai.bim.ifc import IfcStore
        file = IfcStore.get_file()
        if file is None:
            return {"success": False, "error": "No IFC file is currently loaded"}

        warnings = []
        actions = {"created_crs": False, "created_map_conversion": False,
                "updated_map_conversion": False, "updated_site": False,
                "overwrote": False, "wrote_file": False}
        debug = {}

        # ---------- helpers ----------
        def dd_to_ifc_dms(dd: float):
            """Converts decimal degrees to [deg, min, sec, millionth] (sign carried by degrees)."""
            if dd is None:
                return None
            sign = -1 if dd < 0 else 1
            v = abs(dd)
            deg = int(v)
            rem = (v - deg) * 60
            minutes = int(rem)
            sec_float = (rem - minutes) * 60
            seconds = int(sec_float)
            millionth = int(round((sec_float - seconds) * 1_000_000))
            # Normalizes rounding (e.g. 59.999999 → 60)
            if millionth == 1_000_000:
                seconds += 1
                millionth = 0
            if seconds == 60:
                minutes += 1
                seconds = 0
            if minutes == 60:
                deg += 1
                minutes = 0
            return [sign * deg, minutes, seconds, millionth]

        def select_context():
            ctxs = file.by_type("IfcGeometricRepresentationContext") or []
            if not ctxs:
                return None, "No IfcGeometricRepresentationContext found"
            if context_index is not None and 0 <= context_index < len(ctxs):
                return ctxs[context_index], None
            # By filter (default "Model", case-insensitive)
            if context_filter:
                for c in ctxs:
                    if (getattr(c, "ContextType", None) or "").lower() == context_filter.lower():
                        return c, None
            # Fallback to the first one
            return ctxs[0], None

        # ---------- 1) CRS Validation ----------
        if crs_mode not in ("epsg", "custom"):
            return {"success": False, "error": "crs_mode must be 'epsg' or 'custom'"}

        if crs_mode == "epsg":
            if not epsg:
                return {"success": False, "error": "epsg code required when crs_mode='epsg'"}
            crs_name_final = f"EPSG:{epsg}"
            geodetic_datum = geodetic_datum or "WGS84"
            map_projection = map_projection or "TransverseMercator"  # usual UTM
            # map_zone is optional
        else:
            # custom
            missing = [k for k in ("crs_name", "geodetic_datum", "map_projection") if locals().get(k) in (None, "")]
            if missing:
                return {"success": False, "error": f"Missing fields for custom CRS: {', '.join(missing)}"}
            crs_name_final = crs_name

        # ---------- 2) Complete E/N from Lat/Long (if missing and pyproj is available) ----------
        proj_used = None
        try:
            if (eastings is None or northings is None) and (site_ref_latitude_dd is not None and site_ref_longitude_dd is not None) and crs_mode == "epsg":
                try:
                    from pyproj import Transformer
                    # Assume lat/long in WGS84; if the EPSG is not WGS84-derived, pyproj handles the conversion
                    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
                    e, n = transformer.transform(site_ref_longitude_dd, site_ref_latitude_dd)
                    eastings = e if eastings is None else eastings
                    northings = n if northings is None else northings
                    proj_used = f"EPSG:4326->EPSG:{epsg}"
                except Exception as _e:
                    warnings.append(f"Could not convert Lat/Long to E/N: {_e}. Provide eastings/northings manually.")
        except Exception as _e:
            warnings.append(f"pyproj not available to compute E/N: {_e}. Provide eastings/northings manually.")

        # ---------- E/N Validation ----------
        if eastings is None or northings is None:
            return {"success": False, "error": "eastings and northings are required (or provide lat/long + EPSG with pyproj installed)"}

        # ---------- 3) Select context ----------
        context, ctx_err = select_context()
        if not context:
            return {"success": False, "error": ctx_err or "No context found"}

        # ---------- 4) Detect existing ones and handle overwrite ----------
        # Inverse: context.HasCoordinateOperation is already handled by ifcopenshell as an attribute
        existing_ops = list(getattr(context, "HasCoordinateOperation", []) or [])
        existing_map = None
        existing_crs = None
        for op in existing_ops:
            if op.is_a("IfcMapConversion"):
                existing_map = op
                existing_crs = getattr(op, "TargetCRS", None)
                break

        if existing_map and not overwrite:
            return {
                "success": True,
                "georeferenced": True,
                "message": "MapConversion already exists. Use overwrite=True to replace it.",
                "context_used": {"identifier": getattr(context, "ContextIdentifier", None), "type": getattr(context, "ContextType", None)},
                "map_conversion": {
                    "eastings": getattr(existing_map, "Eastings", None),
                    "northings": getattr(existing_map, "Northings", None),
                    "orthogonal_height": getattr(existing_map, "OrthogonalHeight", None),
                    "scale": getattr(existing_map, "Scale", None),
                    "x_axis_abscissa": getattr(existing_map, "XAxisAbscissa", None),
                    "x_axis_ordinate": getattr(existing_map, "XAxisOrdinate", None),
                },
                "crs": {
                    "name": getattr(existing_crs, "Name", None) if existing_crs else None,
                    "geodetic_datum": getattr(existing_crs, "GeodeticDatum", None) if existing_crs else None,
                    "map_projection": getattr(existing_crs, "MapProjection", None) if existing_crs else None,
                    "map_zone": getattr(existing_crs, "MapZone", None) if existing_crs else None,
                },
                "warnings": warnings,
                "actions": actions,
            }

        # ---------- 5) Build/Update CRS ----------
        if existing_crs and overwrite:
            actions["overwrote"] = True
            try:
                file.remove(existing_crs)
            except Exception:
                warnings.append("Could not remove the existing CRS; a new one will be created anyway.")

        # If custom, use the provided values; if EPSG, build the name and defaults
        crs_kwargs = {
            "Name": crs_name_final,
            "GeodeticDatum": geodetic_datum,
            "MapProjection": map_projection,
        }
        if map_zone:
            crs_kwargs["MapZone"] = map_zone

        crs_entity = file.create_entity("IfcProjectedCRS", **crs_kwargs)
        actions["created_crs"] = True

        # ---------- 6) Calculate orientation (optional) ----------
        # If true_north_azimuth_deg is given as the azimuth from North (model +Y axis) towards East (clockwise),
        # We can derive an approximate X vector: X = (cos(az+90°), sin(az+90°)).
        if (x_axis_abscissa is None or x_axis_ordinate is None) and (true_north_azimuth_deg is not None):
            az = math.radians(true_north_azimuth_deg)
            # Estimated X vector rotated 90° from North:
            x_axis_abscissa = math.cos(az + math.pi / 2.0)
            x_axis_ordinate = math.sin(az + math.pi / 2.0)

        # Defaults if still missing
        x_axis_abscissa = 1.0 if x_axis_abscissa is None else float(x_axis_abscissa)
        x_axis_ordinate = 0.0 if x_axis_ordinate is None else float(x_axis_ordinate)
        scale = 1.0 if scale is None else float(scale)
        orthogonal_height = 0.0 if orthogonal_height is None else float(orthogonal_height)

        # ---------- 7) Build/Update IfcMapConversion ----------
        if existing_map and overwrite:
            try:
                file.remove(existing_map)
            except Exception:
                warnings.append("Could not remove the existing MapConversion; another one will be created anyway.")

        map_kwargs = {
            "SourceCRS": context,
            "TargetCRS": crs_entity,
            "Eastings": float(eastings),
            "Northings": float(northings),
            "OrthogonalHeight": float(orthogonal_height),
            "XAxisAbscissa": float(x_axis_abscissa),
            "XAxisOrdinate": float(x_axis_ordinate),
            "Scale": float(scale),
        }
        map_entity = file.create_entity("IfcMapConversion", **map_kwargs)
        actions["created_map_conversion"] = True

        # ---------- 8) (Optional) Update IfcSite ----------
        try:
            sites = file.by_type("IfcSite") or []
            if sites:
                site = sites[0]
                # If no IFC lists are provided but decimal degrees are, convert them
                if site_ref_latitude is None and site_ref_latitude_dd is not None:
                    site_ref_latitude = dd_to_ifc_dms(site_ref_latitude_dd)
                if site_ref_longitude is None and site_ref_longitude_dd is not None:
                    site_ref_longitude = dd_to_ifc_dms(site_ref_longitude_dd)

                changed = False
                if site_ref_latitude is not None:
                    site.RefLatitude = site_ref_latitude
                    changed = True
                if site_ref_longitude is not None:
                    site.RefLongitude = site_ref_longitude
                    changed = True
                if site_ref_elevation is not None:
                    site.RefElevation = float(site_ref_elevation)
                    changed = True
                if changed:
                    actions["updated_site"] = True
            else:
                warnings.append("No IfcSite found; lat/long/elevation were not updated.")
        except Exception as e:
            warnings.append(f"Could not update IfcSite: {e}")

        # ---------- 9) (Optional) Save ----------
        if write_path and not dry_run:
            try:
                file.write(write_path)
                actions["wrote_file"] = True
            except Exception as e:
                warnings.append(f"Could not write IFC to'{write_path}': {e}")

        # ---------- 10) Response ----------
        return {
            "success": True,
            "georeferenced": True,
            "crs": {
                "name": getattr(crs_entity, "Name", None),
                "geodetic_datum": getattr(crs_entity, "GeodeticDatum", None),
                "map_projection": getattr(crs_entity, "MapProjection", None),
                "map_zone": getattr(crs_entity, "MapZone", None),
            },
            "map_conversion": {
                "eastings": float(eastings),
                "northings": float(northings),
                "orthogonal_height": float(orthogonal_height),
                "scale": float(scale),
                "x_axis_abscissa": float(x_axis_abscissa),
                "x_axis_ordinate": float(x_axis_ordinate),
            },
            "context_used": {
                "identifier": getattr(context, "ContextIdentifier", None),
                "type": getattr(context, "ContextType", None),
            },
            "site": {
                "ref_latitude": site_ref_latitude,
                "ref_longitude": site_ref_longitude,
                "ref_elevation": site_ref_elevation,
            },
            "proj_used": proj_used,
            "warnings": warnings,
            "actions": actions,
        }
    
    @staticmethod
    def generate_ids(
        title: str,
        specs: list,
        description: str = "",
        author: str = "",
        ids_version: str = "",
        purpose: str = "",
        milestone: str = "",
        output_path: str = None,
        date_iso: str = None,
    ):
        """
        Generates an .ids file with robust handling of:
            - Synonyms: 'name' → 'baseName', 'minValue/maxValue' + inclusivity, 'minOccurs/maxOccurs' → cardinality.
            - Operators inside 'value' ("> 30", "≤0.45"), in keys (op/target/threshold/limit), and extracted from 'description'
            (ONLY within requirements; never in applicability).
            - Correct restriction mapping:
                * Numeric → ids.Restriction(base="double" | "integer", options={...})
                * Textual (IFCLABEL/TEXT) → ids.Restriction(base="string", options={"pattern": [anchored regexes]})
            - Automatic dataType inference with hints 
            (ThermalTransmittance → IFCTHERMALTRANSMITTANCEMEASURE, IsExternal → IFCBOOLEAN, etc.).
            - PredefinedType remains as an Attribute within APPLICABILITY 
            (NOT absorbed into Entity.predefinedType).
        """
        
        #Libraries/Dependencies
        # -----------------------------------------------------------------------------------------------------------
        try:
            from ifctester import ids
        except Exception as e:
            return {"ok": False, "error": "Could not import ifctester.ids", "details": str(e)}

        import os, datetime, re
        from numbers import Number

        #Validations
        # -----------------------------------------------------------------------------------------------------------    
        if not isinstance(title, str) or not title.strip():
            return {"ok": False, "error": "Invalid or empty 'title' parameter."}
        if not isinstance(specs, list) or len(specs) == 0:
            return {"ok": False, "error": "You must provide at least one specification in 'specs'."}

        # Utils
        # -----------------------------------------------------------------------------------------------------------
        def _norm_card(c):
            """
            Usage:
                Normalizes the given cardinality value, ensuring it matches one of the valid terms.
            Inputs:
                c (str | None): Cardinality value to normalize. Can be 'required', 'optional', or 'prohibited'.
            Output:
                str | None: Normalized lowercase value if valid, or None if not provided.
            Exceptions:
                ValueError: Raised if the input value does not correspond to a valid cardinality.
            """
            if c is None: return None
            c = str(c).strip().lower()
            if c in ("required", "optional", "prohibited"): return c
            raise ValueError("Invalid cardinality: use 'required', 'optional', or 'prohibited'.")

        def _card_from_occurs(minOccurs, maxOccurs):
            """
            Usage:
                Derives the cardinality ('required' or 'optional') based on the values of minOccurs and maxOccurs.
            Inputs:
                minOccurs (int | str | None): Minimum number of occurrences. If greater than 0, the field is considered 'required'.
                maxOccurs (int | str | None): Maximum number of occurrences. Not used directly, included for completeness.
            Output:
                str | None: Returns 'required' if minOccurs > 0, 'optional' if minOccurs == 0, or None if conversion fails.
            """
            try:
                if minOccurs is None: return None
                m = int(minOccurs)
                return "required" if m > 0 else "optional"
            except Exception:
                return None

        def _is_bool_like(v):
            """
            Usage:
                Checks whether a given value can be interpreted as a boolean.
            Inputs:
                v (any): Value to evaluate. Can be of any type (bool, str, int, etc.).
            Output:
                bool: Returns True if the value represents a boolean-like token 
                    (e.g., True, False, "yes", "no", "1", "0", "y", "n", "t", "f"), 
                    otherwise returns False.
            """
            if isinstance(v, bool): return True
            if v is None: return False
            s = str(v).strip().lower()
            return s in ("true", "false", "1", "0", "yes", "no", "y", "n", "t", "f")

        def _to_bool_token(v):
            """
            Usage:
                Converts a boolean-like value into a standardized string token ("TRUE" or "FALSE").
            Inputs:
                v (any): Value to convert. Can be a boolean, string, or numeric value representing truthiness.
            Output:
                str | None: Returns "TRUE" or "FALSE" if the value matches a recognized boolean pattern,
                            or None if it cannot be interpreted as boolean.
            """        
            if isinstance(v, bool): return "TRUE" if v else "FALSE"
            s = str(v).strip().lower()
            if s in ("true", "1", "yes", "y", "t"): return "TRUE"
            if s in ("false", "0", "no", "n", "f"): return "FALSE"
            return None

        # Hints for *MEASURE* types and by property name
        MEASURE_HINTS = {
            "THERMALTRANSMITTANCE": "IFCTHERMALTRANSMITTANCEMEASURE",
            "UVALUE": "IFCTHERMALTRANSMITTANCEMEASURE",
            "RATIOMEASURE": "IFCRATIOMEASURE",
            "AREAMEASURE": "IFCAREAMEASURE",
            "LENGTHMEASURE": "IFCLENGTHMEASURE",
            "SOUNDPRESSURELEVELMEASURE": "IFCSOUNDPRESSURELEVELMEASURE",
        }
        PROPERTY_DATATYPE_HINTS = {
            "THERMALTRANSMITTANCE": "IFCTHERMALTRANSMITTANCEMEASURE",
            "ISEXTERNAL": "IFCBOOLEAN",
            "ACOUSTICRATING": "IFCLABEL",
        }

        def _norm_ifc_version(v: str | None) -> str | None:
            """
            Usage:
                Normalizes the given IFC schema version string to a standardized format.
            Inputs:
                v (str | None): Input version value (e.g., "4", "IFC 4", "2x3", "IFC4.3").
            Output:
                str | None: Returns the normalized IFC version (e.g., "IFC4", "IFC2X3", "IFC4X3"),
                            or None if the input is empty or invalid.
            """
            if not v: return None
            s = str(v).strip().upper()
            m = {"4": "IFC4", "IFC 4": "IFC4", "2X3": "IFC2X3", "IFC 2X3": "IFC2X3", "IFC4.3": "IFC4X3"}
            return m.get(s, s)

        def _strip_ifc_prefix(dt: str | None) -> str | None:
            """
            Usage:
                Removes leading and trailing spaces from the given string and converts it to uppercase.
                Typically used to normalize IFC data type names.
            Inputs:
                dt (str | None): Data type string to normalize (e.g., " ifcreal ").
            Output:
                str | None: Uppercase, trimmed string (e.g., "IFCREAL"), or None if the input is empty or None.
            """       
            return dt.strip().upper() if dt else None

        def _is_number_like(v) -> bool:
            """
            Usage:
                Checks whether the given value can be interpreted as a numeric value.
            Inputs:
                v (any): Value to evaluate. Can be of any type (int, float, str, etc.).
            Output:
                bool: Returns True if the value represents a number (including numeric strings like "3.5" or "2,7"),
                    otherwise returns False.
            """
            if isinstance(v, Number): return True
            if v is None: return False
            try:
                float(str(v).strip().replace(",", "."))
                return True
            except Exception:
                return False

        def _guess_numeric_base_from_ifc(dt_upper: str | None) -> str:
            """
            Usage:
                Determines the numeric base type ('integer' or 'double') from an IFC data type string.
            Inputs:
                dt_upper (str | None): Uppercase IFC data type name (e.g., "IFCINTEGER", "IFCREAL").
            Output:
                str: Returns "integer" if the type contains "INTEGER"; otherwise returns "double".
                    Defaults to "double" when no input is provided.
            """
            if not dt_upper: return "double"
            if "INTEGER" in dt_upper: return "integer"
            return "double"

        # comparators in string ("> 30", "<=0.45", "≥3", "≤ 3")
        _cmp_regex = re.compile(r"^\s*(>=|=>|≤|<=|≥|>|<)\s*([0-9]+(?:[.,][0-9]+)?)\s*$")
        _normalize_op = {">=":">=", "=>":">=", "≥":">=", "<=":"<=", "≤":"<="}
        
        def _extract_op_target_from_string(s: str):
            """
                Usage:
                    Extracts a comparison operator and its numeric target value from a string expression.
                Inputs:
                    s (str): String containing a comparison, e.g., "> 30", "<=0.45", "≥3", or "≤ 3".
                Output:
                    tuple(str | None, float | None): Returns a tuple (operator, target_value),
                                                    where operator is one of ">", ">=", "<", or "<=".
                                                    Returns (None, None) if the string does not match a valid pattern.
            """
            m = _cmp_regex.match(s)
            if not m: return None, None
            op, num = m.group(1), m.group(2)
            op = _normalize_op.get(op, op)
            try: tgt = float(num.replace(",", "."))
            except Exception: return None, None
            return op, tgt

        # English descriptions (>= before >)
        _desc_ops = [
            (r"(greater\s+than\s+or\s+equal\s+to|greater\s+or\s+equal\s+to|equal\s+or\s+greater\s+than|≥)", ">="),
            (r"(less\s+than\s+or\s+equal\s+to|not\s+greater\s+than|≤|at\s+most|maximum)", "<="),
            (r"(greater\s+than|more\s+than|>)", ">"),
            (r"(less\s+than|fewer\s+than|<)", "<"),
        ]
        _num_regex = re.compile(r"([0-9]+(?:[.,][0-9]+)?)")

        
        def _extract_from_description(desc: str):
            """
            Usage:
                Extracts a comparison operator and numeric target value from a descriptive text.
                Designed to interpret expressions such as "greater than 30" or "less than or equal to 0.45".
            Inputs:
                desc (str): Description text potentially containing a numeric comparison.
            Output:
                tuple(str | None, float | None): Returns a tuple (operator, target_value),
                                                where operator is one of ">", ">=", "<", or "<=",
                                                and target_value is the numeric value extracted.
                                                Returns (None, None) if no valid pattern is found.
            """
            if not desc: return None, None
            text = desc.strip().lower()
            for pat, op in _desc_ops:
                if re.search(pat, text):
                    m = _num_regex.search(text)
                    if m:
                        try:
                            tgt = float(m.group(1).replace(",", "."))
                            return op, tgt
                        except Exception:
                            pass
            return None, None

        # anchored regexes for integers (numeric fallback for decimals)
        def _regex_for_threshold(threshold: float, op: str) -> list[str]:
            """
                Usage:
                    Builds one or more anchored regular expressions to validate integer values 
                    against a numeric threshold and comparison operator.
                    For non-integer thresholds, returns a generic numeric pattern as fallback.
                Inputs:
                    threshold (float): Numeric limit used for the comparison (e.g., 30, 10.5).
                    op (str): Comparison operator, one of ">", ">=", "<", or "<=".
                Output:
                    list[str]: A list containing one or more anchored regex patterns that match 
                            integer strings satisfying the given condition.
                            Returns a generic numeric regex pattern as fallback for decimals.
            """
            if abs(threshold - round(threshold)) < 1e-9:
                t = int(round(threshold))
                def gt_int(n):
                    if n <= 8:  return rf"^([{n+1}-9]|[1-9]\d|[1-9]\d{{2,}})$"
                    if n <= 98:
                        tens, units = divmod(n + 1, 10)
                        p1 = rf"{tens}[{units}-9]" if units > 0 else rf"{tens}\d"
                        p2 = rf"[{tens+1}-9]\d" if tens < 9 else ""
                        parts = [p1, p2, r"[1-9]\d{2,}"]
                        return "^(" + "|".join([p for p in parts if p]) + ")$"
                    return r"^[1-9]\d{2,}$"
                def ge_int(n):
                    if n <= 9:  return rf"^([{n}-9]|[1-9]\d|[1-9]\d{{2,}})$"
                    if n <= 99:
                        tens, units = divmod(n, 10)
                        p1 = rf"{tens}[{units}-9]"
                        p2 = rf"[{tens+1}-9]\d" if tens < 9 else ""
                        parts = [p1, p2, r"[1-9]\d{2,}"]
                        return "^(" + "|".join([p for p in parts if p]) + ")$"
                    return r"^[1-9]\d{2,}$"
                def lt_int(n):
                    if n <= 0: return r"^(?!)$"
                    if n <= 10: return rf"^[0-9]$" if n == 10 else rf"^[0-{n-1}]$"
                    tens, units = divmod(n - 1, 10)
                    if tens == 1: return r"^([0-9]|1[0-9])$"
                    return rf"^([0-9]|[1-{tens-1}]\d|{tens}[0-{units}])$"
                def le_int(n):
                    if n < 10: return rf"^[0-{n}]$"
                    tens, units = divmod(n, 10)
                    if tens == 1:
                        return r"^([0-9]|1[0-9])$" if units == 9 else rf"^([0-9]|1[0-{units}])$"
                    parts = [r"[0-9]"]
                    if tens > 1: parts.append(rf"[1-{tens-1}]\d")
                    parts.append(rf"{tens}[0-{units}]")
                    return "^(" + "|".join(parts) + ")$"
                if   op == ">":  return [gt_int(t)]
                elif op == ">=": return [ge_int(t)]
                elif op == "<":  return [lt_int(t)]
                elif op == "<=": return [le_int(t)]
            return [r"^\d+(?:[.,]\d+)?$"]  # fallback for decimals (plain numeric string)

        def _build_restriction_for_text(op: str | None, target, bounds: dict):
            """
            Usage:
                Builds a text-based IDS restriction (ids.Restriction) using regex patterns derived 
                from numeric thresholds and comparison operators. 
                Used when a property has textual dataType (e.g., IFCLABEL) but represents numeric conditions.
            Inputs:
                op (str | None): Comparison operator (">", ">=", "<", "<=") if explicitly provided.
                target (any): Target value for the comparison. Can be numeric or string.
                bounds (dict): Dictionary of limit values such as 
                            {"minInclusive": ..., "maxExclusive": ..., "maxInclusive": ...}.
            Output:
                ids.Restriction | None: Returns an ids.Restriction object with regex patterns 
                                        for matching the specified numeric range in string form,
                                        or None if no valid pattern can be built.
            """
            if op and target is not None and _is_number_like(target):
                return ids.Restriction(base="string", options={"pattern": _regex_for_threshold(float(target), op)})
            patterns = []
            if bounds.get("minExclusive") is not None:
                patterns += _regex_for_threshold(float(bounds["minExclusive"]), ">")
            if bounds.get("minInclusive") is not None:
                patterns += _regex_for_threshold(float(bounds["minInclusive"]), ">=")
            if bounds.get("maxExclusive") is not None:
                patterns += _regex_for_threshold(float(bounds["maxExclusive"]), "<")
            if bounds.get("maxInclusive") is not None:
                patterns += _regex_for_threshold(float(bounds["maxInclusive"]), "<=")
            return ids.Restriction(base="string", options={"pattern": patterns}) if patterns else None

        def _build_numeric_restriction(dt_upper: str | None, op: str | None, target, bounds: dict):
            """
            Usage:
                Builds a numeric IDS restriction (ids.Restriction) from a data type, comparison operator, 
                target value, and optional numeric bounds.
            Inputs:
                dt_upper (str | None): Uppercase IFC data type name (e.g., "IFCREAL", "IFCINTEGER").
                op (str | None): Comparison operator (">", ">=", "<", "<=") if provided.
                target (any): Target value for the comparison. Converted to float when applicable.
                bounds (dict): Dictionary containing optional boundary values such as 
                            {"minInclusive": ..., "maxExclusive": ..., "maxInclusive": ...}.
            Output:
                ids.Restriction | None: Returns an ids.Restriction object with the appropriate numeric limits,
                                        or None if no valid restriction can be created.
            """
            if not (op or any(v is not None for v in bounds.values())): return None
            base_num = _guess_numeric_base_from_ifc(dt_upper)
            opts = {}
            if op and target is not None:
                v = float(str(target).replace(",", "."))
                if   op == ">":  opts["minExclusive"] = v
                elif op == ">=": opts["minInclusive"] = v
                elif op == "<":  opts["maxExclusive"] = v
                elif op == "<=": opts["maxInclusive"] = v
            for k in ("minInclusive","maxInclusive","minExclusive","maxExclusive"):
                if bounds.get(k) is not None:
                    opts[k] = float(str(bounds[k]).replace(",", "."))
            if not opts: return None
            return ids.Restriction(base=base_num, options=opts)

        def _infer_ids_datatype(pset: str | None, baseName: str | None,
                                provided_dt: str | None, value, op: str | None, bounds: dict) -> str:
            """
            Usage:
                Infers the appropriate IFC data type (e.g., IFCREAL, IFCINTEGER, IFCBOOLEAN, IFCLABEL)
                for a given property based on its name, provided data type, value, and restrictions.
            Inputs:
                pset (str | None): Name of the property set to which the property belongs.
                baseName (str | None): Base name of the property (e.g., "ThermalTransmittance", "IsExternal").
                provided_dt (str | None): Data type explicitly provided in the input, if any.
                value (any): Property value or an ids.Restriction object.
                op (str | None): Comparison operator (">", ">=", "<", "<=") if defined.
                bounds (dict): Dictionary containing limit values such as 
                            {"minInclusive": ..., "maxExclusive": ..., "maxInclusive": ...}.
            Output:
                str: Returns the inferred IFC data type string, such as "IFCREAL", "IFCINTEGER", 
                    "IFCBOOLEAN", or "IFCLABEL".
            """
            # if a dataType is provided, normalize and promote it if applicable
            if provided_dt:
                dtU = _strip_ifc_prefix(provided_dt)
                if baseName and dtU in ("IFCREAL", "IFCNUMBER", "NUMBER", "REAL"):
                    hint = PROPERTY_DATATYPE_HINTS.get(str(baseName).strip().upper())
                    if hint: return hint
                if dtU in MEASURE_HINTS: return MEASURE_HINTS[dtU]
                return dtU
            # hints by name
            if baseName:
                hint = PROPERTY_DATATYPE_HINTS.get(str(baseName).strip().upper())
                if hint: return hint
            # value = Restriction
            if isinstance(value, ids.Restriction):
                base = getattr(value, "base", "").lower()
                if base in ("integer",): return "IFCINTEGER"
                if base in ("double","number","real","float"): return "IFCREAL"
                return "IFCLABEL"
            # if op/bounds -> numeric
            if op or any(v is not None for v in bounds.values()):
                return "IFCREAL"
            # booleans
            if _is_bool_like(value): return "IFCBOOLEAN"
            # literal numbers
            if _is_number_like(value):
                try:
                    iv = int(str(value))
                    if float(str(value)) == float(iv): return "IFCINTEGER"
                except Exception:
                    pass
                return "IFCREAL"
            # text
            return "IFCLABEL"

        # (optional) Absorption of PredefinedType into Entity.predefinedType — DISABLED
        def _absorb_predefined_type(applicability_list: list):
            """
            Usage:
                Transfers the value of a PREDEFINEDTYPE attribute into the corresponding Entity's 
                predefinedType field within the applicability list. 
                This operation effectively absorbs the PREDEFINEDTYPE entry into the Entity definition.
            Inputs:
                applicability_list (list): List of facet dictionaries containing 'Entity' and 'Attribute' definitions.
            Output:
                list: The updated applicability list where the PREDEFINEDTYPE value has been moved 
                    to the Entity's 'predefinedType' field, if applicable. 
                    Returns the original list if no valid Entity or PREDEFINEDTYPE attribute is found.
            """
            if not isinstance(applicability_list, list): return applicability_list
            idx = next((i for i,f in enumerate(applicability_list) if (f.get("type") == "Entity")), None)
            if idx is None: return applicability_list
            for i,f in enumerate(list(applicability_list)):
                if f.get("type") == "Attribute" and str(f.get("name","")).strip().upper() == "PREDEFINEDTYPE":
                    val = f.get("value")
                    if val not in (None, ""):
                        applicability_list[idx]["predefinedType"] = val
                        applicability_list.pop(i)
                        break
            return applicability_list

        # IDS Root 
        # -----------------------------------------------------------------------------------------------------------
        try:
            ids_root = ids.Ids(
                title=(title or "Untitled"),
                description=(description or None),
                author=(author or None),
                version=(str(ids_version) if ids_version else None),
                purpose=(purpose or None),
                milestone=(milestone or None),
                date=(date_iso or datetime.date.today().isoformat()),
            )
            try: ids_root.title = (title or "Untitled")
            except Exception: pass
            try: ids_root.info.title = (title or "Untitled")
            except Exception: pass
        except Exception as e:
            return {"ok": False, "error": "Could not initialize the IDS", "details": str(e)}

        # Facets (with context)
        # -----------------------------------------------------------------------------------------------------------
        def _facet_from_dict(f, spec_desc: str | None, context: str):
            """
            Usage:
                Builds an IDS facet object (e.g., Entity, Attribute, Property, Material, Classification, or PartOf)
                from a dictionary definition. Handles data normalization, type inference, comparison extraction,
                and restriction creation for both applicability and requirements contexts.
            Inputs:
                f (dict): Dictionary describing a facet, including its type and relevant attributes.
                spec_desc (str | None): Optional specification description used to infer operators or targets
                                        when not explicitly provided.
                context (str): Indicates the facet context, either 'applicability' or 'requirements'.
                            Only in 'requirements' can operator/target be extracted from the description.
            Output:
                ids.Entity | ids.Attribute | ids.Property | ids.Material | ids.Classification | ids.PartOf:
                    Returns the corresponding ids.* object based on the facet type.
            Exceptions:
                ValueError: Raised if the facet type is unsupported or required fields are missing
                            (e.g., Property without propertySet or baseName, Attribute without name).
            """    
                        
            t = (f.get("type") or "").strip()

            if t == "Entity":
                ent_name = f.get("name", "") or f.get("entity", "") or f.get("Name", "")
                ent_name = ent_name.strip()
                if ent_name.lower().startswith("ifc") and not ent_name.isupper():
                    ent_name = ent_name.upper()  # 'IfcWall' -> 'IFCWALL'
                return ids.Entity(
                    name=ent_name,
                    predefinedType=f.get("predefinedType", ""),  # we keep it separate (not absorbed)
                    instructions=f.get("instructions", ""),
                )

            elif t == "Attribute":
                name = f.get("name") or f.get("Name")
                if not name: raise ValueError("Attribute requires 'name'.")
                kwargs = dict(name=name)
                if f.get("value") not in (None, ""):
                    val = f["value"]
                    if _is_bool_like(val):
                        tok = _to_bool_token(val)
                        kwargs["value"] = tok if tok else val
                    else:
                        kwargs["value"] = val
                # Cardinality from occurs
                card = _card_from_occurs(f.get("minOccurs"), f.get("maxOccurs"))
                if card: kwargs["cardinality"] = card
                if f.get("cardinality"): kwargs["cardinality"] = _norm_card(f.get("cardinality"))
                if f.get("instructions"): kwargs["instructions"] = f["instructions"]
                return ids.Attribute(**kwargs)

            elif t == "Property":
                pset = f.get("propertySet") or f.get("pset") or f.get("psetName")
                base = f.get("baseName") or f.get("name") or f.get("Name")
                if not pset or not base: raise ValueError("Property requires 'propertySet' and 'baseName'.")

                val_in = f.get("value", None)
                bounds = {
                    "minInclusive": f.get("minInclusive"),
                    "maxInclusive": f.get("maxInclusive"),
                    "minExclusive": f.get("minExclusive"),
                    "maxExclusive": f.get("maxExclusive"),
                }
                # minValue/maxValue + inclusivity
                if f.get("minValue") is not None:
                    if bool(f.get("minInclusive")): bounds["minInclusive"] = f.get("minValue")
                    else:                            bounds["minExclusive"] = f.get("minValue")
                if f.get("maxValue") is not None:
                    if bool(f.get("maxInclusive")): bounds["maxInclusive"] = f.get("maxValue")
                    else:                            bounds["maxExclusive"] = f.get("maxValue")

                if isinstance(val_in, dict):
                    for k in ("minInclusive","maxInclusive","minExclusive","maxExclusive"):
                        if k in val_in and bounds.get(k) is None:
                            bounds[k] = val_in[k]

                # explicit operator
                op = f.get("op") or f.get("operator") or f.get("comparison") or f.get("cmp") or f.get("relation")
                target = f.get("target") or f.get("threshold") or f.get("limit")

                # operator in 'value' string ("> 30")
                if target is None and isinstance(val_in, str):
                    _op2, _tg2 = _extract_op_target_from_string(val_in)
                    if _op2 and _tg2 is not None:
                        op, target, val_in = _op2, _tg2, None

                # ONLY IN REQUIREMENTS: extract from description
                if context == "requirements" and (not op and all(v is None for v in bounds.values()) and target is None and spec_desc):
                    _op3, _tg3 = _extract_from_description(spec_desc)
                    if _op3 and _tg3 is not None:
                        op, target = _op3, _tg3

                # cardinality from occurs
                card = _card_from_occurs(f.get("minOccurs"), f.get("maxOccurs"))

                dt = _infer_ids_datatype(pset, base, f.get("dataType"), val_in, op, bounds)

                # boolean normalization
                if _is_bool_like(val_in):
                    tok = _to_bool_token(val_in)
                    if tok is not None:
                        val_in = tok
                        if not dt: dt = "IFCBOOLEAN"

                # Restriction when applicable
                restriction_obj = None
                if op or any(v is not None for v in bounds.values()):
                    if dt in ("IFCLABEL","IFCTEXT"):
                        restriction_obj = _build_restriction_for_text(op, target if target is not None else val_in, bounds)
                    else:
                        restriction_obj = _build_numeric_restriction(dt, op, target if target is not None else val_in, bounds)
                if isinstance(val_in, ids.Restriction):
                    restriction_obj = val_in

                kwargs = dict(propertySet=pset, baseName=base)
                if restriction_obj is not None:
                    kwargs["value"] = restriction_obj
                    if dt: kwargs["dataType"] = dt
                else:
                    if val_in not in (None, ""): kwargs["value"] = val_in
                    if dt: kwargs["dataType"] = dt

                if f.get("uri"): kwargs["uri"] = f["uri"]
                if f.get("instructions"): kwargs["instructions"] = f["instructions"]
                if card: kwargs["cardinality"] = card
                if f.get("cardinality"): kwargs["cardinality"] = _norm_card(f.get("cardinality"))
                if (op or any(v is not None for v in bounds.values())) and "cardinality" not in kwargs:
                    kwargs["cardinality"] = "required"

                return ids.Property(**kwargs)

            elif t == "Material":
                kwargs = {}
                if f.get("value"): kwargs["value"] = f["value"]
                if f.get("uri"): kwargs["uri"] = f["uri"]
                if f.get("cardinality"): kwargs["cardinality"] = _norm_card(f["cardinality"])
                if f.get("instructions"): kwargs["instructions"] = f["instructions"]
                return ids.Material(**kwargs)

            elif t == "Classification":
                return ids.Classification(
                    value=f.get("value", ""),
                    system=f.get("system", ""),
                    uri=f.get("uri", ""),
                    cardinality=_norm_card(f.get("cardinality")),
                    instructions=f.get("instructions", ""),
                )

            elif t == "PartOf":
                return ids.PartOf(
                    name=f.get("name", ""),
                    predefinedType=f.get("predefinedType", ""),
                    relation=f.get("relation", ""),
                    cardinality=_norm_card(f.get("cardinality")),
                    instructions=f.get("instructions", ""),
                )

            else:
                raise ValueError(f"Unsupported or empty facet type: '{t}'.")

        # Construction
        # -----------------------------------------------------------------------------------------------------------
        total_specs = total_app = total_req = 0
        try:
            for s in specs:
                if not isinstance(s, dict):
                    raise ValueError("Each 'spec' must be a dict.")
                applicability = s.get("applicability", [])
                requirements  = s.get("requirements", [])
                if not isinstance(applicability, list) or not isinstance(requirements, list):
                    raise ValueError("'applicability' and 'requirements' must be lists.")

                # Do NOT absorb PredefinedType (it remains as an Attribute in applicability)
                # applicability = _absorb_predefined_type(applicability)

                spec_obj = ids.Specification()
                if s.get("name"):
                    try: spec_obj.name = s["name"]
                    except Exception: pass
                if s.get("description"):
                    try: spec_obj.description = s["description"]
                    except Exception: pass

                # ifcVersion: use the provided one; if not, default to IFC4
                canon = _norm_ifc_version(s.get("ifcVersion") or "IFC4")
                try: spec_obj.ifcVersion = canon
                except Exception: pass

                for f in applicability:
                    facet = _facet_from_dict(f, s.get("description"), context="applicability")
                    spec_obj.applicability.append(facet); total_app += 1

                for f in requirements:
                    facet = _facet_from_dict(f, s.get("description"), context="requirements")
                    spec_obj.requirements.append(facet); total_req += 1

                ids_root.specifications.append(spec_obj); total_specs += 1

        except Exception as e:
            return {"ok": False, "error": "Error while building the IDS specifications", "details": str(e)}

        if total_specs == 0:
            return {"ok": False, "error": "No Specification was created. Check 'specs'."}

        # Saved
        # -----------------------------------------------------------------------------------------------------------
        try:
            if not output_path:
                safe_title = "".join(c for c in title if c.isalnum() or c in (" ","-","_")).rstrip() or "ids"
                today = (date_iso if date_iso else datetime.date.today().isoformat())
                output_path = os.path.abspath(f"{safe_title}_{today}.ids")
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            ids_root.to_xml(output_path)
        except Exception as e:
            return {"ok": False, "error": "Could not save the IDS file", "details": str(e)}

        return {
            "ok": True,
            "output_path": output_path,
            "message": f"IDS '{title}' generated. Specs: {total_specs}, facets: {total_app} appl. / {total_req} req."
        }
    
    #endregion


def extract_quantities(entity, blender_name=None):
    """
    Extract quantity information from an IFC entity.
    
    Parameters:
        entity: IFC entity object
        blender_name: Optional Blender object name
    
    Returns:
        Dictionary with element info and quantities
    """
    try:
        # Get all property sets
        psets = ifcopenshell.util.element.get_psets(entity)
        
        # Basic element info
        element_data = {
            "id": entity.GlobalId if hasattr(entity, "GlobalId") else f"Entity_{entity.id()}",
            "name": entity.Name if hasattr(entity, "Name") else None,
            "type": entity.is_a(),
            "blender_name": blender_name,
            "quantities": {}
        }
        
        # Look for quantity information in different property sets
        quantity_sources = ["BaseQuantities", "ArchiCADQuantities", "Qto_WallBaseQuantities", 
                           "Qto_SlabBaseQuantities", "Qto_BeamBaseQuantities", "Qto_ColumnBaseQuantities"]
        
        # Extract quantities from property sets - keep original names
        for pset_name in quantity_sources:
            if pset_name in psets:
                pset_data = psets[pset_name]
                for prop_name, prop_value in pset_data.items():
                    # Only include numeric values and skip the 'id' field
                    if isinstance(prop_value, (int, float)) and prop_name != 'id':
                        element_data["quantities"][prop_name] = prop_value
            
        return element_data if element_data["quantities"] else None
        
    except Exception as e:
        return None


# Blender UI Panel
class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Bonsai MCP"
    bl_idname = "BLENDERMCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bonsai MCP'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "blendermcp_port")
        
        if not scene.blendermcp_server_running:
            layout.operator("blendermcp.start_server", text="Start MCP Server")
        else:
            layout.operator("blendermcp.stop_server", text="Stop MCP Server")
            layout.label(text=f"Running on port {scene.blendermcp_port}")


# Operator to start the server
class BLENDERMCP_OT_StartServer(bpy.types.Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Connect to Claude"
    bl_description = "Start the BlenderMCP server to connect with Claude"
    
    def execute(self, context):
        scene = context.scene
        
        # Create a new server instance
        if not hasattr(bpy.types, "blendermcp_server") or not bpy.types.blendermcp_server:
            bpy.types.blendermcp_server = BlenderMCPServer(port=scene.blendermcp_port)
        
        # Start the server
        bpy.types.blendermcp_server.start()
        scene.blendermcp_server_running = True
        
        return {'FINISHED'}

# Operator to stop the server
class BLENDERMCP_OT_StopServer(bpy.types.Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop the connection to Claude"
    bl_description = "Stop the connection to Claude"
    
    def execute(self, context):
        scene = context.scene
        
        # Stop the server if it exists
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            bpy.types.blendermcp_server.stop()
            del bpy.types.blendermcp_server
        
        scene.blendermcp_server_running = False
        
        return {'FINISHED'}

# Registration functions
def register():
    bpy.types.Scene.blendermcp_port = IntProperty(
        name="Port",
        description="Port for the BlenderMCP server",
        default=9876,
        min=1024,
        max=65535
    )
    
    bpy.types.Scene.blendermcp_server_running = bpy.props.BoolProperty(
        name="Server Running",
        default=False
    )
    
    
    bpy.utils.register_class(BLENDERMCP_PT_Panel)
    bpy.utils.register_class(BLENDERMCP_OT_StartServer)
    bpy.utils.register_class(BLENDERMCP_OT_StopServer)
    
    print("BlenderMCP addon registered")

def unregister():
    # Stop the server if it's running
    if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
        bpy.types.blendermcp_server.stop()
        del bpy.types.blendermcp_server
    
    bpy.utils.unregister_class(BLENDERMCP_PT_Panel)
    bpy.utils.unregister_class(BLENDERMCP_OT_StartServer)
    bpy.utils.unregister_class(BLENDERMCP_OT_StopServer)
    
    del bpy.types.Scene.blendermcp_port
    del bpy.types.Scene.blendermcp_server_running

    print("BlenderMCP addon unregistered")

if __name__ == "__main__":
    register()
