
import win32com.client
import pythoncom

def analyze_mleader():
    try:
        zwcad = win32com.client.Dispatch("ZWCAD.Application")
        doc = zwcad.ActiveDocument
        if not doc:
            print("No active document")
            return

        # Handle 5F is the MLeader of interest
        handle = "5F"
        try:
            entity = doc.HandleToObject(handle)
        except Exception as e:
            print(f"Could not find entity {handle}: {e}")
            return

        print(f"Analyzing Entity: {entity.ObjectName} (Handle: {entity.Handle})")
        
        # MLeader specific analysis
        if entity.ObjectName == "AcDbMLeader":
            print(f"  ContentType: {entity.ContentType}")
            print(f"  TextString: {entity.TextString}")
            try:
                # Inspect Leader Lines
                # GetLeaderLineIndexes returns an array of indexes
                indexes = entity.GetLeaderLineIndexes(0) # 0 is usually the leader index
                print(f"  LeaderLineIndexes (Group 0): {indexes}")
                
                if indexes:
                    for idx in indexes:
                        print(f"    Line Index: {idx}")
                        # GetLeaderLineVertices returns array of coordinates (x,y,z, x,y,z...)
                        vertices = entity.GetLeaderLineVertices(idx)
                        print(f"      Vertices: {vertices}")
                        
                # Check for other leader groups/indexes
                # AddMLeader documentation suggests usage of 'leaderIndex'
                # Let's try to probe if there are other groups
                try:
                    count = entity.LeaderLineCount
                    print(f"  LeaderLineCount: {count}")
                except:
                    print("  LeaderLineCount property not found")

            except Exception as e:
                print(f"  Error analyzing leader lines: {e}")

    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    analyze_mleader()
