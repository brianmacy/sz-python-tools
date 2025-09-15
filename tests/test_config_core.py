"""Unit tests for _config_core module.

Tests for the core configuration management functionality,
separate from UI and display concerns.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from sz_tools._config_core import ConfigurationManager


class TestConfigurationManager(unittest.TestCase):
    """Test cases for ConfigurationManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigurationManager()

        # Mock Senzing components
        self.mock_factory = Mock()
        self.mock_config_mgr = Mock()
        self.mock_config = Mock()

        self.config_manager._sz_factory = self.mock_factory
        self.config_manager._sz_config_mgr = self.mock_config_mgr
        self.config_manager._sz_config = self.mock_config

    def test_initialization(self):
        """Test ConfigurationManager initialization."""
        # Test with ini_file_name
        manager = ConfigurationManager("/path/to/ini")
        self.assertEqual(manager._ini_file_name, "/path/to/ini")

        # Test without ini_file_name
        manager = ConfigurationManager()
        self.assertIsNone(manager._ini_file_name)

    @patch('sz_tools._config_core.get_engine_config')
    @patch('sz_tools._config_core.SzAbstractFactoryCore')
    def test_initialize_senzing_success(self, mock_factory_class, mock_get_engine_config):
        """Test successful Senzing initialization."""
        # Setup mocks
        mock_get_engine_config.return_value = "mock_engine_config"

        mock_factory = Mock()
        mock_config_mgr = Mock()

        mock_factory_class.return_value = mock_factory
        mock_factory.create_configmanager.return_value = mock_config_mgr

        manager = ConfigurationManager()

        # Mock the load_config method to avoid complex setup
        with patch.object(manager, 'load_config'):
            result = manager.initialize_senzing()

        self.assertTrue(result)
        self.assertEqual(manager._sz_factory, mock_factory)
        self.assertEqual(manager._sz_config_mgr, mock_config_mgr)

    @patch('sz_tools._config_core.SzAbstractFactoryCore')
    def test_initialize_senzing_failure(self, mock_factory_class):
        """Test failed Senzing initialization."""
        from senzing import SzError

        # Make factory creation raise an exception
        mock_factory_class.side_effect = SzError("Test error")

        manager = ConfigurationManager()
        result = manager.initialize_senzing()

        self.assertFalse(result)

    def test_get_default_config_id_success(self):
        """Test successful retrieval of default config ID."""
        self.mock_config_mgr.get_default_config_id.return_value = 1

        result = self.config_manager.get_default_config_id()

        self.assertEqual(result, 1)
        self.mock_config_mgr.get_default_config_id.assert_called_once()

    def test_get_default_config_id_no_manager(self):
        """Test get_default_config_id when no config manager."""
        self.config_manager._sz_config_mgr = None

        result = self.config_manager.get_default_config_id()

        self.assertIsNone(result)

    def test_get_default_config_id_error(self):
        """Test get_default_config_id with SzError."""
        from senzing import SzError

        self.mock_config_mgr.get_default_config_id.side_effect = SzError("Test error")

        result = self.config_manager.get_default_config_id()

        self.assertIsNone(result)

    def test_get_config_registry_success(self):
        """Test successful retrieval of config registry."""
        expected_registry = '{"CONFIGS": [{"CONFIG_ID": 1}]}'
        self.mock_config_mgr.get_configs.return_value = expected_registry

        result = self.config_manager.get_config_registry()

        self.assertEqual(result, expected_registry)

    def test_get_config_registry_no_manager(self):
        """Test get_config_registry when no config manager."""
        self.config_manager._sz_config_mgr = None

        result = self.config_manager.get_config_registry()

        self.assertIsNone(result)

    def test_load_config_success(self):
        """Test successful config loading."""
        self.mock_config_mgr.get_default_config_id.return_value = 1
        self.mock_config_mgr.create_config_from_config_id.return_value = self.mock_config
        self.mock_config.export.return_value = '{"G2_CONFIG": {"CFG_DSRC": []}}'

        self.config_manager.load_config()

        self.assertEqual(self.config_manager._current_config_id, 1)
        self.assertIsNotNone(self.config_manager.config_data)
        self.mock_config_mgr.create_config_from_config_id.assert_called_once_with(1)

    def test_load_config_with_specific_id(self):
        """Test loading config with specific ID."""
        self.mock_config_mgr.create_config_from_config_id.return_value = self.mock_config
        self.mock_config.export.return_value = '{"G2_CONFIG": {"CFG_DSRC": []}}'

        self.config_manager.load_config(5)

        self.assertEqual(self.config_manager._current_config_id, 5)
        self.assertIsNotNone(self.config_manager.config_data)
        self.mock_config_mgr.create_config_from_config_id.assert_called_once_with(5)

    def test_load_config_no_components(self):
        """Test load_config when components not initialized."""
        self.config_manager._sz_config_mgr = None

        # New implementation catches AttributeError and returns False
        result = self.config_manager.load_config()
        self.assertFalse(result)

    def test_get_current_config_success(self):
        """Test successful retrieval of current config."""
        expected_config = '{"test": "config"}'
        self.mock_config.export.return_value = expected_config

        result = self.config_manager.get_current_config()

        self.assertEqual(result, expected_config)

    def test_get_current_config_no_config(self):
        """Test get_current_config when no config loaded."""
        self.config_manager._sz_config = None

        result = self.config_manager.get_current_config()

        self.assertIsNone(result)

    def test_save_config_success(self):
        """Test successful config saving."""
        self.mock_config.export.return_value = '{"test": "config"}'
        self.mock_config_mgr.register_config.return_value = 2

        result = self.config_manager.save_config("Test comment")

        self.assertEqual(result, 2)
        self.mock_config_mgr.register_config.assert_called_once_with(
            '{"test": "config"}', "Test comment"
        )

    def test_import_config_from_file_success(self):
        """Test successful config import from file."""
        test_config = '{"G2_CONFIG": {"test": "data"}}'

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(test_config)
            temp_path = f.name

        try:
            result = self.config_manager.import_config_from_file(temp_path)

            self.assertTrue(result)
            self.mock_config.import_config.assert_called_once_with(test_config)
        finally:
            Path(temp_path).unlink()

    def test_import_config_from_file_not_exists(self):
        """Test import from non-existent file."""
        result = self.config_manager.import_config_from_file("/nonexistent/file.json")

        self.assertFalse(result)

    def test_import_config_from_file_invalid_json(self):
        """Test import from file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            result = self.config_manager.import_config_from_file(temp_path)

            self.assertFalse(result)
        finally:
            Path(temp_path).unlink()

    def test_export_config_to_file_success(self):
        """Test successful config export to file."""
        test_config = '{"test": "config"}'
        self.mock_config.export.return_value = test_config

        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            result = self.config_manager.export_config_to_file(temp_path)

            self.assertTrue(result)

            # Verify file content
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertEqual(content, test_config)
        finally:
            Path(temp_path).unlink()

    def test_export_config_to_file_no_config(self):
        """Test export when no config loaded."""
        self.config_manager._sz_config = None

        result = self.config_manager.export_config_to_file("/tmp/test.json")

        self.assertFalse(result)

    def test_get_data_sources_success(self):
        """Test successful retrieval of data sources."""
        test_config = {
            "G2_CONFIG": {
                "CFG_DSRC": [
                    {"DSRC_ID": 1, "DSRC_CODE": "TEST1"},
                    {"DSRC_ID": 2, "DSRC_CODE": "TEST2"}
                ]
            }
        }
        self.mock_config.export.return_value = json.dumps(test_config)

        result = self.config_manager.get_data_sources()

        expected = [
            {"DSRC_ID": 1, "DSRC_CODE": "TEST1"},
            {"DSRC_ID": 2, "DSRC_CODE": "TEST2"}
        ]
        self.assertEqual(result, expected)

    def test_get_data_sources_no_config(self):
        """Test get_data_sources when no config available."""
        self.config_manager._sz_config = None

        result = self.config_manager.get_data_sources()

        self.assertIsNone(result)

    def test_add_data_source_success(self):
        """Test successful data source addition."""
        # Setup config_data for the test
        self.config_manager.config_data = {
            'G2_CONFIG': {
                'CFG_DSRC': [
                    {'DSRC_ID': 1, 'DSRC_CODE': 'EXISTING_SOURCE'}
                ]
            }
        }

        # Mock the update_config_data method to return True
        with patch.object(self.config_manager, 'update_config_data', return_value=True):
            result = self.config_manager.add_data_source("NEW_SOURCE")
            self.assertTrue(result)

    def test_add_data_source_no_config(self):
        """Test add_data_source when no config loaded."""
        self.config_manager._sz_config = None

        result = self.config_manager.add_data_source("NEW_SOURCE")

        self.assertFalse(result)

    def test_delete_data_source_success(self):
        """Test successful data source deletion."""
        # Setup config_data with the data source to delete
        self.config_manager.config_data = {
            'G2_CONFIG': {
                'CFG_DSRC': [
                    {'DSRC_ID': 1, 'DSRC_CODE': 'OLD_SOURCE'},
                    {'DSRC_ID': 2, 'DSRC_CODE': 'KEEP_SOURCE'}
                ]
            }
        }

        # Mock the update_config_data method to return True
        with patch.object(self.config_manager, 'update_config_data', return_value=True):
            result = self.config_manager.delete_data_source("OLD_SOURCE")
            self.assertTrue(result)

    def test_close(self):
        """Test resource cleanup."""
        self.config_manager.close()

        self.mock_config.close.assert_called_once()
        self.mock_config_mgr.close.assert_called_once()

    def test_properties(self):
        """Test class properties."""
        # Test current_config_id
        self.config_manager._current_config_id = 5
        self.assertEqual(self.config_manager.current_config_id, 5)

        # Test is_initialized
        self.assertTrue(self.config_manager.is_initialized)

        self.config_manager._sz_config = None
        self.assertFalse(self.config_manager.is_initialized)


    def test_initialize_senzing_partial_failure(self):
        """Test Senzing initialization with partial component failure."""
        from senzing import SzError

        # Mock factory succeeds but config manager creation fails
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory_class:
            mock_factory = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.create_configmanager.side_effect = SzError("Config manager error")

            manager = ConfigurationManager()
            result = manager.initialize_senzing()

            self.assertFalse(result)

    def test_get_default_config_id_sz_error_with_details(self):
        """Test get_default_config_id with detailed SzError."""
        from senzing import SzError

        error_msg = "Database connection failed"
        self.mock_config_mgr.get_default_config_id.side_effect = SzError(error_msg)

        result = self.config_manager.get_default_config_id()

        self.assertIsNone(result)

    def test_get_config_registry_empty_response(self):
        """Test get_config_registry with empty response."""
        self.mock_config_mgr.get_configs.return_value = ""

        result = self.config_manager.get_config_registry()

        self.assertEqual(result, "")

    def test_load_config_default_id_none(self):
        """Test load_config when default config ID is None - should create new config."""
        self.mock_config_mgr.get_default_config_id.return_value = None

        # Mock creation of new default config
        template_config = Mock()
        template_config.export.return_value = '{"G2_CONFIG": {"CFG_DSRC": []}}'
        self.mock_config_mgr.create_config_from_template.return_value = template_config
        self.mock_config_mgr.register_config.return_value = 1

        final_config = Mock()
        final_config.export.return_value = '{"G2_CONFIG": {"CFG_DSRC": []}}'
        self.mock_config_mgr.create_config_from_config_id.return_value = final_config

        self.config_manager.load_config()

        # Verify new config creation process
        self.mock_config_mgr.create_config_from_template.assert_called_once()
        self.mock_config_mgr.register_config.assert_called_once()
        self.mock_config_mgr.set_default_config_id.assert_called_once_with(1)

    def test_load_config_get_config_failure(self):
        """Test load_config when create_config_from_config_id fails."""
        from senzing import SzError

        self.mock_config_mgr.create_config_from_config_id.side_effect = SzError("Config not found")

        # New implementation returns False instead of raising exception
        result = self.config_manager.load_config(123)
        self.assertFalse(result)

    def test_load_config_import_failure(self):
        """Test load_config when export fails."""
        from senzing import SzError

        self.mock_config_mgr.create_config_from_config_id.return_value = self.mock_config
        self.mock_config.export.side_effect = SzError("Export failed")

        # New implementation returns False instead of raising exception
        result = self.config_manager.load_config(123)
        self.assertFalse(result)

    def test_get_current_config_sz_error(self):
        """Test get_current_config with SzError."""
        from senzing import SzError

        self.mock_config.export.side_effect = SzError("Export failed")

        result = self.config_manager.get_current_config()

        self.assertIsNone(result)

    def test_save_config_export_failure(self):
        """Test save_config when export_config fails."""
        from senzing import SzError

        self.mock_config.export.side_effect = SzError("Export failed")

        result = self.config_manager.save_config("Test comment")

        self.assertIsNone(result)
        self.mock_config_mgr.register_config.assert_not_called()

    def test_save_config_add_config_failure(self):
        """Test save_config when register_config fails."""
        from senzing import SzError

        self.mock_config.export.return_value = '{"test": "config"}'
        self.mock_config_mgr.register_config.side_effect = SzError("Add failed")

        result = self.config_manager.save_config("Test comment")

        self.assertIsNone(result)

    def test_import_config_from_file_pathlib_path(self):
        """Test import from file using pathlib.Path."""
        test_config = '{"G2_CONFIG": {"test": "data"}}'

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(test_config)
            temp_path = Path(f.name)

        try:
            result = self.config_manager.import_config_from_file(temp_path)

            self.assertTrue(result)
            self.mock_config.import_config.assert_called_once_with(test_config)
        finally:
            temp_path.unlink()

    def test_import_config_from_file_sz_error(self):
        """Test import from file with SzError during import."""
        from senzing import SzError

        test_config = '{"G2_CONFIG": {"test": "data"}}'

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(test_config)
            temp_path = f.name

        self.mock_config.import_config.side_effect = SzError("Import failed")

        try:
            result = self.config_manager.import_config_from_file(temp_path)

            self.assertFalse(result)
        finally:
            Path(temp_path).unlink()

    def test_import_config_from_file_io_error(self):
        """Test import from file with IO error."""
        # Create a file that we can't read (simulate permission error)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        # Delete the file to simulate it not existing
        Path(temp_path).unlink()

        result = self.config_manager.import_config_from_file(temp_path)

        self.assertFalse(result)
        self.mock_config.import_config.assert_not_called()

    def test_export_config_to_file_pathlib_path(self):
        """Test export to file using pathlib.Path."""
        test_config = '{"test": "config"}'
        self.mock_config.export.return_value = test_config

        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            temp_path = Path(f.name)

        try:
            result = self.config_manager.export_config_to_file(temp_path)

            self.assertTrue(result)

            # Verify file content
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertEqual(content, test_config)
        finally:
            temp_path.unlink()

    def test_export_config_to_file_sz_error(self):
        """Test export to file with SzError during export."""
        from senzing import SzError

        self.mock_config.export.side_effect = SzError("Export failed")

        result = self.config_manager.export_config_to_file("/tmp/test.json")

        self.assertFalse(result)

    def test_export_config_to_file_permission_error(self):
        """Test export to file with permission error."""
        self.mock_config.export.return_value = '{"test": "config"}'

        # Try to write to a directory that doesn't exist
        result = self.config_manager.export_config_to_file("/nonexistent/path/file.json")

        self.assertFalse(result)

    def test_get_data_sources_invalid_config_structure(self):
        """Test get_data_sources with invalid config structure."""
        # Config without G2_CONFIG key
        invalid_config = '{"INVALID": {"test": "data"}}'
        self.mock_config.export.return_value = invalid_config

        result = self.config_manager.get_data_sources()

        self.assertEqual(result, [])

    def test_get_data_sources_missing_dsrc_key(self):
        """Test get_data_sources with missing CFG_DSRC key."""
        # Config without CFG_DSRC key
        config_without_dsrc = '{"G2_CONFIG": {"OTHER": "data"}}'
        self.mock_config.export.return_value = config_without_dsrc

        result = self.config_manager.get_data_sources()

        self.assertEqual(result, [])

    def test_get_data_sources_malformed_json(self):
        """Test get_data_sources with malformed JSON."""
        self.mock_config.export.return_value = 'invalid json'

        result = self.config_manager.get_data_sources()

        self.assertIsNone(result)

    def test_add_data_source_sz_error(self):
        """Test add_data_source with SzError."""
        from senzing import SzError

        self.mock_config.add_data_source.side_effect = SzError("Add failed")

        result = self.config_manager.add_data_source("NEW_SOURCE")

        self.assertFalse(result)

    def test_delete_data_source_sz_error(self):
        """Test delete_data_source with SzError."""
        from senzing import SzError

        self.mock_config.delete_data_source.side_effect = SzError("Delete failed")

        result = self.config_manager.delete_data_source("OLD_SOURCE")

        self.assertFalse(result)

    def test_close_with_sz_errors(self):
        """Test close method when SzError occurs during cleanup."""
        from senzing import SzError

        self.mock_config.close.side_effect = SzError("Close failed")
        self.mock_config_mgr.close.side_effect = SzError("Close failed")

        # Should not raise exception even if close operations fail
        self.config_manager.close()

        self.mock_config.close.assert_called_once()
        self.mock_config_mgr.close.assert_called_once()

    def test_close_with_none_components(self):
        """Test close method when components are None."""
        self.config_manager._sz_config = None
        self.config_manager._sz_config_mgr = None

        # Should not raise exception
        self.config_manager.close()

    def test_current_config_id_property(self):
        """Test current_config_id property edge cases."""
        # Test with None
        self.config_manager._current_config_id = None
        self.assertIsNone(self.config_manager.current_config_id)

        # Test with valid ID
        self.config_manager._current_config_id = 42
        self.assertEqual(self.config_manager.current_config_id, 42)

    def test_is_initialized_property_edge_cases(self):
        """Test is_initialized property edge cases."""
        # Both None
        self.config_manager._sz_config = None
        self.config_manager._sz_config_mgr = None
        self.assertFalse(self.config_manager.is_initialized)

        # Only config None
        self.config_manager._sz_config = None
        self.config_manager._sz_config_mgr = Mock()
        self.assertFalse(self.config_manager.is_initialized)

        # Only config_mgr None
        self.config_manager._sz_config = Mock()
        self.config_manager._sz_config_mgr = None
        self.assertFalse(self.config_manager.is_initialized)

        # Both present
        self.config_manager._sz_config = Mock()
        self.config_manager._sz_config_mgr = Mock()
        self.assertTrue(self.config_manager.is_initialized)


if __name__ == '__main__':
    unittest.main()