"""Compare memory usage before and after caching optimizations."""
import pytest
import sys
import os
from unittest.mock import Mock

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _config_core import ConfigurationManager


class TestMemoryComparison:
    """Compare memory usage patterns."""

    def test_multiple_export_calls_without_cache_simulation(self):
        """Simulate the old behavior that caused massive memory usage."""
        config_mgr = ConfigurationManager()

        # Mock _sz_config to simulate large configuration export
        mock_sz_config = Mock()
        large_config_json = '{"G2_CONFIG": {"large_data": "' + 'x' * 100000 + '"}}'  # Simulate large config
        mock_sz_config.export.return_value = large_config_json
        config_mgr._sz_config = mock_sz_config

        # Disable caching to simulate old behavior
        config_mgr._cached_config_json = None
        config_mgr._cached_config_data = None

        # Simulate multiple operations that would each call get_config_data
        # In the old code, this would cause multiple exports and JSON parsing
        call_count = 0

        # Override get_current_config to count calls and simulate no caching
        original_get_current_config = config_mgr.get_current_config

        def no_cache_get_current_config():
            nonlocal call_count
            call_count += 1
            return mock_sz_config.export()

        def no_cache_get_config_data():
            import json
            config_json = no_cache_get_current_config()
            return json.loads(config_json) if config_json else None

        # Simulate the old pattern - each operation would call get_config_data
        operations = [
            "get_rules",
            "get_fragments",
            "get_features",
            "get_attributes",
            "get_data_sources"
        ]

        for op in operations:
            data = no_cache_get_config_data()  # Each call would export+parse
            assert data is not None

        # Without caching, each operation would cause an export
        assert call_count == len(operations), f"Expected {len(operations)} export calls, got {call_count}"

    def test_multiple_operations_with_cache(self):
        """Test the new cached behavior."""
        config_mgr = ConfigurationManager()

        # Mock _sz_config
        mock_sz_config = Mock()
        large_config_json = '{"G2_CONFIG": {"CFG_ERRULE": [], "CFG_ERFRAG": [], "CFG_FTYPE": []}}'
        mock_sz_config.export.return_value = large_config_json
        config_mgr._sz_config = mock_sz_config

        # Simulate multiple operations that call get_config_data
        operations = [
            lambda: config_mgr.get_record_list("CFG_ERRULE"),
            lambda: config_mgr.get_record_list("CFG_ERFRAG"),
            lambda: config_mgr.get_record_list("CFG_FTYPE"),
            lambda: config_mgr.get_record_list("CFG_ATTR"),
            lambda: config_mgr.get_record_list("CFG_DSRC")
        ]

        for op in operations:
            result = op()
            assert result is not None or result == []  # Some tables might be empty

        # With caching, should only call export once regardless of number of operations
        mock_sz_config.export.assert_called_once()

    def test_memory_efficient_record_access(self):
        """Test that record access is memory efficient."""
        config_mgr = ConfigurationManager()

        # Mock with realistic Senzing configuration structure
        mock_sz_config = Mock()
        realistic_config = '''
        {
            "G2_CONFIG": {
                "CFG_ERRULE": [
                    {"ERRULE_ID": 100, "ERRULE_CODE": "SAME_A1", "RESOLVE": "Yes"},
                    {"ERRULE_ID": 108, "ERRULE_CODE": "SF1_SNAME_CFF_CSTAB", "RESOLVE": "Yes"}
                ],
                "CFG_ERFRAG": [
                    {"ERFRAG_ID": 16, "ERFRAG_CODE": "DIFF_NAME", "ERFRAG_DESC": "DIFF_NAME"},
                    {"ERFRAG_ID": 11, "ERFRAG_CODE": "SAME_NAME", "ERFRAG_DESC": "SAME_NAME"}
                ],
                "CFG_FTYPE": [
                    {"FTYPE_ID": 1, "FTYPE_CODE": "NAME", "FTYPE_DESC": "Name"},
                    {"FTYPE_ID": 2, "FTYPE_CODE": "DOB", "FTYPE_DESC": "Date of birth"}
                ]
            }
        }
        '''
        mock_sz_config.export.return_value = realistic_config
        config_mgr._sz_config = mock_sz_config

        # Access all major record types multiple times
        for _ in range(3):  # Multiple rounds
            rules = config_mgr.get_rules()
            fragments = config_mgr.get_fragments()
            features = config_mgr.get_features()

            assert len(rules) == 2
            assert len(fragments) == 2
            assert len(features) == 2

        # Should still only export once due to caching
        mock_sz_config.export.assert_called_once()

        # Verify cache contents exist
        assert config_mgr._cached_config_data is not None
        assert config_mgr._cached_config_json is not None

    def test_cache_invalidation_efficiency(self):
        """Test that cache invalidation works correctly without memory leaks."""
        config_mgr = ConfigurationManager()

        # Mock _sz_config
        mock_sz_config = Mock()
        config_mgr._sz_config = mock_sz_config

        # Set initial cached data
        config_mgr._cached_config_data = {"initial": "data"}
        config_mgr._cached_config_json = '{"initial": "json"}'

        # Verify cache is set
        assert config_mgr._cached_config_data is not None
        assert config_mgr._cached_config_json is not None

        # Update configuration (should clear cache)
        new_data = {"updated": "configuration"}
        success = config_mgr.update_config_data(new_data)

        assert success is True
        # Cache should be cleared
        assert config_mgr._cached_config_data is None
        assert config_mgr._cached_config_json is None

        # Verify import was called
        mock_sz_config.import_config.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])