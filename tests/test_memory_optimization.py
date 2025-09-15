"""Tests for memory optimization and caching functionality."""
import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _config_core import ConfigurationManager


class TestMemoryOptimization:
    """Test memory optimization through configuration caching."""

    def test_config_caching_initialization(self):
        """Test that cache variables are properly initialized."""
        config_mgr = ConfigurationManager()

        assert config_mgr._cached_config_data is None
        assert config_mgr._cached_config_json is None

    @patch('_config_core.SzAbstractFactoryCore')
    @patch('_config_core.get_engine_config')
    def test_cache_clearing_on_initialization(self, mock_get_engine_config, mock_sz_factory):
        """Test that cache is cleared during Senzing initialization."""
        mock_get_engine_config.return_value = '{"test": "config"}'
        mock_factory_instance = Mock()
        mock_sz_factory.return_value = mock_factory_instance
        mock_config_mgr = Mock()
        mock_factory_instance.create_configmanager.return_value = mock_config_mgr
        mock_config_mgr.get_default_config_id.return_value = 1
        mock_config_mgr.create_config_from_config_id.return_value = Mock()

        config_mgr = ConfigurationManager()

        # Set some cached data
        config_mgr._cached_config_data = {"cached": "data"}
        config_mgr._cached_config_json = '{"cached": "json"}'

        # Initialize - should clear cache
        success = config_mgr.initialize_senzing()

        assert success is True
        assert config_mgr._cached_config_data is None
        assert config_mgr._cached_config_json is None

    def test_config_json_caching(self):
        """Test that configuration JSON is cached properly."""
        config_mgr = ConfigurationManager()

        # Mock the _sz_config object
        mock_sz_config = Mock()
        test_config_json = '{"test": "configuration", "large": "data"}'
        mock_sz_config.export.return_value = test_config_json
        config_mgr._sz_config = mock_sz_config

        # First call should export and cache
        result1 = config_mgr.get_current_config()
        assert result1 == test_config_json
        assert config_mgr._cached_config_json == test_config_json
        mock_sz_config.export.assert_called_once()

        # Second call should use cache, not call export again
        result2 = config_mgr.get_current_config()
        assert result2 == test_config_json
        assert config_mgr._cached_config_json == test_config_json
        mock_sz_config.export.assert_called_once()  # Still only called once

    def test_config_data_caching(self):
        """Test that parsed configuration data is cached properly."""
        config_mgr = ConfigurationManager()

        # Mock the _sz_config object
        mock_sz_config = Mock()
        test_config_json = '{"test": "configuration", "G2_CONFIG": {"CFG_DSRC": []}}'
        mock_sz_config.export.return_value = test_config_json
        config_mgr._sz_config = mock_sz_config

        # First call should parse and cache
        result1 = config_mgr.get_config_data()
        expected_data = {"test": "configuration", "G2_CONFIG": {"CFG_DSRC": []}}
        assert result1 == expected_data
        assert config_mgr._cached_config_data == expected_data
        mock_sz_config.export.assert_called_once()

        # Second call should use cached parsed data
        result2 = config_mgr.get_config_data()
        assert result2 == expected_data
        assert config_mgr._cached_config_data == expected_data
        mock_sz_config.export.assert_called_once()  # Still only called once

    def test_cache_clearing_method(self):
        """Test the cache clearing method works correctly."""
        config_mgr = ConfigurationManager()

        # Set cached data
        config_mgr._cached_config_data = {"test": "data"}
        config_mgr._cached_config_json = '{"test": "json"}'

        # Clear cache
        config_mgr._clear_config_cache()

        assert config_mgr._cached_config_data is None
        assert config_mgr._cached_config_json is None

    def test_cache_cleared_on_config_update(self):
        """Test that cache is cleared when configuration is updated."""
        config_mgr = ConfigurationManager()

        # Mock the _sz_config object
        mock_sz_config = Mock()
        config_mgr._sz_config = mock_sz_config

        # Set cached data
        config_mgr._cached_config_data = {"old": "data"}
        config_mgr._cached_config_json = '{"old": "json"}'

        # Update configuration
        new_config_data = {"new": "configuration"}
        success = config_mgr.update_config_data(new_config_data)

        assert success is True
        assert config_mgr._cached_config_data is None
        assert config_mgr._cached_config_json is None
        mock_sz_config.import_config.assert_called_once()

    def test_cache_cleared_on_file_import(self):
        """Test that cache is cleared when importing from file."""
        config_mgr = ConfigurationManager()

        # Mock the _sz_config object
        mock_sz_config = Mock()
        config_mgr._sz_config = mock_sz_config

        # Create a temporary config file
        import tempfile
        import json

        test_config = {"test": "file_config"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            temp_file_path = f.name

        try:
            # Set cached data
            config_mgr._cached_config_data = {"old": "data"}
            config_mgr._cached_config_json = '{"old": "json"}'

            # Import from file
            success = config_mgr.import_config_from_file(temp_file_path)

            assert success is True
            assert config_mgr._cached_config_data is None
            assert config_mgr._cached_config_json is None
            mock_sz_config.import_config.assert_called_once()
        finally:
            os.unlink(temp_file_path)

    @patch('_config_core.SzAbstractFactoryCore')
    @patch('_config_core.get_engine_config')
    def test_cache_cleared_on_load_config(self, mock_get_engine_config, mock_sz_factory):
        """Test that cache is cleared when loading a different configuration."""
        mock_get_engine_config.return_value = '{"test": "config"}'
        mock_factory_instance = Mock()
        mock_sz_factory.return_value = mock_factory_instance
        mock_config_mgr = Mock()
        mock_factory_instance.create_configmanager.return_value = mock_config_mgr
        mock_sz_config = Mock()
        mock_config_mgr.get_default_config_id.return_value = 1
        mock_config_mgr.create_config_from_config_id.return_value = mock_sz_config
        mock_config_mgr.get_config.return_value = '{"config": "from_id"}'

        config_mgr = ConfigurationManager()
        config_mgr.initialize_senzing()

        # Set cached data
        config_mgr._cached_config_data = {"old": "data"}
        config_mgr._cached_config_json = '{"old": "json"}'

        # Load different configuration
        success = config_mgr.load_config(2)

        assert success is True
        assert config_mgr._cached_config_data is None
        assert config_mgr._cached_config_json is None

    def test_multiple_record_access_uses_cache(self):
        """Test that multiple record access operations use cached data."""
        config_mgr = ConfigurationManager()

        # Mock the _sz_config object
        mock_sz_config = Mock()
        test_config_json = '''
        {
            "G2_CONFIG": {
                "CFG_ERRULE": [
                    {"ERRULE_ID": 100, "ERRULE_CODE": "TEST_RULE"}
                ],
                "CFG_ERFRAG": [
                    {"ERFRAG_ID": 16, "ERFRAG_CODE": "TEST_FRAG"}
                ],
                "CFG_FTYPE": [
                    {"FTYPE_ID": 1, "FTYPE_CODE": "NAME"}
                ]
            }
        }
        '''
        mock_sz_config.export.return_value = test_config_json
        config_mgr._sz_config = mock_sz_config

        # Access multiple record types - should only call export once
        rules = config_mgr.get_rules()
        fragments = config_mgr.get_fragments()
        features = config_mgr.get_features()

        assert len(rules) == 1
        assert len(fragments) == 1
        assert len(features) == 1

        # Should have only called export once due to caching
        mock_sz_config.export.assert_called_once()


if __name__ == "__main__":
    # Run the memory optimization tests
    pytest.main([__file__, "-v", "--tb=short"])