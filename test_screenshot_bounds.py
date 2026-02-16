from PIL import ImageGrab
import os

# Coordinates from debug_windows.py
# Rect: (-2531, 12, -1056, 1401)
bbox = (-2531, 12, -1056, 1401)

print(f"Capturing bbox: {bbox}")
try:
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    img.save("test_capture.png")
    print("Saved test_capture.png")
    
    # Analyze if image is all black (simple check)
    extrema = img.getextrema()
    print(f"Image extrema: {extrema}")
    if extrema:
        # For RGB, extrema is a list of tuples like [(min, max), ...]
        is_black = True
        for min_val, max_val in extrema:
            if max_val > 0:
                is_black = False
                break
        if is_black:
            print("WARNING: Image appears to be all black.")
        else:
            print("Image content detected (not all black).")

except Exception as e:
    print(f"Error: {e}")
