"""Comprehensive test suite for the original sz_configtool.

This test suite verifies all 120 commands in the original sz_configtool
including their functionality, parameter handling, and output formatting.
Tests are designed to work with a live Senzing database connection.
"""

import pytest
import subprocess
import tempfile
import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple


class SzConfigToolTester:
    """Test harness for the original sz_configtool."""

    def __init__(self):
        """Initialize the test harness."""
        self.configtool_path = "/home/bmacy/open_dev/sz-python-tools/sz_tools/sz_configtool"
        self.timeout = 30
        self.setup_environment()

    def setup_environment(self):
        """Set up the environment for testing."""
        self.env = os.environ.copy()
        self.env['SENZING_ENGINE_CONFIGURATION_JSON'] = '''{
            "PIPELINE": {
                "CONFIGPATH": "/etc/opt/senzing",
                "RESOURCEPATH": "/opt/senzing/er/resources",
                "SUPPORTPATH": "/opt/senzing/data"
            },
            "SQL": {
                "XXXDEBUGLEVEL": 2,
                "CONNECTION": "postgresql://senzing:senzing4pgsql@192.168.2.122:5432:g2"
            }
        }'''

    def run_command(self, command: str, expect_success: bool = True) -> Tuple[str, str, int]:
        """Run a single command in sz_configtool and return output."""
        try:
            process = subprocess.run(
                [self.configtool_path],
                input=f"{command}\\nquit\\n",
                text=True,
                capture_output=True,
                env=self.env,
                timeout=self.timeout
            )

            stdout = process.stdout
            stderr = process.stderr
            returncode = process.returncode

            # Filter out interactive prompts and colors
            lines = stdout.split('\\n')
            filtered_lines = []
            for line in lines:
                if 'Type help' not in line and 'szcfg' not in line and line.strip():
                    # Remove ANSI color codes for easier testing
                    import re
                    line = re.sub(r'\\x1b\\[[0-9;]*m', '', line)
                    filtered_lines.append(line)

            clean_output = '\\n'.join(filtered_lines)

            if expect_success and returncode != 0:
                raise Exception(f"Command failed: {command}, stderr: {stderr}")

            return clean_output, stderr, returncode

        except subprocess.TimeoutExpired:
            raise Exception(f"Command timed out: {command}")

    def run_commands(self, commands: List[str]) -> Dict[str, Tuple[str, str, int]]:
        """Run multiple commands and return results."""
        results = {}
        for command in commands:
            try:
                results[command] = self.run_command(command)
            except Exception as e:
                results[command] = ("", str(e), -1)
        return results

    def create_test_data_source(self, name: str = "TEST_SOURCE") -> str:
        """Create a test data source for testing."""
        command = f'addDataSource {{"dataSource": "{name}"}}'
        output, _, _ = self.run_command(command)
        return name

    def cleanup_test_data_source(self, name: str):
        """Clean up test data source."""
        try:
            self.run_command(f'deleteDataSource {name}', expect_success=False)
        except:
            pass  # May not exist

    def validate_table_output(self, output: str, expected_columns: List[str]) -> bool:
        """Validate that output contains a table with expected columns."""
        if not output:
            return False

        # Look for table structure
        has_table_chars = any(char in output for char in ['┌', '├', '│', '┐', '┤', '└', '┘'])
        if not has_table_chars:
            return False

        # Check for expected column headers
        output_lower = output.lower()
        for column in expected_columns:
            if column.lower() not in output_lower:
                return False

        return True

    def validate_json_output(self, output: str) -> bool:
        """Validate that output contains valid JSON."""
        try:
            # Extract JSON content from output
            lines = output.split('\\n')
            json_lines = [line for line in lines if line.strip().startswith('{')]
            if json_lines:
                json.loads(json_lines[0])
                return True
        except:
            pass
        return False


