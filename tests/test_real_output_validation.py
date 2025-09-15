"""Real Output Validation Tests.

These tests run actual commands against the refactored sz_configtool
to capture and validate the real output, without mocking.
"""

import pytest
import json
import sys
import os
from io import StringIO
from unittest.mock import patch
from typing import Dict, Any, List, Optional

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


class RealOutputValidator:
    """Validate actual output from the refactored sz_configtool."""

    def __init__(self):
        """Initialize the validator with real instances."""
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter)

        # Try to initialize Senzing
        self.senzing_available = self.config_manager.initialize_senzing()

    def run_real_command(self, command_name: str, args: str = "") -> tuple:
        """Run a real command and capture its output."""
        if not hasattr(self.shell, f'do_{command_name}'):
            return f"Command {command_name} not found", None, 1

        method = getattr(self.shell, f'do_{command_name}')

        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with patch('sys.stderr', new=StringIO()) as fake_stderr:
                try:
                    method(args)
                    stdout = fake_stdout.getvalue()
                    stderr = fake_stderr.getvalue()

                    # Try to extract JSON from output
                    json_data = self.extract_json_from_output(stdout)

                    return stdout, json_data, 0
                except Exception as e:
                    return fake_stdout.getvalue(), None, 1

    def extract_json_from_output(self, output: str) -> Optional[Dict]:
        """Extract JSON data from command output."""
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('[') or line.startswith('{'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return None

    def validate_field_names(self, json_data: Dict, command_name: str) -> List[str]:
        """Validate field names in JSON output."""
        issues = []

        if not isinstance(json_data, dict):
            return ["Output is not a dictionary"]

        # Database schema field names that should NOT appear in API
        forbidden_fields = [
            "ATTR_ID", "ATTR_CODE", "ATTR_CLASS", "DEFAULT_VALUE",
            "FELEM_CODE", "FTYPE_CODE", "FELEM_REQ", "INTERNAL",
            "FTYPE_ID", "FTYPE_FREQ", "FTYPE_SHOW", "FTYPE_RULE",
            "DSRC_ID", "DSRC_CODE", "DSRC_DESC", "DSRC_RELY",
            "CFCALL_ID", "CFUNC_ID", "CFUNC_CODE", "EXEC_ORDER"
        ]

        # Check for forbidden database schema field names
        found_forbidden = [field for field in forbidden_fields if field in json_data]
        if found_forbidden:
            issues.append(f"Found database schema field names: {found_forbidden}")

        # Expected user-friendly field names by command
        expected_fields = {
            "getAttribute": ["id", "attribute", "class", "default", "element", "feature", "internal", "required"],
            "getFeature": ["id", "feature", "behavior", "elementList"],
            "listAttributes": ["id", "attribute", "class"],
            "listFeatures": ["id", "feature", "behavior"],
            "listDataSources": ["id", "dataSource", "description"]
        }

        if command_name in expected_fields:
            required_fields = expected_fields[command_name]
            missing_fields = [field for field in required_fields if field not in json_data]
            if missing_fields:
                issues.append(f"Missing expected user-friendly fields: {missing_fields}")

        return issues


class TestRealOutputValidation:
    """Test suite for validating real command output."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = RealOutputValidator()

    @pytest.mark.skipif(not os.path.exists("/home/bmacy/open_dev/sz-python-tools/sz_tools/sz_configtool"),
                       reason="Original sz_configtool not available")
    def test_help_command_real_output(self):
        """Test real help command output."""
        output, json_data, returncode = self.validator.run_real_command("help")

        # Should produce some help output
        assert output.strip(), "Help command produced no output"
        assert "help" in output.lower() or "command" in output.lower(), "Help output doesn't contain expected content"

    def test_listDataSources_real_output_format(self):
        """Test real listDataSources output format."""
        if not self.validator.senzing_available:
            pytest.skip("Senzing not available for real testing")

        # Test JSON output format
        output, json_data, returncode = self.validator.run_real_command("listDataSources", "json")

        if json_data is not None:
            if isinstance(json_data, list) and json_data:
                # Validate field names in first item
                first_item = json_data[0]
                issues = self.validator.validate_field_names(first_item, "listDataSources")

                if issues:
                    pytest.fail(f"listDataSources field validation issues: {issues}\\nActual output: {json_data}")
            elif isinstance(json_data, list):
                # Empty list is acceptable
                pass
            else:
                pytest.fail(f"listDataSources should return JSON array, got {type(json_data)}")

    def test_getAttribute_real_output_format(self):
        """Test real getAttribute output format."""
        if not self.validator.senzing_available:
            pytest.skip("Senzing not available for real testing")

        # First get list of attributes to test with
        list_output, list_json, _ = self.validator.run_real_command("listAttributes", "json")

        if list_json and isinstance(list_json, list) and list_json:
            # Use first attribute for testing
            first_attr = list_json[0]
            if "attribute" in first_attr:
                attr_name = first_attr["attribute"]
            elif "ATTR_CODE" in first_attr:
                attr_name = first_attr["ATTR_CODE"]
            else:
                pytest.skip("Cannot determine attribute name from list output")

            # Test getAttribute with the found attribute
            output, json_data, returncode = self.validator.run_real_command("getAttribute", f"{attr_name} json")

            if json_data is not None:
                issues = self.validator.validate_field_names(json_data, "getAttribute")
                if issues:
                    pytest.fail(f"getAttribute field validation issues: {issues}\\nActual output: {json_data}")
        else:
            pytest.skip("No attributes available for testing")

    def test_getFeature_real_output_format(self):
        """Test real getFeature output format."""
        if not self.validator.senzing_available:
            pytest.skip("Senzing not available for real testing")

        # First get list of features to test with
        list_output, list_json, _ = self.validator.run_real_command("listFeatures", "json")

        if list_json and isinstance(list_json, list) and list_json:
            # Use first feature for testing
            first_feature = list_json[0]
            if "feature" in first_feature:
                feature_name = first_feature["feature"]
            elif "FTYPE_CODE" in first_feature:
                feature_name = first_feature["FTYPE_CODE"]
            else:
                pytest.skip("Cannot determine feature name from list output")

            # Test getFeature with the found feature
            output, json_data, returncode = self.validator.run_real_command("getFeature", f"{feature_name} json")

            if json_data is not None:
                issues = self.validator.validate_field_names(json_data, "getFeature")
                if issues:
                    pytest.fail(f"getFeature field validation issues: {issues}\\nActual output: {json_data}")

                # Special check for elementList
                if "elementList" not in json_data:
                    pytest.fail(f"getFeature missing required 'elementList' field. Actual output: {json_data}")
        else:
            pytest.skip("No features available for testing")

    def test_actual_field_naming_issues(self):
        """Test for actual field naming issues in real output."""
        if not self.validator.senzing_available:
            pytest.skip("Senzing not available for real testing")

        # Test multiple list commands for field naming issues
        commands_to_test = ["listDataSources", "listFeatures", "listAttributes"]

        field_issues = {}

        for command in commands_to_test:
            output, json_data, returncode = self.validator.run_real_command(command, "json")

            if json_data and isinstance(json_data, list) and json_data:
                first_item = json_data[0]
                issues = self.validator.validate_field_names(first_item, command)
                if issues:
                    field_issues[command] = {
                        "issues": issues,
                        "actual_fields": list(first_item.keys()),
                        "sample_data": first_item
                    }

        if field_issues:
            error_report = "\\n\\nField naming compatibility issues found:\\n"
            for command, details in field_issues.items():
                error_report += f"\\n{command}:\\n"
                error_report += f"  Issues: {details['issues']}\\n"
                error_report += f"  Actual fields: {details['actual_fields']}\\n"
                error_report += f"  Sample data: {details['sample_data']}\\n"

            pytest.fail(error_report)

    def test_json_output_structure_validation(self):
        """Test JSON output structure across multiple commands."""
        if not self.validator.senzing_available:
            pytest.skip("Senzing not available for real testing")

        commands_to_test = [
            "listDataSources", "listFeatures", "listAttributes",
            "listElements", "listFeatureClasses", "listEntityTypes"
        ]

        structure_issues = {}

        for command in commands_to_test:
            output, json_data, returncode = self.validator.run_real_command(command, "json")

            issues = []

            # JSON should be valid
            if json_data is None:
                if "json" in output.lower():
                    issues.append("Command requested JSON but output was not valid JSON")

            # List commands should return arrays
            elif not isinstance(json_data, list):
                issues.append(f"List command should return JSON array, got {type(json_data).__name__}")

            # If array has items, check structure
            elif json_data:
                first_item = json_data[0]
                if not isinstance(first_item, dict):
                    issues.append(f"Array items should be objects, got {type(first_item).__name__}")
                else:
                    # Check for empty objects
                    if not first_item:
                        issues.append("Array contains empty objects")

            if issues:
                structure_issues[command] = {
                    "issues": issues,
                    "output_sample": output[:200] + "..." if len(output) > 200 else output,
                    "json_type": type(json_data).__name__ if json_data is not None else "None"
                }

        if structure_issues:
            error_report = "\\n\\nJSON structure issues found:\\n"
            for command, details in structure_issues.items():
                error_report += f"\\n{command}:\\n"
                error_report += f"  Issues: {details['issues']}\\n"
                error_report += f"  JSON type: {details['json_type']}\\n"
                error_report += f"  Output sample: {details['output_sample']}\\n"

            pytest.fail(error_report)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])