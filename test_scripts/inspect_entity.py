import sys
import os
import logging

project_root = r"d:\dev\proys\mcp\cad\multiCAD-mcp"
sys.path.append(os.path.join(project_root, "src"))

logging.basicConfig(level=logging.INFO)

from adapters.adapter_manager import get_adapter

def inspect_entity(handle):
    print(f"Connecting to ZWCAD to inspect handle {handle}...")
    try:
        adapter = get_adapter("zwcad")
        doc = adapter.document
        model_space = doc.ModelSpace
        
        try:
            entity = doc.HandleToObject(handle)
        except Exception as e:
            print(f"Could not find entity with handle {handle}: {e}")
            return

        print(f"\n--- Entity Inspection: {handle} ---")
        print(f"ObjectName: {entity.ObjectName}")
        print(f"EntityType: {entity.EntityType}")
        print(f"Layer: {entity.Layer}")
        
        if entity.ObjectName == "AcDbLeader":
            print("Detected Type: LEADER (AcDbLeader)")
            try:
                print(f"Type: {entity.Type} (0=NoArrow, 1=Arrow)")
            except: pass
            
            try:
                print(f"Coordinate count: {len(entity.Coordinates)}")
                print(f"Coordinates: {entity.Coordinates}")
            except: pass

            try:
                annotation = entity.Annotation
                print(f"Annotation: {annotation.ObjectName} (Handle: {annotation.Handle})")
            except Exception as e:
                 print(f"Annotation access failed: {e}")

        elif entity.ObjectName == "AcDbMLeader":
            print("Detected Type: MULTILEADER (AcDbMLeader)")
            try:
                print(f"ContentType: {entity.ContentType} (1=Block, 2=MText, 0=None)")
            except Exception as e: print(f"ContentType failed: {e}")
            
            try:
                print(f"TextString: {entity.TextString}")
            except Exception as e: print(f"TextString failed: {e}")

            try:
                # Try to get MText object if possible, though MLeader usually wraps it
                # Some interfaces expose 'MText' property
                print(f"MText Attribute: {entity.MText.TextString}")
            except: pass

        # List all dynamic properties
        print("\n--- Available Properties/Methods (dir) ---")
        try:
            # Filter out internal/private attributes
            props = [p for p in dir(entity) if not p.startswith('_')]
            for p in props:
                try:
                    # Just print the name, maybe value if simple
                    val = getattr(entity, p)
                    if not callable(val):
                        s_val = str(val)
                        if len(s_val) > 100: s_val = s_val[:100] + "..."
                        print(f"{p}: {s_val}")
                except:
                    print(f"{p}: <access failed>")
        except Exception as e:
            print(f"Failed to list properties: {e}")

    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_entity("7B1")
