import sys
import os
import logging

project_root = r"d:\dev\proys\mcp\cad\multiCAD-mcp"
sys.path.append(os.path.join(project_root, "src"))

logging.basicConfig(level=logging.INFO)

from adapters.adapter_manager import get_adapter

def main():
    print("Connecting to ZWCAD...")
    try:
        # get_adapter will default to trying to connect
        adapter = get_adapter("zwcad")
        
        print(f"Connected to {adapter}")
        
        print("Testing draw_leader with REFACTORED logic...")
        try:
            # Using the same parameters as the user request
            result = adapter.draw_leader(
                points=[(30, 10, 0), (40, 20, 0)], # Changed coordinates slightly to not overlap
                text="motos_v2",
                text_height=2.5,
                color="blue", # Changed color to distinguish
                layer="0"
            )
            print(f"Success! Result handle: {result}")
            
        except Exception as e:
            print(f"Error calling draw_leader: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
