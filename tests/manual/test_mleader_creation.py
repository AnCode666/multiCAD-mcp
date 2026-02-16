import sys
import os
import logging

project_root = r"d:\dev\proys\mcp\cad\multiCAD-mcp"
sys.path.append(os.path.join(project_root, "src"))

logging.basicConfig(level=logging.INFO)

from adapters.adapter_manager import get_adapter
from core import CADInterface

def test_creation():
    print("Connecting to ZWCAD...")
    try:
        adapter = get_adapter("zwcad")
        doc = adapter.document
        msp = doc.ModelSpace
        
        # Normalize points first
        points = [(0, 0, 0), (10, 10, 0), (20, 10, 0)]
        norm_points = [CADInterface.normalize_coordinate(p) for p in points]
        
        # Use simple list for variant array creation via adapter helper
        # adapter._points_to_variant_array takes list of 3-tuples
        pts_array = adapter._points_to_variant_array(norm_points)
        
        # Test 1: AddMLeader with just points (as array) + index?
        print("\n--- Test 1: AddMLeader(points_array, 0) ---")
        try:
            print("Attempting AddMLeader(pts_array, 0)...")
            result = msp.AddMLeader(pts_array, 0)
            print(f"Result type: {type(result)}")
            print(f"Result value: {result}")
            
            # If tuple, maybe the object is the first element
            if isinstance(result, tuple):
                 mleader = result[0]
            else:
                 mleader = result
                 
            try:
                print(f"Handle: {mleader.Handle}")
                mleader.ContentType = 2
                mleader.TextString = "Test 1 Content"
                print("Content set successfully.")
            except Exception as e:
                print(f"Failed to access/set properties on result: {e}")
                
            return

        except Exception as e:
            print(f"Test 1 failed: {e}")

        # Test 2: AddMLeader(points_array)
        print("\n--- Test 2: AddMLeader(points_array) ---")
        try:
            print("Attempting AddMLeader(pts_array)...")
            result = msp.AddMLeader(pts_array)
            print(f"Result type: {type(result)}")
            print(f"Result value: {result}")
            return
        except Exception as e:
            print(f"Test 2 failed: {e}")
            
    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_creation()
