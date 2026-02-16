
import win32com.client
import pythoncom

def test_composite_mleader():
    try:
        zwcad = win32com.client.Dispatch("ZWCAD.Application")
        doc = zwcad.ActiveDocument
        
        # 1. Main Leader (Content + Arrow 1)
        p_arrow1 = [0.0, 0.0, 0.0]
        p_landing = [10.0, 10.0, 0.0]
        pts1 = p_arrow1 + p_landing
        var_pts1 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, pts1)
        
        print("Creating Main Leader...")
        res = doc.ModelSpace.AddMLeader(var_pts1, 0)
        main_ml = res[0] if isinstance(res, tuple) else res
        main_ml.TextString = "Composite Leader Test"
        
        # Get Exact Landing Point from Main Leader to match perfectly
        # Vertices 0: [ArrowX, ArrowY, ArrowZ, LandingX, LandingY, LandingZ]
        v0 = main_ml.GetLeaderLineVertices(0)
        exact_landing = list(v0)[3:] # Last 3 points
        print(f"Exact Landing: {exact_landing}")

        # 2. Secondary Leader (Arrow 2 -> Exact Landing)
        p_arrow2 = [20.0, 0.0, 0.0]
        
        # We want this leader to have NO text. 
        # If we use AddMLeader, it creates default content.
        # We can try setting ContentType = 0 (None) or 1 (Block) or just TextString=""?
        
        pts2 = p_arrow2 + exact_landing
        var_pts2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, pts2)
        
        print("Creating Secondary Leader...")
        res2 = doc.ModelSpace.AddMLeader(var_pts2, 0)
        sec_ml = res2[0] if isinstance(res2, tuple) else res2
        
        # Hide Text?
        sec_ml.TextString = ""
        # Try to remove the landing line? No, we WANT the landing line to merge.
        # But if TextString is empty, does it show a landing? 
        # Usually yes, a small dogleg.
        
        # Let's try changing ContentType to None (0) if allowed?
        try:
             # sec_ml.ContentType = 0 # AcMLeaderContentType.acNoneContent
             # API might not allow setting this easily?
             pass
        except:
             pass

        print("Secondary Leader Created.")
        
        zwcad.ZoomExtents()

    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    test_composite_mleader()
