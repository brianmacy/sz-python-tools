"""Critical integration tests to catch missing formatter methods."""
import pytest
from unittest.mock import Mock
import sys
import os

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _config_display import ConfigDisplayFormatter
from configtool_main import ConfigToolShell


class TestFormatterMethodExistence:
    """Test that all required formatter methods exist - would have caught the listRules issue."""

    def test_all_formatter_methods_exist(self):
        """Verify every formatter method called by enhanced commands actually exists."""
        formatter = ConfigDisplayFormatter()

        # These are the methods that enhanced commands depend on
        required_methods = [
            'format_rule_list',           # Used by listRules
            'format_fragment_list',       # Used by listFragments
            'format_function_list',       # Used by function list commands
            'format_call_list',           # Used by call list commands
            'format_call_details',        # Used by get call commands
            'format_rule_details',        # Used by getRule
            'format_fragment_details',    # Used by getFragment
            'format_behavior_override_list',  # Used by listBehaviorOverrides
            'format_reference_code_list',     # Used by listReferenceCodes
            'format_system_parameter_list',   # Used by listSystemParameters
            'format_config_section_details',  # Used by getConfigSection
            'format_threshold_list',          # Used by threshold commands
            'format_generic_plan_list',       # Used by listGenericPlans
            'print_with_paging',              # Used by all enhanced commands for paging
            'set_paging_enabled',             # Used for paging control
        ]

        missing_methods = []
        for method_name in required_methods:
            if not hasattr(formatter, method_name):
                missing_methods.append(method_name)
            elif not callable(getattr(formatter, method_name)):
                missing_methods.append(f"{method_name} (not callable)")

        if missing_methods:
            pytest.fail(f"Missing formatter methods: {missing_methods}")


class TestCommandIntegration:
    """Test actual command execution to catch integration issues."""

    def setup_method(self):
        """Set up with mocked config manager but real formatter."""
        from _config_core import ConfigurationManager

        mock_config_manager = Mock()
        real_formatter = ConfigDisplayFormatter()

        self.config_tool = ConfigToolShell(mock_config_manager, real_formatter, hist_disable=True)

        # Set up mock returns
        mock_config_manager.get_record_list.return_value = []
        self.config_tool.config_manager.get_record_list.return_value = []
        self.config_tool.config_manager.get_record.return_value = []
        self.config_tool.config_manager.apply_filter.return_value = []

    def test_listRules_doesnt_crash(self):
        """Test the exact command that was failing."""
        try:
            # This should NOT raise AttributeError about missing format_rule_list
            self.config_tool.do_listRules("")
        except AttributeError as e:
            if "format_rule_list" in str(e):
                pytest.fail(f"Missing formatter method: {e}")
            else:
                raise  # Re-raise if it's a different AttributeError

    def test_all_enhanced_list_commands_dont_crash(self):
        """Test all enhanced list commands to catch missing formatter methods."""
        commands_to_test = [
            ('do_listRules', ''),
            ('do_listFragments', ''),
            ('do_listStandardizeFunctions', ''),
            ('do_listComparisonFunctions', ''),
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
        ]

        failed_commands = []
        for command_method, args in commands_to_test:
            try:
                if hasattr(self.config_tool, command_method):
                    method = getattr(self.config_tool, command_method)
                    method(args)
                else:
                    failed_commands.append(f"{command_method} (method missing)")
            except AttributeError as e:
                if "format_" in str(e):
                    failed_commands.append(f"{command_method}: {e}")
                # Ignore other AttributeErrors (like missing config methods)
            except Exception:
                # Ignore other exceptions - we're only testing for missing formatter methods
                pass

        if failed_commands:
            pytest.fail(f"Commands with missing formatter methods: {failed_commands}")

    def test_enhanced_get_commands_dont_crash(self):
        """Test enhanced get commands."""
        # Mock to return some data for get commands
        self.config_tool.config_manager.get_record.return_value = [{'ID': 1, 'CODE': 'TEST'}]

        get_commands = [
            ('do_getRule', 'TEST'),
            ('do_getFragment', 'TEST'),
            ('do_getStandardizeCall', '1'),
            ('do_getComparisonCall', '1'),
            ('do_getExpressionCall', '1'),
            ('do_getDistinctCall', '1'),
        ]

        failed_commands = []
        for command_method, args in get_commands:
            try:
                if hasattr(self.config_tool, command_method):
                    method = getattr(self.config_tool, command_method)
                    method(args)
            except AttributeError as e:
                if "format_" in str(e):
                    failed_commands.append(f"{command_method}: {e}")
            except Exception:
                # Ignore other exceptions
                pass

        if failed_commands:
            pytest.fail(f"Get commands with missing formatter methods: {failed_commands}")


class TestOutputFormatSupport:
    """Test that enhanced commands actually support multiple output formats."""

    def setup_method(self):
        mock_config_manager = Mock()
        real_formatter = ConfigDisplayFormatter()

        self.config_tool = ConfigToolShell(mock_config_manager, real_formatter, hist_disable=True)

        # Set up mock returns
        mock_config_manager.get_record_list.return_value = []
        mock_config_manager.apply_filter.return_value = []

    def test_format_parsing_works(self):
        """Test that format parsing doesn't crash."""
        test_commands = [
            "table",
            "json",
            "jsonl",
            "filter_expression table",
            "filter_expression json",
            "filter_expression jsonl"
        ]

        for arg in test_commands:
            try:
                # Test format parsing doesn't crash
                cleaned = self.config_tool.check_arg_for_output_format("list", arg)
                assert isinstance(cleaned, str)
            except Exception as e:
                pytest.fail(f"Format parsing failed for '{arg}': {e}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])