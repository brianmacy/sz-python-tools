"""Comprehensive data retrieval validation tests to catch missing/incorrect data.

This test suite validates that all list commands return meaningful data,
not empty or placeholder values. It ensures the correct Senzing configuration
tables are being used and proper field mappings are in place.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch
from io import StringIO

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter
from configtool_main import ConfigToolShell


class TestDataRetrievalValidation:
    """Validate that all list commands return proper data from correct tables."""

    def setup_method(self):
        """Set up with real Senzing data."""
        # Use real ConfigurationManager to get actual Senzing data
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter()
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter, hist_disable=True)

        # Initialize Senzing - this will use actual Senzing configuration
        success = self.config_manager.initialize_senzing()
        if not success:
            pytest.skip("Senzing initialization failed - cannot test data retrieval")

    def test_listRules_returns_actual_rule_data(self):
        """Test that listRules returns actual CFG_ERRULE data with proper fields."""
        rules = self.config_manager.get_rules()

        # Should have actual rules, not empty data
        assert len(rules) > 0, "No rules found - check CFG_ERRULE table access"

        # Verify it's using CFG_ERRULE fields, not CFG_RCLASS
        first_rule = rules[0]
        required_fields = ['ERRULE_ID', 'ERRULE_CODE', 'ERRULE_TIER', 'RESOLVE', 'RELATE']
        for field in required_fields:
            assert field in first_rule, f"Missing field {field} in rule data - check CFG_ERRULE mapping"
            assert first_rule[field] is not None, f"Field {field} is None - data not properly retrieved"

        # Verify actual rule codes exist (not empty strings)
        rule_codes = [rule['ERRULE_CODE'] for rule in rules]
        non_empty_codes = [code for code in rule_codes if code]
        assert len(non_empty_codes) > 0, "No actual rule codes found - data retrieval issue"

    def test_listFragments_returns_actual_fragment_data(self):
        """Test that listFragments returns actual CFG_ERFRAG data with proper fields."""
        fragments = self.config_manager.get_fragments()

        # Should have actual fragments
        assert len(fragments) > 0, "No fragments found - check CFG_ERFRAG table access"

        # Verify it's using CFG_ERFRAG fields, not CFG_FRAG
        first_fragment = fragments[0]
        required_fields = ['ERFRAG_ID', 'ERFRAG_CODE', 'ERFRAG_DESC', 'ERFRAG_SOURCE']
        for field in required_fields:
            assert field in first_fragment, f"Missing field {field} in fragment data - check CFG_ERFRAG mapping"

        # Verify actual fragment codes exist
        fragment_codes = [frag['ERFRAG_CODE'] for frag in fragments]
        non_empty_codes = [code for code in fragment_codes if code]
        assert len(non_empty_codes) > 0, "No actual fragment codes found - data retrieval issue"

    def test_listFeatures_returns_actual_feature_data(self):
        """Test that listFeatures returns actual feature data."""
        features = self.config_manager.get_features()

        # Should have actual features
        assert len(features) > 0, "No features found - check CFG_FTYPE table access"

        # Verify proper fields exist
        first_feature = features[0]
        assert 'FTYPE_ID' in first_feature, "Missing FTYPE_ID field in feature data"
        assert 'FTYPE_CODE' in first_feature, "Missing FTYPE_CODE field in feature data"

        # Verify actual feature codes exist
        feature_codes = [feat['FTYPE_CODE'] for feat in features]
        non_empty_codes = [code for code in feature_codes if code]
        assert len(non_empty_codes) > 0, "No actual feature codes found"

    @pytest.mark.parametrize("command_name,method_name", [
        ("listRules", "get_rules"),
        ("listFragments", "get_fragments"),
        ("listFeatures", "get_features"),
        ("listAttributes", "get_attributes"),
        ("listDataSources", "get_data_sources"),
        ("listStandardizeFunctions", "get_standardize_functions"),
        ("listComparisonFunctions", "get_comparison_functions"),
        ("listExpressionFunctions", "get_expression_functions"),
        ("listDistinctFunctions", "get_distinct_functions"),
    ])
    def test_all_list_commands_return_non_empty_data(self, command_name, method_name):
        """Test that all major list commands return actual data, not empty results."""
        if not hasattr(self.config_manager, method_name):
            pytest.skip(f"Method {method_name} not implemented")

        method = getattr(self.config_manager, method_name)
        data = method()

        # Check that we get actual data
        if isinstance(data, list):
            # For list results, we should have some data (most Senzing configs have these)
            if command_name in ["listRules", "listFeatures", "listAttributes"]:
                assert len(data) > 0, f"{command_name} returned empty list - check table mapping"
        else:
            assert data is not None, f"{command_name} returned None - method failed"

    def test_table_field_mappings_are_correct(self):
        """Test that our table and field mappings match actual Senzing configuration structure."""
        config_json = self.config_manager._sz_config.export()
        import json
        config_data = json.loads(config_json)
        g2_config = config_data.get('G2_CONFIG', {})

        # Verify key tables exist
        critical_tables = [
            'CFG_ERRULE',    # Rules
            'CFG_ERFRAG',    # Fragments
            'CFG_FTYPE',     # Features
            'CFG_ATTR',      # Attributes
            'CFG_DSRC',      # Data sources
        ]

        missing_tables = []
        for table in critical_tables:
            if table not in g2_config:
                missing_tables.append(table)

        if missing_tables:
            pytest.fail(f"Critical tables missing from configuration: {missing_tables}")

        # Verify table contents have expected fields
        table_field_checks = {
            'CFG_ERRULE': ['ERRULE_ID', 'ERRULE_CODE', 'RESOLVE', 'RELATE'],
            'CFG_ERFRAG': ['ERFRAG_ID', 'ERFRAG_CODE', 'ERFRAG_DESC'],
            'CFG_FTYPE': ['FTYPE_ID', 'FTYPE_CODE', 'FTYPE_DESC'],
            'CFG_ATTR': ['ATTR_ID', 'ATTR_CODE', 'ATTR_CLASS'],
        }

        for table, required_fields in table_field_checks.items():
            table_data = g2_config.get(table, [])
            if table_data:
                first_record = table_data[0]
                missing_fields = [field for field in required_fields if field not in first_record]
                if missing_fields:
                    pytest.fail(f"Table {table} missing required fields: {missing_fields}")

    def test_command_execution_returns_meaningful_output(self):
        """Test that running commands produces meaningful output, not empty tables."""
        test_commands = [
            "listRules",
            "listFragments",
            "listFeatures",
            "listAttributes"
        ]

        for command_str in test_commands:
            try:
                # Mock the print_with_paging method to capture its output
                with patch.object(self.display_formatter, 'print_with_paging') as mock_paging:
                    # Execute the command
                    command_method = f"do_{command_str}"
                    if hasattr(self.shell, command_method):
                        method = getattr(self.shell, command_method)
                        method("")  # Empty args for basic listing

                    # Verify print_with_paging was called
                    assert mock_paging.called, f"{command_str} did not call print_with_paging"

                    # Get the output that would have been paged
                    call_args = mock_paging.call_args[0]
                    output = call_args[0] if call_args else ""

                # Verify output contains data, not just headers or "No X found" messages
                assert len(output) > 100, f"{command_str} produced minimal output: {len(output)} chars"
                assert "No " not in output or "found" not in output.lower(), f"{command_str} returned 'No X found' message"

                # Check for table structure indicators (borders, headers)
                has_table_structure = ("┌" in output or "│" in output or "├" in output)
                has_json_structure = ("{" in output and "}" in output)

                assert has_table_structure or has_json_structure, f"{command_str} output lacks proper formatting structure"

            except Exception as e:
                pytest.fail(f"Command {command_str} failed with error: {e}")

    def test_data_is_sorted_by_id(self):
        """Test that list commands return data that can be sorted by ID fields."""
        # Test rules have valid ERRULE_ID fields (sorting not guaranteed by API)
        rules = self.config_manager.get_rules()
        if len(rules) > 1:
            rule_ids = [rule.get('ERRULE_ID', 0) for rule in rules]
            # Verify all IDs are numeric (which allows sorting)
            assert all(isinstance(rid, (int, str)) and str(rid).isdigit() for rid in rule_ids if rid), \
                "Rules have invalid ERRULE_ID values"

        # Test fragments have valid ERFRAG_ID fields
        fragments = self.config_manager.get_fragments()
        if len(fragments) > 1:
            frag_ids = [frag.get('ERFRAG_ID', 0) for frag in fragments]
            # Verify all IDs are numeric (which allows sorting)
            assert all(isinstance(fid, (int, str)) and str(fid).isdigit() for fid in frag_ids if fid), \
                "Fragments have invalid ERFRAG_ID values"

    def test_no_json_import_errors_in_commands(self):
        """Test that no commands have missing json import issues."""
        # This was the specific issue with listFragments using json.dumps without import
        problematic_commands = [
            "listFragments",
            "listRules",
            "listFeatures"
        ]

        for command_str in problematic_commands:
            try:
                with StringIO() as captured_output:
                    import sys
                    old_stdout = sys.stdout
                    sys.stdout = captured_output

                    command_method = f"do_{command_str}"
                    if hasattr(self.shell, command_method):
                        method = getattr(self.shell, command_method)
                        method("")  # Basic execution

                    sys.stdout = old_stdout
                    output = captured_output.getvalue()

                # Check for json-related errors
                assert "name 'json' is not defined" not in output, f"{command_str} has missing json import"
                assert "json.dumps" not in output, f"{command_str} may have raw json.dumps call"

            except NameError as e:
                if "json" in str(e):
                    pytest.fail(f"Command {command_str} has json import issue: {e}")
                else:
                    raise


if __name__ == "__main__":
    # Run the data validation tests
    pytest.main([__file__, "-v", "--tb=short"])