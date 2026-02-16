import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from adapters.autocad_adapter import AutoCADAdapter
from core import ConfigManager

def test_subfolders():
    print("Connecting to ZWCAD...")
    adapter = AutoCADAdapter(cad_type="zwcad")
    
    if not adapter.connect():
        print("Failed to connect to ZWCAD")
        return

    config = ConfigManager()
    base_output_dir = Path(config.ensure_output_directory()).expanduser().resolve()
    print(f"Base output directory: {base_output_dir}")

    try:
        # 1. Test Screenshot (images/)
        print("\nTesting screenshot...")
        screenshot_result = adapter.get_screenshot()
        screenshot_path = Path(screenshot_result["path"])
        print(f"Screenshot saved to: {screenshot_path}")
        assert screenshot_path.parent.name == "images"
        assert screenshot_path.exists()

        # 2. Test Export View (images/)
        print("\nTesting internal render export...")
        export_result = adapter.export_view()
        export_path = Path(export_result["path"])
        print(f"Export saved to: {export_path}")
        assert export_path.parent.name == "images"
        assert export_path.exists()

        # 3. Test Save Drawing (drawings/)
        print("\nTesting save drawing...")
        save_filename = f"test_save_{os.getpid()}.dwg"
        success = adapter.save_drawing(filename=save_filename)
        if success:
            # We need to find where it was saved. 
            # Our UtilityMixin should have placed it in drawings/
            expected_save_path = base_output_dir / "drawings" / save_filename
            print(f"Checking for drawing at: {expected_save_path}")
            assert expected_save_path.exists()
        else:
            print("Save drawing failed")
            assert False

        # 4. Test Excel Export (sheets/)
        print("\nTesting Excel export...")
        excel_filename = f"test_data_{os.getpid()}.xlsx"
        success = adapter.export_to_excel(filepath=excel_filename)
        if success:
            expected_excel_path = base_output_dir / "sheets" / excel_filename
            print(f"Checking for Excel at: {expected_excel_path}")
            assert expected_excel_path.exists()
        else:
            print("Excel export failed")
            assert False

        print("\nALL TESTS PASSED! Hierarchical structure verified.")

    finally:
        pass

if __name__ == "__main__":
    test_subfolders()
