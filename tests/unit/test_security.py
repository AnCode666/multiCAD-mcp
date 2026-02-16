"""
Security tests for multiCAD-MCP.

Tests for path traversal prevention, command injection prevention, and thread safety.
"""

import pytest
import threading
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from src.adapters import AutoCADAdapter
from src.core import CADOperationError
from src.adapters.adapter_manager import AdapterRegistry


class TestPathTraversal:
    """Test suite for path traversal prevention."""

    def test_validate_export_path_allows_safe_paths_in_dir(self):
        """Test that _validate_export_path allows paths within output directory."""
        adapter = AutoCADAdapter("autocad")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir).resolve()
            drawings_dir = output_dir / "drawings"
            drawings_dir.mkdir()

            # Safe path within output dir should pass validation
            safe_path = (drawings_dir / "file.dwg").resolve()
            assert adapter._validate_export_path(safe_path, output_dir) is True

    def test_validate_export_path_blocks_traversal_attempts(self):
        """Test that _validate_export_path rejects paths outside output directory."""
        adapter = AutoCADAdapter("autocad")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir).resolve()
            drawings_dir = output_dir / "drawings"
            drawings_dir.mkdir()

            # Path outside output dir should raise
            parent_dir = output_dir.parent
            traversal_path = (parent_dir / "dangerous.txt").resolve()

            # Use pytest.raises with exception type only
            with pytest.raises(Exception):  # Catch any exception
                adapter._validate_export_path(traversal_path, output_dir)

    def test_resolve_export_path_allows_safe_paths(self):
        """Test that resolve_export_path allows legitimate paths."""
        adapter = AutoCADAdapter("autocad")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            drawings_dir = output_dir / "drawings"
            drawings_dir.mkdir()

            mock_config_instance = MagicMock()
            mock_config_instance.output.directory = str(output_dir)

            with patch("core.get_config", return_value=mock_config_instance):
                # Safe path should work
                result = adapter.resolve_export_path("my_drawing.dwg", "drawings")
                assert "drawings" in result
                assert "my_drawing.dwg" in result

    def test_resolve_export_path_normalizes_names(self):
        """Test that filename from Path.name is used safely."""
        adapter = AutoCADAdapter("autocad")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            drawings_dir = output_dir / "drawings"
            drawings_dir.mkdir()

            mock_config_instance = MagicMock()
            mock_config_instance.output.directory = str(output_dir)

            with patch("core.get_config", return_value=mock_config_instance):
                # Only the filename part should be used
                result = adapter.resolve_export_path("../other/file.dwg", "drawings")
                assert "file.dwg" in result


class TestCommandInjection:
    """Test suite for command injection prevention."""

    def test_sanitize_blocks_semicolons(self):
        """Test that sanitization removes semicolons."""
        adapter = AutoCADAdapter("autocad")
        result = adapter._sanitize_command_input("test; malicious")
        assert ";" not in result

    def test_sanitize_allows_safe_chars(self):
        """Test that safe characters are preserved."""
        adapter = AutoCADAdapter("autocad")
        input_str = "C:\\drawings\\my_file.dwg"
        result = adapter._sanitize_command_input(input_str)
        assert result == input_str

    def test_sanitize_blocks_dangerous_chars(self):
        """Test that dangerous characters are removed."""
        adapter = AutoCADAdapter("autocad")
        input_str = "file`whoami`.dwg"
        result = adapter._sanitize_command_input(input_str)
        # Backticks should be removed, but alphanumeric characters remain
        assert "`" not in result
        assert "dwg" in result  # Safe extension remains

    def test_sanitize_preserves_paths(self):
        """Test that valid file paths with slashes are preserved."""
        adapter = AutoCADAdapter("autocad")
        input_str = "C:\\Program Files\\drawings\\my-drawing_v1.dwg"
        result = adapter._sanitize_command_input(input_str)
        assert "\\" in result or "/" in result
        assert "drawings" in result
        assert "-" in result
        assert "_" in result


class TestThreadSafety:
    """Test suite for thread safety of singletons."""

    def test_adapter_registry_thread_safe(self):
        """Test that AdapterRegistry singleton is thread-safe."""
        AdapterRegistry.reset()
        instances = []
        lock = threading.Lock()

        def get_registry():
            inst = AdapterRegistry.get_instance()
            with lock:
                instances.append(inst)

        # Create 10 threads all trying to get the singleton
        threads = [threading.Thread(target=get_registry) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same object
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

    def test_adapter_registry_set_active_cad_thread_safe(self):
        """Test thread-safe setting of active CAD type."""
        AdapterRegistry.reset()
        registry = AdapterRegistry.get_instance()
        results = []

        def set_and_read(cad_type):
            registry.set_active_cad_type(cad_type)
            results.append(registry._active_cad_type)

        # Multiple threads setting different CAD types
        threads = [
            threading.Thread(target=set_and_read, args=("autocad",)),
            threading.Thread(target=set_and_read, args=("zwcad",)),
            threading.Thread(target=set_and_read, args=("gcad",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have one of the values (no crashes, no corruption)
        assert all(val in ["autocad", "zwcad", "gcad"] for val in results)

    def test_config_manager_thread_safe(self):
        """Test that ConfigManager singleton is thread-safe."""
        from src.core.config import ConfigManager

        ConfigManager.reset()
        instances = []
        lock = threading.Lock()

        def get_config():
            mgr = ConfigManager()
            with lock:
                instances.append(mgr)

        # Create 10 threads all trying to get the singleton
        threads = [threading.Thread(target=get_config) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same object
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance


class TestInputValidation:
    """Test suite for input validation robustness."""

    def test_sanitize_empty_string(self):
        """Test handling of empty input."""
        adapter = AutoCADAdapter("autocad")
        result = adapter._sanitize_command_input("")
        assert result == ""

    def test_sanitize_whitespace(self):
        """Test handling of whitespace."""
        adapter = AutoCADAdapter("autocad")
        result = adapter._sanitize_command_input("  C:\\file.dwg  ")
        assert "file.dwg" in result

    def test_resolve_export_path_with_unicode(self):
        """Test handling of unicode characters in filenames."""
        adapter = AutoCADAdapter("autocad")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            drawings_dir = output_dir / "drawings"
            drawings_dir.mkdir()

            mock_config_instance = MagicMock()
            mock_config_instance.output.directory = str(output_dir)

            with patch("core.get_config", return_value=mock_config_instance):
                # Should handle unicode gracefully
                result = adapter.resolve_export_path("drawing_tm.dwg", "drawings")
                assert result is not None
