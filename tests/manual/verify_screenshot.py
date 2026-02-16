import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from adapters import AutoCADAdapter

def test_screenshot():
    logger.info("Testing screenshot functionality...")
    
    # Initialize adapter
    adapter = AutoCADAdapter("zwcad") # Defaulting to ZWCAD as per user context
    
    try:
        print("Connecting to CAD...")
        adapter.connect()
        
        print("Taking screenshot...")
        result = adapter.get_screenshot()
        
        print(f"Screenshot success!")
        print(f"Path: {result['path']}")
        print(f"Data length: {len(result['data'])} chars")
        
        # Verify file exists
        if os.path.exists(result['path']):
            print("File exists on disk.")
        else:
            print("ERROR: File not found on disk.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_screenshot()
