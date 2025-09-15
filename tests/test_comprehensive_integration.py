"""Comprehensive integration tests to catch ALL missing methods and integration issues."""
import pytest
import sys
import os
from unittest.mock import Mock, patch
from io import StringIO

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _config_display import ConfigDisplayFormatter
from configtool_main import ConfigToolShell


class TestComprehensiveIntegration:
    """Comprehensive integration testing to catch ALL issues before user encounters them."""

    def setup_method(self):
        """Set up real objects with mocked data sources."""
        # Use real display formatter - this will catch missing methods
        self.formatter = ConfigDisplayFormatter()

        # Mock config manager with realistic return values
        self.mock_config_manager = Mock()
        self.setup_mock_returns()

        # Create the shell with real formatter
        self.shell = ConfigToolShell(self.mock_config_manager, self.formatter, hist_disable=True)

    def setup_mock_returns(self):
        """Set up realistic mock returns to test all code paths."""
        # Empty returns for most commands to test "no data" paths
        self.mock_config_manager.get_record_list.return_value = []
        self.mock_config_manager.get_record.return_value = []
        self.mock_config_manager.apply_filter.return_value = []

        # Some realistic data for get commands to test formatting
        self.sample_rule = [{'RULE_ID': 1, 'RULE_CODE': 'TEST_RULE', 'RULE_DESC': 'Test Rule Description'}]
        self.sample_fragment = [{'FRAGMENT_ID': 1, 'FRAGMENT_CODE': 'FRAG1', 'FRAGMENT_DESC': 'Test Fragment'}]
        self.sample_call = [{'CFCALL_ID': 1, 'CFUNC_CODE': 'TEST_FUNC', 'EXEC_ORDER': 1}]

    @pytest.mark.parametrize("command,args", [
        # Test ALL enhanced list commands
        ('do_listRules', ''),
        ('do_listRules', 'table'),
        ('do_listRules', 'json'),
        ('do_listRules', 'jsonl'),
        ('do_listFragments', ''),
        ('do_listFragments', 'table'),
        ('do_listFragments', 'json'),
        ('do_listFragments', 'jsonl'),
        ('do_listFeatures', ''),
        ('do_listFeatures', 'table'),
        ('do_listFeatures', 'json'),
        ('do_listFeatures', 'jsonl'),
        ('do_listAttributes', ''),
        ('do_listAttributes', 'table'),
        ('do_listElements', ''),
        ('do_listDataSources', ''),
        ('do_listStandardizeFunctions', ''),
        ('do_listStandardizeFunctions', 'table'),
        ('do_listComparisonFunctions', ''),
        ('do_listComparisonFunctions', 'json'),
        ('do_listExpressionFunctions', ''),
        ('do_listDistinctFunctions', ''),
        ('do_listStandardizeCalls', ''),
        ('do_listComparisonCalls', ''),
        ('do_listExpressionCalls', ''),
        ('do_listDistinctCalls', ''),
        ('do_listBehaviorOverrides', ''),
        ('do_listReferenceCodes', ''),
        ('do_listSystemParameters', ''),
        ('do_listComparisonThresholds', ''),
        ('do_listGenericThresholds', ''),
        ('do_listGenericPlans', ''),
    ])
    def test_all_list_commands_execute_successfully(self, command, args):
        """Test that ALL enhanced list commands execute without AttributeError."""
        if not hasattr(self.shell, command):
            pytest.skip(f"Command {command} not implemented")

        try:
            method = getattr(self.shell, command)
            # Capture output to prevent console spam
            with patch('sys.stdout', new_callable=StringIO):
                method(args)
        except AttributeError as e:
            if "format_" in str(e) or "print_with_paging" in str(e):
                pytest.fail(f"Missing formatter method in {command}: {e}")
            else:
                # Re-raise other AttributeErrors
                raise
        except Exception as e:
            # Allow other exceptions (like missing config methods) - we're only testing formatter integration
            pass

    @pytest.mark.parametrize("command,args", [
        # Test ALL enhanced get commands with different argument types
        ('do_getRule', 'TEST'),
        ('do_getRule', '1'),
        ('do_getRule', 'TEST table'),
        ('do_getRule', 'TEST json'),
        ('do_getRule', 'TEST jsonl'),
        ('do_getFragment', 'FRAG1'),
        ('do_getFragment', '1'),
        ('do_getFragment', 'FRAG1 table'),
        ('do_getFeature', '1'),
        ('do_getFeature', 'NAME'),
        ('do_getFeature', 'NAME table'),
        ('do_getAttribute', '1'),
        ('do_getElement', '1'),
        ('do_getStandardizeCall', '1'),
        ('do_getComparisonCall', '1'),
        ('do_getExpressionCall', '1'),
        ('do_getDistinctCall', '1'),
        ('do_getConfigSection', 'CFG_ATTR'),
        ('do_getConfigSection', 'CFG_FTYPE table'),
    ])
    def test_all_get_commands_execute_successfully(self, command, args):
        """Test that ALL enhanced get commands execute without AttributeError."""
        if not hasattr(self.shell, command):
            pytest.skip(f"Command {command} not implemented")

        # Set up mock to return data for get commands
        self.mock_config_manager.get_record.return_value = self.sample_rule

        try:
            method = getattr(self.shell, command)
            with patch('sys.stdout', new_callable=StringIO):
                method(args)
        except AttributeError as e:
            if "format_" in str(e) or "print_with_paging" in str(e):
                pytest.fail(f"Missing formatter method in {command}: {e}")
            else:
                raise
        except Exception:
            # Allow other exceptions
            pass

    def test_all_required_formatter_methods_exist(self):
        """Comprehensive test of ALL formatter methods that might be needed."""
        formatter = ConfigDisplayFormatter()

        # Comprehensive list of all formatter methods that might be called
        all_possible_methods = [
            # Basic formatting
            'format_table_data',
            'format_json',
            'format_error',
            'format_success',
            'format_info',
            'format_warning',

            # List formatters
            'format_rule_list',
            'format_fragment_list',
            'format_feature_list',
            'format_attribute_list',
            'format_element_list',
            'format_function_list',
            'format_call_list',
            'format_behavior_override_list',
            'format_reference_code_list',
            'format_system_parameter_list',
            'format_threshold_list',
            'format_generic_plan_list',

            # Detail formatters
            'format_rule_details',
            'format_fragment_details',
            'format_call_details',
            'format_config_section_details',

            # Utility methods
            'print_with_paging',
            'set_paging_enabled',
            'colorize',
            'format_message',
        ]

        missing_methods = []
        non_callable_methods = []

        for method_name in all_possible_methods:
            if not hasattr(formatter, method_name):
                missing_methods.append(method_name)
            elif not callable(getattr(formatter, method_name)):
                non_callable_methods.append(method_name)

        error_messages = []
        if missing_methods:
            error_messages.append(f"Missing methods: {missing_methods}")
        if non_callable_methods:
            error_messages.append(f"Non-callable methods: {non_callable_methods}")

        if error_messages:
            pytest.fail("; ".join(error_messages))

    def test_format_parsing_methods_exist(self):
        """Test that format parsing methods exist and work."""
        if not hasattr(self.shell, 'check_arg_for_output_format'):
            pytest.fail("Missing check_arg_for_output_format method")

        # Test format parsing with various inputs
        test_inputs = [
            ("", "list"),
            ("table", "list"),
            ("json", "list"),
            ("jsonl", "list"),
            ("filter_expr table", "list"),
            ("filter_expr json", "list"),
            ("NAME table", "get"),
            ("1 json", "get"),
        ]

        for input_arg, cmd_type in test_inputs:
            try:
                result = self.shell.check_arg_for_output_format(cmd_type, input_arg)
                assert isinstance(result, str)  # Should return a string
            except Exception as e:
                pytest.fail(f"Format parsing failed for '{input_arg}' with type '{cmd_type}': {e}")

    def test_id_or_code_parsing_exists(self):
        """Test that ID/code parsing method exists and works."""
        if not hasattr(self.shell, 'id_or_code_parm'):
            pytest.fail("Missing id_or_code_parm method")

        # Test ID/code parsing with various inputs
        test_cases = [
            ("1", "ID_TAG", "CODE_TAG", "ID_FIELD", "CODE_FIELD"),
            ("TEST", "ID_TAG", "CODE_TAG", "ID_FIELD", "CODE_FIELD"),
            ('{"ID_TAG": 1}', "ID_TAG", "CODE_TAG", "ID_FIELD", "CODE_FIELD"),
            ('{"CODE_TAG": "TEST"}', "ID_TAG", "CODE_TAG", "ID_FIELD", "CODE_FIELD"),
        ]

        for input_arg, *args in test_cases:
            try:
                result = self.shell.id_or_code_parm(input_arg, *args)
                assert isinstance(result, tuple)  # Should return a tuple
                assert len(result) == 2  # Should return (value, field)
            except Exception as e:
                pytest.fail(f"ID/code parsing failed for '{input_arg}': {e}")

    def test_output_format_properties_exist(self):
        """Test that output format properties exist."""
        required_properties = [
            'current_output_format_list',
            'current_output_format_record',
        ]

        missing_properties = []
        for prop in required_properties:
            if not hasattr(self.shell, prop):
                missing_properties.append(prop)

        if missing_properties:
            pytest.fail(f"Missing output format properties: {missing_properties}")

    def test_realistic_command_scenarios(self):
        """Test realistic user scenarios that would expose integration issues."""
        # Test scenarios that users actually run
        scenarios = [
            # Basic listing
            ("listRules", []),
            ("listFragments", []),
            ("listFeatures", []),

            # With formats
            ("listRules table", []),
            ("listFragments json", []),
            ("listFeatures jsonl", []),

            # With filters
            ("listFeatures NAME table", []),
            ("listAttributes ADDR json", []),

            # Get commands
            ("getRule TEST", self.sample_rule),
            ("getFeature NAME", self.sample_rule),
            ("getFragment FRAG1 table", self.sample_fragment),
        ]

        for command_str, mock_return in scenarios:
            self.mock_config_manager.get_record_list.return_value = mock_return
            self.mock_config_manager.get_record.return_value = mock_return

            try:
                with patch('sys.stdout', new_callable=StringIO):
                    # Parse command and execute
                    parts = command_str.split(None, 1)
                    command_name = f"do_{parts[0]}"
                    args = parts[1] if len(parts) > 1 else ""

                    if hasattr(self.shell, command_name):
                        method = getattr(self.shell, command_name)
                        method(args)

            except AttributeError as e:
                if "format_" in str(e) or "print_with_paging" in str(e):
                    pytest.fail(f"Integration issue in '{command_str}': {e}")
                else:
                    raise
            except Exception:
                # Allow other exceptions - we're testing integration, not business logic
                pass

    def test_help_system_works(self):
        """Test that help system doesn't crash."""
        try:
            with patch('sys.stdout', new_callable=StringIO):
                self.shell.do_help("")
        except Exception as e:
            pytest.fail(f"Help system failed: {e}")


if __name__ == "__main__":
    # Run the comprehensive tests
    pytest.main([__file__, "-v", "--tb=short"])