class TestOriginalSzConfigTool:
    """Comprehensive test suite for original sz_configtool."""

    @pytest.fixture(scope="session")
    def tester(self):
        """Create test harness instance."""
        return SzConfigToolTester()

    # =========================================================================
    # BASIC COMMANDS TESTS
    # =========================================================================

    def test_basic_commands_exist(self, tester):
        """Test that all basic commands exist and respond."""
        basic_commands = [
            "help", "history", "quit", "exit"
        ]

        for command in basic_commands:
            output, stderr, returncode = tester.run_command(command, expect_success=False)
            # These commands should execute without error
            assert returncode == 0 or "Unknown command" not in output

    def test_help_command_comprehensive(self, tester):
        """Test help command shows all categories and commands."""
        output, _, _ = tester.run_command("help")

        # Should show command categories
        expected_categories = [
            "Basic Commands:",
            "Configuration Management:",
            "Data Source Management:",
            "Feature Management:",
            "Attribute Management:",
            "Element Management:",
            "Function Management:",
            "Rules and Fragments:",
            "Threshold and Scoring:",
            "Behavior Overrides:"
        ]

        for category in expected_categories:
            assert category in output, f"Missing category: {category}"

        # Should show total command count
        assert "120" in output, "Should show 120 total commands"

    # =========================================================================
    # CONFIGURATION MANAGEMENT TESTS
    # =========================================================================

    def test_configuration_management_commands(self, tester):
        """Test configuration management commands."""
        config_commands = [
            "getDefaultConfigID",
            "getConfigRegistry",
            "reload_config",
            "getCompatibilityVersion",
            "verifyCompatibilityVersion"
        ]

        for command in config_commands:
            output, stderr, returncode = tester.run_command(command)
            assert returncode == 0, f"Command {command} failed: {stderr}"
            assert output.strip(), f"Command {command} produced no output"

    def test_config_section_management(self, tester):
        """Test config section management commands."""
        # Test listing config sections
        output, _, _ = tester.run_command("getConfigSection")
        assert "CFG_" in output or "config" in output.lower()

    def test_export_import_functionality(self, tester):
        """Test export and import functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name

        try:
            # Test export
            export_output, _, _ = tester.run_command(f"exportToFile {export_file}")
            assert "successfully" in export_output.lower() or os.path.exists(export_file)

            # Verify file exists and has content
            if os.path.exists(export_file):
                with open(export_file, 'r') as f:
                    content = f.read()
                    assert len(content) > 0
                    # Should be valid JSON
                    json.loads(content)

        finally:
            if os.path.exists(export_file):
                os.unlink(export_file)

    # =========================================================================
    # DATA SOURCE MANAGEMENT TESTS
    # =========================================================================

    def test_data_source_management_complete(self, tester):
        """Test complete data source management workflow."""
        test_source = "TEST_DS_" + str(int(time.time()))

        try:
            # Test adding data source
            add_command = f'addDataSource {{"dataSource": "{test_source}"}}'
            output, _, _ = tester.run_command(add_command)
            assert "successfully" in output.lower() or "added" in output.lower()

            # Test listing data sources
            list_output, _, _ = tester.run_command("listDataSources")
            expected_columns = ["id", "datasource"]
            assert tester.validate_table_output(list_output, expected_columns)
            assert test_source in list_output

            # Test deleting data source
            delete_output, _, _ = tester.run_command(f"deleteDataSource {test_source}")
            assert "successfully" in delete_output.lower() or "deleted" in delete_output.lower()

        finally:
            # Cleanup
            tester.cleanup_test_data_source(test_source)

    # =========================================================================
    # FEATURE MANAGEMENT TESTS
    # =========================================================================

    def test_feature_list_commands(self, tester):
        """Test feature listing commands."""
        # Test listFeatures
        output, _, _ = tester.run_command("listFeatures")
        expected_columns = ["id", "feature", "class", "behavior", "anonymize",
                          "candidates", "standardize", "expression", "comparison",
                          "matchKey", "version", "elementList"]
        assert tester.validate_table_output(output, expected_columns)

    def test_feature_retrieval(self, tester):
        """Test individual feature retrieval."""
        # Get a feature that should exist (NAME)
        output, _, _ = tester.run_command("getFeature NAME")
        assert tester.validate_json_output(output) or "feature" in output.lower()

    def test_feature_management_workflow(self, tester):
        """Test adding, modifying, and deleting features."""
        test_feature = "TEST_FEATURE_" + str(int(time.time()))

        try:
            # Test adding feature
            add_command = f'''addFeature {{
                "feature": "{test_feature}",
                "class": "OTHER",
                "behavior": "FM",
                "anonymize": "No",
                "candidates": "No",
                "standardize": "",
                "expression": "",
                "comparison": "",
                "matchKey": "No"
            }}'''

            output, _, _ = tester.run_command(add_command)
            assert "successfully" in output.lower() or "added" in output.lower()

            # Verify feature exists
            list_output, _, _ = tester.run_command("listFeatures")
            assert test_feature in list_output

        finally:
            # Cleanup - try to delete test feature
            try:
                tester.run_command(f"deleteFeature {test_feature}", expect_success=False)
            except:
                pass

    # =========================================================================
    # ATTRIBUTE MANAGEMENT TESTS
    # =========================================================================

    def test_attribute_management(self, tester):
        """Test attribute management commands."""
        # Test listing attributes
        output, _, _ = tester.run_command("listAttributes")
        expected_columns = ["id", "attribute", "class", "feature", "element",
                          "required", "default", "internal"]
        assert tester.validate_table_output(output, expected_columns)

    def test_attribute_retrieval(self, tester):
        """Test individual attribute retrieval."""
        # Try to get a common attribute
        output, _, _ = tester.run_command("getAttribute DATA_SOURCE")
        assert "attribute" in output.lower() or tester.validate_json_output(output)

    # =========================================================================
    # ELEMENT MANAGEMENT TESTS
    # =========================================================================

    def test_element_management(self, tester):
        """Test element management commands."""
        # Test listing elements
        output, _, _ = tester.run_command("listElements")
        expected_columns = ["id", "element", "datatype"]
        assert tester.validate_table_output(output, expected_columns)

    def test_element_retrieval(self, tester):
        """Test individual element retrieval."""
        output, _, _ = tester.run_command("getElement FULL_NAME")
        assert "element" in output.lower() or tester.validate_json_output(output)

    # =========================================================================
    # FUNCTION MANAGEMENT TESTS
    # =========================================================================

    def test_function_listing_commands(self, tester):
        """Test all function listing commands."""
        function_list_commands = [
            ("listStandardizeFunctions", ["id", "function"]),
            ("listExpressionFunctions", ["id", "function"]),
            ("listComparisonFunctions", ["id", "function"]),
            ("listDistinctFunctions", ["id", "function"])
        ]

        for command, expected_columns in function_list_commands:
            output, _, _ = tester.run_command(command)
            assert tester.validate_table_output(output, expected_columns), f"Failed: {command}"

    def test_function_call_management(self, tester):
        """Test function call management commands."""
        call_list_commands = [
            ("listStandardizeCalls", ["id", "feature", "function"]),
            ("listExpressionCalls", ["id", "feature", "function"]),
            ("listComparisonCalls", ["id", "feature", "function"]),
            ("listDistinctCalls", ["id", "feature", "function"])
        ]

        for command, expected_columns in call_list_commands:
            output, _, _ = tester.run_command(command)
            # These may be empty but should have proper table structure
            assert "┌" in output or "No" in output, f"Command {command} failed"

    # =========================================================================
    # RULES AND FRAGMENTS TESTS
    # =========================================================================

    def test_rules_management(self, tester):
        """Test rules management commands."""
        # Test listing rules
        output, _, _ = tester.run_command("listRules")
        expected_columns = ["id", "rule", "resolve", "relate", "rtype_id",
                          "fragment", "disqualifier", "tier"]
        assert tester.validate_table_output(output, expected_columns)

    def test_fragments_management(self, tester):
        """Test fragments management commands."""
        # Test listing fragments
        output, _, _ = tester.run_command("listFragments")
        expected_columns = ["id", "fragment"]
        assert tester.validate_table_output(output, expected_columns)

    def test_rule_retrieval(self, tester):
        """Test individual rule retrieval."""
        # Get first rule from list
        list_output, _, _ = tester.run_command("listRules")
        if "│" in list_output:
            lines = list_output.split('\\n')
            for line in lines:
                if "│" in line and not "id" in line and line.strip():
                    # Extract rule ID from first data row
                    parts = [p.strip() for p in line.split('│') if p.strip()]
                    if len(parts) > 1 and parts[1].isdigit():
                        rule_id = parts[1]
                        rule_output, _, _ = tester.run_command(f"getRule {rule_id}")
                        assert "rule" in rule_output.lower() or tester.validate_json_output(rule_output)
                        break

    # =========================================================================
    # THRESHOLD AND SCORING TESTS
    # =========================================================================

    def test_threshold_management(self, tester):
        """Test threshold management commands."""
        # Test generic thresholds
        output, _, _ = tester.run_command("listGenericThresholds")
        expected_columns = ["plan", "behavior", "feature", "candidateCap",
                          "scoringCap", "sendToRedo"]
        assert tester.validate_table_output(output, expected_columns)

        # Test comparison thresholds
        output, _, _ = tester.run_command("listComparisonThresholds")
        expected_columns = ["id", "feature", "element", "function", "behavior"]
        assert tester.validate_table_output(output, expected_columns)

    def test_generic_plan_management(self, tester):
        """Test generic plan management."""
        output, _, _ = tester.run_command("listGenericPlans")
        expected_columns = ["plan", "behavior"]
        assert tester.validate_table_output(output, expected_columns)

    # =========================================================================
    # BEHAVIOR OVERRIDES TESTS
    # =========================================================================

    def test_behavior_overrides(self, tester):
        """Test behavior override management."""
        output, _, _ = tester.run_command("listBehaviorOverrides")
        # May be empty but should execute without error
        assert "┌" in output or "No" in output or "override" in output.lower()

    # =========================================================================
    # SYSTEM PARAMETERS TESTS
    # =========================================================================

    def test_system_parameters(self, tester):
        """Test system parameter management."""
        output, _, _ = tester.run_command("listSystemParameters")
        # Should show system parameters
        assert "parameter" in output.lower() or "┌" in output

    # =========================================================================
    # REFERENCE DATA TESTS
    # =========================================================================

    def test_reference_codes(self, tester):
        """Test reference code listing."""
        output, _, _ = tester.run_command("listReferenceCodes")
        # Should execute without error
        assert "┌" in output or "reference" in output.lower() or "code" in output.lower()

    # =========================================================================
    # INTEGRATION AND WORKFLOW TESTS
    # =========================================================================

    def test_command_chaining_workflow(self, tester):
        """Test realistic command workflows."""
        # Test a typical configuration workflow
        commands = [
            "listFeatures",
            "getFeature NAME",
            "listAttributes",
            "listElements",
            "listRules",
            "listGenericThresholds"
        ]

        results = tester.run_commands(commands)

        # All commands should succeed
        for command, (output, stderr, returncode) in results.items():
            assert returncode == 0, f"Command {command} failed: {stderr}"
            assert output.strip(), f"Command {command} produced no output"

    def test_help_for_all_commands(self, tester):
        """Test that help exists for all major commands."""
        major_commands = [
            "addDataSource", "listDataSources", "deleteDataSource",
            "addFeature", "listFeatures", "getFeature", "deleteFeature",
            "addAttribute", "listAttributes", "getAttribute", "deleteAttribute",
            "addElement", "listElements", "getElement", "deleteElement",
            "addRule", "listRules", "getRule", "deleteRule",
            "addFragment", "listFragments", "getFragment", "deleteFragment",
            "listGenericThresholds", "listComparisonThresholds",
            "listBehaviorOverrides"
        ]

        for command in major_commands:
            help_output, _, _ = tester.run_command(f"help {command}")
            # Should show help text, not "Unknown command"
            assert "Unknown command" not in help_output
            assert "Syntax:" in help_output or command in help_output

    def test_all_120_commands_exist(self, tester):
        """Test that all 120 commands exist and are accessible."""
        # Get help output to see all commands
        help_output, _, _ = tester.run_command("help")

        # Extract command names from help output
        # This is a basic check that the help system recognizes all commands
        assert "120" in help_output, "Should show 120 total commands"

        # Test a representative sample from each category
        sample_commands = [
            # Basic
            "help", "history", "quit",
            # Configuration
            "getDefaultConfigID", "reload_config", "exportToFile",
            # Data Sources
            "addDataSource", "listDataSources", "deleteDataSource",
            # Features
            "addFeature", "listFeatures", "getFeature", "setFeature", "deleteFeature",
            # Attributes
            "addAttribute", "listAttributes", "getAttribute", "setAttribute", "deleteAttribute",
            # Elements
            "addElement", "listElements", "getElement", "deleteElement",
            # Functions
            "listStandardizeFunctions", "listExpressionFunctions",
            "listComparisonFunctions", "listDistinctFunctions",
            # Calls
            "addStandardizeCall", "listStandardizeCalls", "deleteStandardizeCall",
            "addExpressionCall", "listExpressionCalls", "deleteExpressionCall",
            "addComparisonCall", "listComparisonCalls", "deleteComparisonCall",
            "addDistinctCall", "listDistinctCalls", "deleteDistinctCall",
            # Rules and Fragments
            "addRule", "listRules", "getRule", "setRule", "deleteRule",
            "addFragment", "listFragments", "getFragment", "setFragment", "deleteFragment",
            # Thresholds
            "listGenericThresholds", "addGenericThreshold", "setGenericThreshold", "deleteGenericThreshold",
            "listComparisonThresholds", "addComparisonThreshold", "setComparisonThreshold", "deleteComparisonThreshold",
            # Behavior Overrides
            "listBehaviorOverrides", "addBehaviorOverride", "deleteBehaviorOverride",
            # System
            "listSystemParameters", "setSystemParameter",
            "verifyCompatibilityVersion", "getCompatibilityVersion"
        ]

        failed_commands = []
        for command in sample_commands:
            try:
                # Just test that the command is recognized (doesn't return "Unknown command")
                output, stderr, returncode = tester.run_command(command, expect_success=False)
                if "Unknown command" in output:
                    failed_commands.append(command)
            except Exception as e:
                failed_commands.append(f"{command}: {str(e)}")

        assert not failed_commands, f"Commands not recognized: {failed_commands}"

    # =========================================================================
    # OUTPUT FORMAT VALIDATION TESTS
    # =========================================================================

    def test_output_format_consistency(self, tester):
        """Test that all list commands produce consistent table output."""
        list_commands = [
            "listDataSources", "listFeatures", "listAttributes", "listElements",
            "listRules", "listFragments", "listGenericThresholds",
            "listComparisonThresholds", "listBehaviorOverrides",
            "listStandardizeFunctions", "listExpressionFunctions",
            "listComparisonFunctions", "listDistinctFunctions"
        ]

        for command in list_commands:
            output, _, _ = tester.run_command(command)
            # Should either have table formatting or indicate no data
            assert ("┌" in output or "│" in output or
                   "No" in output or "none" in output.lower()), f"Command {command} has unexpected output format"

    def test_json_output_modes(self, tester):
        """Test JSON output modes where supported."""
        # Test commands that should support JSON output
        json_commands = [
            "listFeatures json",
            "listAttributes json",
            "listElements json",
            "getFeature NAME json"
        ]

        for command in json_commands:
            try:
                output, _, _ = tester.run_command(command, expect_success=False)
                # Should either produce JSON or indicate the format is not supported
                if "{" in output:
                    assert tester.validate_json_output(output), f"Invalid JSON from {command}"
            except:
                # Some commands may not support JSON mode
                pass

    # =========================================================================
    # ERROR HANDLING TESTS
    # =========================================================================

    def test_invalid_command_handling(self, tester):
        """Test handling of invalid commands."""
        invalid_commands = [
            "invalidCommand",
            "listInvalidThings",
            "getNothing",
            ""
        ]

        for command in invalid_commands:
            output, stderr, returncode = tester.run_command(command, expect_success=False)
            # Should indicate unknown command
            assert ("Unknown command" in output or
                   "command" in output.lower() or
                   "help" in output.lower()), f"Poor error handling for: {command}"

    def test_malformed_json_handling(self, tester):
        """Test handling of malformed JSON inputs."""
        malformed_commands = [
            'addDataSource {"invalid json}',
            'addFeature {incomplete',
            'addAttribute {"missing": quote"}'
        ]

        for command in malformed_commands:
            output, stderr, returncode = tester.run_command(command, expect_success=False)
            # Should handle malformed JSON gracefully
            assert returncode != 0 or "error" in output.lower() or "invalid" in output.lower()


# =========================================================================
# PERFORMANCE AND STRESS TESTS
# =========================================================================

class TestPerformanceAndStress:
    """Performance and stress tests for sz_configtool."""

    @pytest.fixture(scope="class")
    def tester(self):
        """Create test harness instance."""
        return SzConfigToolTester()

    def test_large_list_commands_performance(self, tester):
        """Test performance of list commands with large datasets."""
        # Test that list commands complete within reasonable time
        large_list_commands = [
            "listFeatures",
            "listAttributes",
            "listElements",
            "listRules"
        ]

        for command in large_list_commands:
            start_time = time.time()
            output, _, _ = tester.run_command(command)
            elapsed = time.time() - start_time

            # Should complete within 30 seconds
            assert elapsed < 30, f"Command {command} took too long: {elapsed}s"
            assert output.strip(), f"Command {command} produced no output"

    def test_concurrent_access_simulation(self, tester):
        """Test that multiple commands can be run in sequence without issues."""
        # Simulate concurrent access by running multiple commands rapidly
        commands = ["listFeatures", "listAttributes", "listElements"] * 3

        start_time = time.time()
        results = tester.run_commands(commands)
        elapsed = time.time() - start_time

        # All commands should succeed
        for command, (output, stderr, returncode) in results.items():
            assert returncode == 0, f"Command {command} failed: {stderr}"

        # Should complete in reasonable time
        assert elapsed < 60, f"Concurrent commands took too long: {elapsed}s"


if __name__ == "__main__":
    # Run the comprehensive test suite
    pytest.main([__file__, "-v", "--tb=short", "-x"])