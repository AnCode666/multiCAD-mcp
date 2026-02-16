import win32com.client
import pythoncom
import traceback

def get_cad_app():
    progs = ["ZwCAD.Application", "AutoCAD.Application", "Gcad.Application", "Bricscad.Application"]
    for prog in progs:
        try:
            app = win32com.client.GetActiveObject(prog)
            print(f"Connected to {prog}")
            return app
        except:
            pass
    print("Could not connect to any CAD application")
    return None

def draw():
    try:
        app = get_cad_app()
        if not app:
            return

        doc = app.ActiveDocument
        msp = doc.ModelSpace
        
        print("Drawing double leader...")
        
        # Coordinates
        # Text at 250,250
        # Arrow 1 at 200,200
        # Arrow 2 at 300,200
        
        # Create MText
        # Note: AddMText(InsertionPoint, Width, Text)
        # InsertionPoint must be array of doubles
        text_pt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [250.0, 250.0, 0.0])
        mtext = msp.AddMText(text_pt, 20, "coches")
        mtext.Height = 5
        
        # Create Leader 1
        # Points: ArrowHead -> Landing
        pts1 = [200.0, 200.0, 0.0, 250.0, 250.0, 0.0]
        pts1_var = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, pts1)
        leader1 = msp.AddLeader(pts1_var, mtext, 1) # 1 = acLineWithArrow
        
        # Create Leader 2
        pts2 = [300.0, 200.0, 0.0, 250.0, 250.0, 0.0]
        pts2_var = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, pts2)
        leader2 = msp.AddLeader(pts2_var, mtext, 1)

        # Update
        mtext.Update()
        leader1.Update()
        leader2.Update()
        
        # Force regen not usually needed but let's update view
        app.Update()

        print("Successfully drew double leader with fallback method")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    draw()
