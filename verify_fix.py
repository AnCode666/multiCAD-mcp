import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from adapters.mixins.view_mixin import ViewMixin

# Setup logging
logging.basicConfig(level=logging.DEBUG)

class MockAdapter(ViewMixin):
    def __init__(self):
        self.cad_type = "zwcad"
    
    def _validate_connection(self):
        pass

    def _get_application(self, op):
        return None
        
    def _get_document(self, op):
        return None
        
    def _simulate_autocad_click(self):
        pass

try:
    adapter = MockAdapter()
    print("Attempting to capture screenshot using modified ViewMixin...")
    result = adapter.get_screenshot()
    print(f"Screenshot captured: {result['path']}")
    
    # Check if file exists and size
    if os.path.exists(result['path']):
        size = os.path.getsize(result['path'])
        print(f"File size: {size} bytes")
        
        # Simple check for black image again to be sure
        from PIL import Image
        img = Image.open(result['path'])
        extrema = img.getextrema()
        print(f"Extrema: {extrema}")
        
        is_black = True
        for min_val, max_val in extrema:
            if max_val > 0:
                is_black = False
                break
        
        if is_black:
             print("FAILURE: Image is still black.")
        else:
             print("SUCCESS: Image has content!")

except Exception as e:
    print(f"Error: {e}")
