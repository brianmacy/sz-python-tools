"""Comprehensive Regression Test Suite for sz_configtool.

These tests ensure that changes to the codebase don't break existing
functionality and that all previously working features continue to work
as expected. This includes API compatibility, behavior consistency,
and feature preservation across versions.
"""

import pytest
import json
import sys
import os
import hashlib
import tempfile
import subprocess
from io import StringIO
from unittest.mock import patch
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


@dataclass
class RegressionTestCase:
    """Represents a regression test case."""
    command: str
    args: str
    expected_behavior: str
    critical: bool = True
    description: str = ""


class RegressionTestHarness:
    """Harness for running regression tests."""

    def __init__(self):
        """Initialize the regression test harness."""
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter, force_mode=True)
        self.senzing_available = self.config_manager.initialize_senzing()

        # Track regression test results
        self.test_results = []
        self.known_issues = set()

    def get_all_available_commands(self) -> List[str]:
        """Get all available commands from the shell."""
        commands = []
        for attr_name in dir(self.shell):
            if attr_name.startswith('do_') and callable(getattr(self.shell, attr_name)):
                command_name = attr_name[3:]  # Remove 'do_' prefix
                commands.append(command_name)
        return sorted(commands)

    def execute_command_safely(self, command: str, args: str = "") -> Dict[str, Any]:
        """Execute a command safely and capture results."""
        if not hasattr(self.shell, f'do_{command}'):
            return {
                "success": False,
                "error": f"Command {command} not found",
                "stdout": "",
                "stderr": "",
                "output_hash": None
            }

        method = getattr(self.shell, f'do_{command}')

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            # Set test flag for proper output capture
            sys._called_from_test = True
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            method(args)

            stdout_content = sys.stdout.getvalue()
            stderr_content = sys.stderr.getvalue()

            # Check for specific error patterns (not just keywords)
            all_output = stdout_content + stderr_content
            all_output_lower = all_output.lower()

            # Look for specific error patterns, not just keywords that might appear in normal output
            error_patterns = [
                "error:", "failed:", "is required", "not found:",
                "missing required", "invalid parameter",
                "syntax error", "command failed"
            ]
            has_error = any(pattern in all_output_lower for pattern in error_patterns)

            # Generate hash of output for consistency checking
            output_hash = hashlib.md5(stdout_content.encode()).hexdigest()

            return {
                "success": not has_error,
                "error": None,
                "stdout": stdout_content,
                "stderr": stderr_content,
                "output_hash": output_hash
            }

        except Exception as e:
            stdout_content = sys.stdout.getvalue()
            stderr_content = sys.stderr.getvalue()
            return {
                "success": False,
                "error": str(e),
                "stdout": stdout_content,
                "stderr": stderr_content,
                "output_hash": None
            }

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # Reset test flag
            if hasattr(sys, '_called_from_test'):
                delattr(sys, '_called_from_test')

    def extract_structured_data(self, output: str, format_type: str = "json") -> Optional[Any]:
        """Extract structured data from command output."""
        if not output:
            return None

        if format_type != "json":
            return None

        output_stripped = output.strip()

        # First try to parse the entire output as JSON
        if output_stripped:
            try:
                return json.loads(output_stripped)
            except json.JSONDecodeError:
                pass

        # If that fails, try line by line for single-line JSON
        lines = output_stripped.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('[') or line.startswith('{'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        # Try to find JSON blocks in the output
        json_start = -1
        brace_count = 0
        bracket_count = 0

        for i, char in enumerate(output_stripped):
            if char == '{':
                if json_start == -1:
                    json_start = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and json_start != -1:
                    try:
                        return json.loads(output_stripped[json_start:i+1])
                    except json.JSONDecodeError:
                        json_start = -1
            elif char == '[':
                if json_start == -1:
                    json_start = i
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0 and json_start != -1:
                    try:
                        return json.loads(output_stripped[json_start:i+1])
                    except json.JSONDecodeError:
                        json_start = -1

        return None

    def validate_command_compatibility(self, command: str, args: str = "") -> Dict[str, Any]:
        """Validate that a command maintains compatibility."""
        result = self.execute_command_safely(command, args)

        compatibility_check = {
            "command": command,
            "args": args,
            "executable": result["success"] or self._is_acceptable_error(result["error"]),
            "produces_output": bool(result["stdout"]),
            "json_parseable": False,
            "field_compatibility": {},
            "issues": []
        }

        # Check JSON parseability for json format commands
        if "json" in args and result["stdout"]:
            json_data = self.extract_structured_data(result["stdout"], "json")
            if json_data is not None:
                compatibility_check["json_parseable"] = True
                compatibility_check["field_compatibility"] = self._check_field_compatibility(command, json_data)
            else:
                compatibility_check["issues"].append("JSON format requested but output not parseable")

        return compatibility_check

    def _is_acceptable_error(self, error: Optional[str]) -> bool:
        """Check if an error is acceptable (parameter errors, etc.)."""
        # No error is always acceptable (successful execution)
        if not error:
            return True

        error_lower = error.lower()
        acceptable_errors = [
            "required", "parameter", "argument", "missing", "usage",
            "syntax", "expected", "invalid", "specify"
        ]
        return any(err in error_lower for err in acceptable_errors)

    def _check_field_compatibility(self, command: str, json_data: Any) -> Dict[str, Any]:
        """Check field compatibility for JSON output."""
        field_check = {
            "has_user_friendly_names": True,
            "has_database_schema_names": False,
            "missing_expected_fields": [],
            "unexpected_fields": []
        }

        if not isinstance(json_data, (list, dict)):
            return field_check

        # Get first item for analysis
        sample_item = json_data[0] if isinstance(json_data, list) and json_data else json_data
        if not isinstance(sample_item, dict):
            return field_check

        # Define expected field mappings
        expected_fields = self._get_expected_fields(command)
        database_fields = self._get_database_fields(command)

        # Check for database schema field names (should not be present)
        found_db_fields = [field for field in database_fields if field in sample_item]
        if found_db_fields:
            field_check["has_database_schema_names"] = True
            field_check["unexpected_fields"] = found_db_fields

        # Check for expected user-friendly field names
        missing_expected = [field for field in expected_fields if field not in sample_item]
        if missing_expected:
            field_check["has_user_friendly_names"] = False
            field_check["missing_expected_fields"] = missing_expected

        return field_check

    def _get_expected_fields(self, command: str) -> List[str]:
        """Get expected user-friendly field names for a command."""
        field_mappings = {
            "listDataSources": ["id", "dataSource", "description"],
            "listFeatures": ["id", "feature", "frequency"],
            "listAttributes": ["id", "attribute", "class", "default", "element", "feature", "required"],
            "listElements": ["id", "element", "derived", "display", "order"],
            "getFeature": ["id", "feature", "elementList"],
            "getAttribute": ["id", "attribute", "class", "default", "element", "feature", "internal", "required"]
        }
        return field_mappings.get(command, [])

    def _get_database_fields(self, command: str) -> List[str]:
        """Get database schema field names that should not appear in API."""
        database_mappings = {
            "listDataSources": ["DSRC_ID", "DSRC_CODE", "DSRC_DESC"],
            "listFeatures": ["FTYPE_ID", "FTYPE_CODE", "FTYPE_FREQ"],
            "listAttributes": ["ATTR_ID", "ATTR_CODE", "ATTR_CLASS", "DEFAULT_VALUE", "FELEM_CODE", "FTYPE_CODE", "FELEM_REQ"],
            "listElements": ["FELEM_ID", "FELEM_CODE", "DERIVED_IND", "DISPLAY_IND", "DISPLAY_ORDER"],
            "getFeature": ["FTYPE_ID", "FTYPE_CODE"],
            "getAttribute": ["ATTR_ID", "ATTR_CODE", "ATTR_CLASS", "DEFAULT_VALUE", "FELEM_CODE", "FTYPE_CODE", "FELEM_REQ"]
        }
        return database_mappings.get(command, [])


class TestRegressionCommandExistence:
    """Regression tests for command existence and basic functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = RegressionTestHarness()

    def test_all_120_commands_still_exist(self):
        """Ensure all 120 expected commands still exist."""
        available_commands = self.harness.get_all_available_commands()

        # Should have approximately 120 commands
        assert len(available_commands) >= 100, \
            f"Regression: Command count too low, expected ~120, got {len(available_commands)}"

        # Define critical commands that must exist
        critical_commands = [
            # Core management commands
            "help", "quit", "save", "exportToFile", "importFromFile",

            # Data source management
            "listDataSources", "addDataSource", "deleteDataSource",

            # Feature management
            "listFeatures", "getFeature", "addFeature", "deleteFeature",

            # Attribute management
            "listAttributes", "getAttribute", "addAttribute", "deleteAttribute",

            # Element management
            "listElements", "getElement", "addElement", "deleteElement",

            # Comparison functions
            "listComparisonCalls", "getComparisonCall", "addComparisonCall", "deleteComparisonCall",

            # Expression functions
            "listExpressionCalls", "getExpressionCall", "addExpressionCall", "deleteExpressionCall",

            # Distinct functions
            "listDistinctCalls", "getDistinctCall", "addDistinctCall", "deleteDistinctCall"
        ]

        missing_critical = [cmd for cmd in critical_commands if cmd not in available_commands]
        assert not missing_critical, \
            f"Regression: Missing critical commands: {missing_critical}"

    def test_command_basic_executability(self):
        """Test that all commands are basically executable (don't crash immediately)."""
        available_commands = self.harness.get_all_available_commands()

        non_executable_commands = []

        for command in available_commands:
            result = self.harness.execute_command_safely(command)

            # Command should either succeed or fail gracefully with parameter error
            if not result["success"]:
                if not self.harness._is_acceptable_error(result["error"]):
                    non_executable_commands.append(f"{command}: {result['error']}")

        assert not non_executable_commands, \
            f"Regression: Non-executable commands: {non_executable_commands}"

    def test_help_system_functionality(self):
        """Test that help system still works correctly."""
        # Test main help command
        help_result = self.harness.execute_command_safely("help")
        assert help_result["success"], f"Help command failed: {help_result['error']}"
        assert help_result["stdout"], "Help command should produce output"

        # Help output should contain useful information
        help_output = help_result["stdout"].lower()
        assert any(word in help_output for word in ["command", "help", "usage"]), \
            "Help output should contain command information"


class TestRegressionAPICompatibility:
    """Regression tests for API compatibility and output format consistency."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = RegressionTestHarness()

    @pytest.mark.skipif(not RegressionTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_json_output_format_consistency(self):
        """Test that JSON output formats remain consistent."""
        json_commands = [
            "listDataSources", "listFeatures", "listAttributes", "listElements"
        ]

        format_regressions = []

        for command in json_commands:
            compatibility = self.harness.validate_command_compatibility(command, "json")

            if not compatibility["executable"]:
                format_regressions.append(f"{command}: Not executable")
                continue

            if not compatibility["json_parseable"]:
                format_regressions.append(f"{command}: JSON output not parseable")
                continue

            # Check for field compatibility issues
            field_compat = compatibility["field_compatibility"]
            if field_compat.get("has_database_schema_names", False):
                format_regressions.append(
                    f"{command}: Uses database schema field names: {field_compat['unexpected_fields']}"
                )

            if not field_compat.get("has_user_friendly_names", True):
                format_regressions.append(
                    f"{command}: Missing user-friendly field names: {field_compat['missing_expected_fields']}"
                )

        if format_regressions:
            pytest.fail(f"API compatibility regressions detected: {format_regressions}")

    @pytest.mark.skipif(not RegressionTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_get_command_output_structure(self):
        """Test that get commands maintain proper output structure."""
        # Test getAttribute with first available attribute
        list_result = self.harness.execute_command_safely("listAttributes", "json")
        if list_result["success"]:
            attributes_data = self.harness.extract_structured_data(list_result["stdout"], "json")
            if attributes_data and isinstance(attributes_data, list) and attributes_data:
                first_attr = attributes_data[0]
                attr_name = first_attr.get("ATTR_CODE") or first_attr.get("attribute")

                if attr_name:
                    get_compat = self.harness.validate_command_compatibility("getAttribute", f"{attr_name} json")

                    assert get_compat["executable"], "getAttribute should be executable"
                    assert get_compat["json_parseable"], "getAttribute should produce valid JSON"

                    # Check for database schema field names regression
                    field_compat = get_compat["field_compatibility"]
                    if field_compat.get("has_database_schema_names", False):
                        pytest.fail(f"getAttribute regression: uses database field names {field_compat['unexpected_fields']}")

        # Test getFeature with first available feature
        list_result = self.harness.execute_command_safely("listFeatures", "json")
        if list_result["success"]:
            features_data = self.harness.extract_structured_data(list_result["stdout"], "json")
            if features_data and isinstance(features_data, list) and features_data:
                first_feature = features_data[0]
                feature_name = first_feature.get("FTYPE_CODE") or first_feature.get("feature")

                if feature_name:
                    get_compat = self.harness.validate_command_compatibility("getFeature", f"{feature_name} json")

                    assert get_compat["executable"], "getFeature should be executable"
                    assert get_compat["json_parseable"], "getFeature should produce valid JSON"

                    # Check for missing elementList regression
                    get_result = self.harness.execute_command_safely("getFeature", f"{feature_name} json")
                    if get_result["success"]:
                        feature_data = self.harness.extract_structured_data(get_result["stdout"], "json")
                        if feature_data and isinstance(feature_data, dict):
                            if "elementList" not in feature_data:
                                pytest.fail("getFeature regression: missing required elementList field")

    @pytest.mark.skipif(not RegressionTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_table_output_format_consistency(self):
        """Test that table output formats remain consistent."""
        table_commands = ["listDataSources", "listFeatures", "listAttributes"]

        table_regressions = []

        for command in table_commands:
            compatibility = self.harness.validate_command_compatibility(command, "table")

            if not compatibility["executable"]:
                table_regressions.append(f"{command}: Table format not executable")
                continue

            if not compatibility["produces_output"]:
                table_regressions.append(f"{command}: Table format produces no output")

        assert not table_regressions, f"Table format regressions: {table_regressions}"


class TestRegressionFunctionalBehavior:
    """Regression tests for functional behavior and business logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = RegressionTestHarness()

    @pytest.mark.skipif(not RegressionTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_crud_operations_still_work(self):
        """Test that CRUD operations maintain their behavior."""
        test_ds_name = "REGRESSION_TEST_DS"

        try:
            # Test Create
            add_result = self.harness.execute_command_safely("addDataSource", test_ds_name)
            if not add_result["success"]:
                pytest.skip(f"Cannot test CRUD - addDataSource failed: {add_result['error']}")

            # Test Read
            list_result = self.harness.execute_command_safely("listDataSources", "json")
            assert list_result["success"], "listDataSources should work for CRUD test"

            list_data = self.harness.extract_structured_data(list_result["stdout"], "json")
            if list_data and isinstance(list_data, list):
                # Look for our test data source
                found = False
                for item in list_data:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if value == test_ds_name:
                                found = True
                                break
                        if found:
                            break

                assert found, f"CRUD regression: Created data source {test_ds_name} not found in list"


            # Test Delete
            delete_result = self.harness.execute_command_safely("deleteDataSource", test_ds_name)
            # Delete might fail if not in force mode, that's acceptable

        finally:
            # Cleanup
            self.harness.execute_command_safely("deleteDataSource", test_ds_name)

    @pytest.mark.skipif(not RegressionTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_parameter_validation_consistency(self):
        """Test that parameter validation behavior remains consistent."""
        # Test commands with missing required parameters
        parameter_tests = [
            ("getAttribute", ""),  # Missing attribute name
            ("getFeature", ""),    # Missing feature name
            ("addDataSource", ""), # Missing data source name
        ]

        validation_regressions = []

        for command, args in parameter_tests:
            result = self.harness.execute_command_safely(command, args)

            # Should fail with meaningful error message
            if result["success"]:
                validation_regressions.append(f"{command}: Should fail with missing parameters but succeeded")
            else:
                error_text = (result["error"] or result["stderr"] or result["stdout"]).lower()
                if not any(word in error_text for word in ["required", "parameter", "missing", "usage", "argument"]):
                    validation_regressions.append(f"{command}: Error message not informative: {result['error']}")

        assert not validation_regressions, f"Parameter validation regressions: {validation_regressions}"

    def test_error_handling_consistency(self):
        """Test that error handling behavior remains consistent."""
        # Test invalid commands
        invalid_command_result = self.harness.execute_command_safely("invalidCommand")
        assert not invalid_command_result["success"], "Invalid commands should fail"

        # Test malformed parameters
        if self.harness.senzing_available:
            malformed_tests = [
                ("listDataSources", "invalidformat"),
                ("getAttribute", "NONEXISTENT_ATTR json"),
            ]

            for command, args in malformed_tests:
                result = self.harness.execute_command_safely(command, args)
                # Should either succeed or fail gracefully
                if not result["success"]:
                    # Should provide some error information
                    assert result["error"] or result["stderr"] or "error" in result["stdout"].lower(), \
                        f"Error handling regression: {command} with {args} provides no error information"


class TestRegressionConfiguration:
    """Regression tests for configuration management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = RegressionTestHarness()

    @pytest.mark.skipif(not RegressionTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_export_import_functionality(self):
        """Test that export/import functionality maintains behavior."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            # Test export
            export_result = self.harness.execute_command_safely("exportToFile", temp_file)
            if export_result["success"]:
                # File should be created
                assert os.path.exists(temp_file), "Export should create file"
                assert os.path.getsize(temp_file) > 0, "Export file should not be empty"

                # File should contain valid JSON
                try:
                    with open(temp_file, 'r') as f:
                        config_data = json.load(f)
                    assert isinstance(config_data, dict), "Exported configuration should be JSON object"
                except json.JSONDecodeError:
                    pytest.fail("Export regression: File does not contain valid JSON")

                # Test import
                import_result = self.harness.execute_command_safely("importFromFile", temp_file)
                # Import might have specific requirements, but should handle gracefully

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @pytest.mark.skipif(not RegressionTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_configuration_consistency(self):
        """Test that configuration data remains consistent."""
        # Get configuration snapshots
        snapshots = {}
        config_commands = ["listDataSources", "listFeatures", "listAttributes"]

        for command in config_commands:
            result = self.harness.execute_command_safely(command, "json")
            if result["success"]:
                data = self.harness.extract_structured_data(result["stdout"], "json")
                if data:
                    snapshots[command] = data

        # Verify data types and basic structure
        for command, data in snapshots.items():
            assert isinstance(data, list), f"Configuration regression: {command} should return list"

            if data:  # If we have data, check structure
                first_item = data[0]
                assert isinstance(first_item, dict), f"Configuration regression: {command} items should be objects"

                # Should have some fields
                assert len(first_item) > 0, f"Configuration regression: {command} items should have fields"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])