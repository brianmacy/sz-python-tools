"""Tests for the modular configuration manager."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools', 'configtool'))

try:
    from configtool.core.unified_manager import UnifiedConfigurationManager
except ImportError:
    # Skip tests if modular version not available
    import pytest
    pytest.skip("Modular configuration manager not available", allow_module_level=True)


class TestUnifiedConfigurationManager(unittest.TestCase):
    """Test cases for UnifiedConfigurationManager class - mirrors the original test structure."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = UnifiedConfigurationManager()

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
        manager = UnifiedConfigurationManager("/path/to/ini")
        self.assertEqual(manager._ini_file_name, "/path/to/ini")

        # Test without ini_file_name
        manager = UnifiedConfigurationManager()
        self.assertIsNone(manager._ini_file_name)

    @patch('configtool.core.base_manager.get_engine_config')
    @patch('configtool.core.base_manager.SzAbstractFactoryCore')
    def test_initialize_senzing_success(self, mock_factory_class, mock_get_engine_config):
        """Test successful Senzing initialization."""
        # Setup mocks
        mock_get_engine_config.return_value = "mock_engine_config"

        mock_factory = Mock()
        mock_config_mgr = Mock()

        mock_factory_class.return_value = mock_factory
        mock_factory.create_configmanager.return_value = mock_config_mgr

        manager = UnifiedConfigurationManager()

        # Mock the load_config method to avoid complex setup
        with patch.object(manager, 'load_config'):
            result = manager.initialize_senzing()

        self.assertTrue(result)
        self.assertEqual(manager._sz_factory, mock_factory)
        self.assertEqual(manager._sz_config_mgr, mock_config_mgr)

    def test_add_data_source_success(self):
        """Test successful data source addition."""
        # Mock get_config_data to return proper config structure
        mock_config = {
            'G2_CONFIG': {
                'CFG_DSRC': [
                    {'DSRC_ID': 1, 'DSRC_CODE': 'EXISTING_SOURCE'}
                ]
            }
        }

        with patch.object(self.config_manager, 'get_config_data', return_value=mock_config):
            with patch.object(self.config_manager, 'update_config_data', return_value=True):
                result = self.config_manager.add_data_source("NEW_SOURCE")
                self.assertTrue(result)

    def test_add_data_source_no_config(self):
        """Test add_data_source when no config loaded."""
        self.config_manager._sz_config = None
        self.config_manager.config_data = None

        result = self.config_manager.add_data_source("NEW_SOURCE")

        self.assertFalse(result)

    def test_delete_data_source_success(self):
        """Test successful data source deletion."""
        # Setup config_data with the data source to delete
        test_config = {
            'G2_CONFIG': {
                'CFG_DSRC': [
                    {'DSRC_ID': 1, 'DSRC_CODE': 'OLD_SOURCE'},
                    {'DSRC_ID': 2, 'DSRC_CODE': 'KEEP_SOURCE'}
                ]
            }
        }
        self.config_manager._cached_config_data = test_config
        self.config_manager._config_cache_set = True

        # Mock the update_config_data method to return True
        with patch.object(self.config_manager, 'update_config_data', return_value=True):
            result = self.config_manager.delete_data_source("OLD_SOURCE")
            self.assertTrue(result)

    def test_get_data_sources_success(self):
        """Test successful data sources retrieval."""
        # Setup config_data for the test by setting cached data directly
        test_config = {
            'G2_CONFIG': {
                'CFG_DSRC': [
                    {'DSRC_ID': 1, 'DSRC_CODE': 'SOURCE_1'},
                    {'DSRC_ID': 2, 'DSRC_CODE': 'SOURCE_2'}
                ]
            }
        }
        self.config_manager._cached_config_data = test_config
        self.config_manager._config_cache_set = True

        result = self.config_manager.get_data_sources()

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['DSRC_CODE'], 'SOURCE_1')

    def test_get_data_sources_no_config(self):
        """Test get_data_sources when no config loaded."""
        self.config_manager._cached_config_data = None
        self.config_manager._config_cache_set = True

        result = self.config_manager.get_data_sources()

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

    def test_close(self):
        """Test resource cleanup."""
        self.config_manager.close()

        self.mock_config.close.assert_called_once()
        self.mock_config_mgr.close.assert_called_once()
        self.mock_factory.close.assert_called_once()

    def test_current_config_id_property(self):
        """Test current_config_id property."""
        self.config_manager._current_config_id = 123
        self.assertEqual(self.config_manager.current_config_id, 123)

    def test_is_initialized_property(self):
        """Test is_initialized property."""
        # Test initialized state
        self.assertTrue(self.config_manager.is_initialized())

        # Test uninitialized state
        self.config_manager._sz_factory = None
        self.assertFalse(self.config_manager.is_initialized())

    def test_get_statistics_no_config(self):
        """Test statistics with no configuration data."""
        self.config_manager._cached_config_data = None
        self.config_manager._config_cache_set = True
        stats = self.config_manager.get_statistics()
        self.assertEqual(stats, {})

    def test_get_statistics_with_config(self):
        """Test statistics with valid configuration data."""
        test_config = {
            'G2_CONFIG': {
                'CFG_DSRC': [{'DSRC_ID': 1}],
                'CFG_FTYPE': [{'FTYPE_ID': 1}, {'FTYPE_ID': 2}],
                'CFG_ATTR': []
            }
        }
        self.config_manager._cached_config_data = test_config
        self.config_manager._config_cache_set = True
        self.config_manager._current_config_id = 5
        self.config_manager.config_updated = True

        stats = self.config_manager.get_statistics()
        self.assertEqual(stats['dataSources'], 1)
        self.assertEqual(stats['features'], 2)
        self.assertEqual(stats['attributes'], 0)
        self.assertEqual(stats['configId'], 5)
        self.assertTrue(stats['hasChanges'])

    def test_apply_filter_basic(self):
        """Test basic filtering functionality."""
        records = [
            {'name': 'John Doe', 'city': 'New York'},
            {'name': 'Jane Smith', 'city': 'Los Angeles'},
            {'name': 'Bob Johnson', 'city': 'Chicago'}
        ]

        # Test case-insensitive filtering
        filtered = self.config_manager.apply_filter(records, 'john')
        self.assertEqual(len(filtered), 2)  # John Doe and Bob Johnson

        # Test no matches
        filtered = self.config_manager.apply_filter(records, 'xyz')
        self.assertEqual(len(filtered), 0)

        # Test empty filter
        filtered = self.config_manager.apply_filter(records, '')
        self.assertEqual(len(filtered), 3)

    def test_string_representations(self):
        """Test string representation methods."""
        # Set up some config data to avoid JSON serialization issues
        test_config = {'G2_CONFIG': {'CFG_DSRC': []}}
        self.config_manager._cached_config_data = test_config
        self.config_manager._config_cache_set = True

        str_repr = str(self.config_manager)
        self.assertIn('ConfigurationManager', str_repr)

        detailed_repr = repr(self.config_manager)
        self.assertIn('UnifiedConfigurationManager', detailed_repr)

    def test_domain_specific_methods(self):
        """Test that domain-specific methods are available."""
        # Test that all domain methods are accessible
        domain_methods = [
            'get_features', 'get_attributes', 'get_elements',  # Feature domain
            'get_comparison_functions', 'get_distinct_calls',  # Function domain
            'get_rules', 'validate_configuration',             # Rules domain
            'get_thresholds', 'get_scoring_sets'               # System domain
        ]

        for method in domain_methods:
            self.assertTrue(hasattr(self.config_manager, method),
                          f"Missing domain method: {method}")


if __name__ == '__main__':
    unittest.main()