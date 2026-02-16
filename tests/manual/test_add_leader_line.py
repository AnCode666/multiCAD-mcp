
import win32com.client
import pythoncom

def test_add_leader_line():
    try:
        zwcad = win32com.client.Dispatch("ZWCAD.Application")
        doc = zwcad.ActiveDocument
        
        # Create points for a new MLeader
        # 1. First leader line
        points1 = [0.0, 0.0, 0.0, 10.0, 10.0, 0.0]
        variant_points1 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, points1)
        
        # Create MLeader
        result = doc.ModelSpace.AddMLeader(variant_points1, 0)
        mleader = result[0] if isinstance(result, tuple) else result
        mleader.TextString = "Test Multi-Line"
        
        print("Initial Leader Line Indexes:", mleader.GetLeaderLineIndexes(0))
        
        # Test 1: AddLeaderLine with 2 points (Arrow -> Landing)
        points2 = [20.0, 0.0, 0.0, 10.0, 10.0, 0.0] # Converging to same point
        variant_points2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, points2)
        try:
            new_idx = mleader.AddLeaderLine(0, variant_points2)
            print(f"Added Leader Line (2 opts). New Index: {new_idx}")
            print(f" vertices: {mleader.GetLeaderLineVertices(new_idx)}")
        except Exception as e:
            print(f"Failed AddLeaderLine(0, 2pts): {e}")

        # Test 2: AddLeaderLine with 1 point (Arrow only)
        # Point: [40, 0, 0]
        points3 = [40.0, 0.0, 0.0]
        variant_points3 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, points3)
        
        try:
            new_idx2 = mleader.AddLeaderLine(0, variant_points3)
            print(f"Added Leader Line (1 pt). New Index: {new_idx2}")
            print(f" vertices: {mleader.GetLeaderLineVertices(new_idx2)}")
        except Exception as e:
             print(f"Failed AddLeaderLine(0, 1pt): {e}")

        print("Final Leader Line Indexes:", mleader.GetLeaderLineIndexes(0))
        zwcad.ZoomExtents()

    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    test_add_leader_line()
