"""Output Comparison Tests for sz_configtool.

These tests compare the actual output from the refactored sz_configtool
against expected output patterns from the original tool to catch
backwards compatibility issues.
"""

import pytest
import json
import subprocess
import sys
import os
from io import StringIO
from unittest.mock import patch, Mock
from typing import Dict, Any, List, Optional, Tuple

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


class OutputComparisonTester:
    """Compare output between original and refactored sz_configtool."""

    def __init__(self):
        """Initialize the comparison tester."""
        self.original_tool_path = "/home/bmacy/open_dev/sz-python-tools/sz_tools/sz_configtool"
        self.setup_refactored_tool()
        self.setup_environment()

    def setup_refactored_tool(self):
        """Set up the refactored tool for testing."""
        self.config_manager = Mock(spec=ConfigurationManager)
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter)

    def setup_environment(self):
        """Set up environment for both tools."""
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

    def run_original_command(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """Run a command on the original sz_configtool."""
        try:
            process = subprocess.run(
                [self.original_tool_path],
                input=f"{command}\\nquit\\n",
                text=True,
                capture_output=True,
                env=self.env,
                timeout=timeout
            )

            # Clean up output - remove prompts and color codes
            stdout = process.stdout
            stderr = process.stderr
            returncode = process.returncode

            # Filter out interactive prompts and colors
            lines = stdout.split('\\n')
            filtered_lines = []
            for line in lines:
                if 'Type help' not in line and 'szcfg' not in line and line.strip():
                    # Remove ANSI color codes
                    import re
                    line = re.sub(r'\\x1b\\[[0-9;]*m', '', line)
                    filtered_lines.append(line)

            clean_output = '\\n'.join(filtered_lines)
            return clean_output, stderr, returncode

        except subprocess.TimeoutExpired:
            return "", f"Command timed out: {command}", 1
        except Exception as e:
            return "", f"Error running command: {e}", 1

    def run_refactored_command(self, command_name: str, args: str = "") -> Tuple[str, str, int]:
        """Run a command on the refactored sz_configtool."""
        try:
            if not hasattr(self.shell, f'do_{command_name}'):
                return "", f"Command {command_name} not found", 1

            method = getattr(self.shell, f'do_{command_name}')

            with patch('sys.stdout', new=StringIO()) as fake_stdout:
                with patch('sys.stderr', new=StringIO()) as fake_stderr:
                    try:
                        method(args)
                        return fake_stdout.getvalue(), fake_stderr.getvalue(), 0
                    except Exception as e:
                        return fake_stdout.getvalue(), str(e), 1

        except Exception as e:
            return "", f"Error running refactored command: {e}", 1

    def extract_json_from_output(self, output: str) -> Optional[Dict]:
        """Extract JSON data from command output."""
        lines = output.strip().split('\\n')
        for line in lines:
            line = line.strip()
            if line.startswith('[') or line.startswith('{'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return None

    def compare_field_structures(self, original_data: Dict, refactored_data: Dict) -> List[str]:
        """Compare field structures between original and refactored output."""
        issues = []

        if not isinstance(original_data, dict) or not isinstance(refactored_data, dict):
            return ["One or both outputs are not dictionaries"]

        # Check for missing fields from original
        for field in original_data.keys():
            if field not in refactored_data:
                issues.append(f"Missing field in refactored output: {field}")

        # Check for unexpected fields in refactored
        for field in refactored_data.keys():
            if field not in original_data:
                issues.append(f"New field in refactored output: {field}")

        # Check field value types
        for field in original_data.keys():
            if field in refactored_data:
                orig_type = type(original_data[field])
                refact_type = type(refactored_data[field])
                if orig_type != refact_type:
                    issues.append(f"Field {field} type changed: {orig_type.__name__} -> {refact_type.__name__}")

        return issues

    def normalize_output_for_comparison(self, output: str) -> str:
        """Normalize output for comparison by removing formatting differences."""
        lines = output.strip().split('\\n')
        normalized_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('(') and 'szcfg' not in line:
                # Remove extra whitespace
                line = ' '.join(line.split())
                normalized_lines.append(line)

        return '\\n'.join(normalized_lines)


class TestOutputComparison:
    """Test suite for comparing original vs refactored output."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tester = OutputComparisonTester()
        self.setup_mock_data()

    def setup_mock_data(self):
        """Set up consistent mock data for testing."""
        # Sample attribute data that should match original format
        self.sample_attribute = {
            "id": 1,
            "attribute": "NAME_FIRST",
            "class": "NAME",
            "default": "",
            "element": "GIVEN_NAME",
            "feature": "NAME",
            "internal": "No",
            "required": "Yes"
        }

        # Sample feature data with elementList
        self.sample_feature = {
            "id": 1,
            "feature": "NAME",
            "behavior": "NAME",
            "anonymize": "No",
            "candidates": "Yes",
            "standardize": "Yes",
            "expression": "Yes",
            "comparison": "Yes",
            "elementList": [
                {
                    "id": 1,
                    "element": "GIVEN_NAME",
                    "derived": "No",
                    "display": "No",
                    "order": 1
                }
            ]
        }

    def test_help_command_structure(self):
        """Test that help command output has similar structure."""
        # Run help on both versions
        original_output, _, _ = self.tester.run_original_command("help")
        refactored_output, _, _ = self.tester.run_refactored_command("help")

        # Both should contain help information
        assert "help" in original_output.lower() or "command" in original_output.lower(), "Original help seems invalid"
        assert "help" in refactored_output.lower() or "command" in refactored_output.lower(), "Refactored help seems invalid"

        # Check that refactored help has some similarity to original
        # This is a basic structure check - not exact content match
        original_normalized = self.tester.normalize_output_for_comparison(original_output)
        refactored_normalized = self.tester.normalize_output_for_comparison(refactored_output)

        # Both should be substantial (more than just error messages)
        assert len(original_normalized) > 50, "Original help output too short"
        assert len(refactored_normalized) > 50, "Refactored help output too short"

    def test_getAttribute_output_structure(self):
        """Test getAttribute output structure matches original expectations."""
        # Mock the refactored tool to return database schema names (current behavior)
        self.tester.config_manager.get_record.return_value = {
            "ATTR_ID": 1,
            "ATTR_CODE": "NAME_FIRST",
            "ATTR_CLASS": "NAME",
            "DEFAULT_VALUE": "",
            "FELEM_CODE": "GIVEN_NAME",
            "FTYPE_CODE": "NAME",
            "INTERNAL": "No",
            "FELEM_REQ": "Yes"
        }

        # Run the refactored command
        refactored_output, _, _ = self.tester.run_refactored_command("getAttribute", "NAME_FIRST json")

        # Extract JSON if present
        json_data = self.tester.extract_json_from_output(refactored_output)

        if json_data:
            # Check if the output uses database schema names (this should FAIL)
            database_fields = ["ATTR_ID", "ATTR_CODE", "ATTR_CLASS", "DEFAULT_VALUE", "FELEM_CODE", "FTYPE_CODE"]
            found_db_fields = [field for field in database_fields if field in json_data]

            if found_db_fields:
                pytest.fail(f"getAttribute returns database schema field names: {found_db_fields}. "
                           f"Should return user-friendly names: ['id', 'attribute', 'class', 'default', 'element', 'feature']")

            # Check for expected user-friendly field names
            expected_fields = ["id", "attribute", "class", "default", "element", "feature", "internal", "required"]
            missing_fields = [field for field in expected_fields if field not in json_data]

            if missing_fields:
                pytest.fail(f"getAttribute missing expected fields: {missing_fields}")

    def test_getFeature_elementList_structure(self):
        """Test that getFeature returns complete elementList structure."""
        # Mock the refactored tool to return incomplete data (current behavior)
        self.tester.config_manager.get_record.return_value = {
            "FTYPE_ID": 1,
            "FTYPE_CODE": "NAME",
            "FTYPE_FREQ": "NAME"
            # Missing elementList and other fields
        }

        # Run the refactored command
        refactored_output, _, _ = self.tester.run_refactored_command("getFeature", "NAME json")

        # Extract JSON if present
        json_data = self.tester.extract_json_from_output(refactored_output)

        if json_data:
            # Check for elementList (this should FAIL currently)
            if "elementList" not in json_data:
                pytest.fail("getFeature missing required 'elementList' field")

            # Check elementList structure
            element_list = json_data.get("elementList", [])
            if not isinstance(element_list, list):
                pytest.fail(f"elementList should be a list, got {type(element_list)}")

            if element_list:  # If elementList exists and has items
                first_element = element_list[0]
                expected_element_fields = ["id", "element", "derived", "display", "order"]
                missing_element_fields = [field for field in expected_element_fields if field not in first_element]

                if missing_element_fields:
                    pytest.fail(f"elementList items missing fields: {missing_element_fields}")

    def test_json_output_format_consistency(self):
        """Test that JSON output format is consistent and valid."""
        commands_to_test = [
            ("listAttributes", "json"),
            ("listFeatures", "json"),
            ("listDataSources", "json")
        ]

        for command, args in commands_to_test:
            if hasattr(self.tester.shell, f'do_{command}'):
                # Mock some sample data
                self.tester.config_manager.get_record_list.return_value = [
                    {"id": 1, "code": "TEST", "description": "Test item"}
                ]

                refactored_output, _, _ = self.tester.run_refactored_command(command, args)
                json_data = self.tester.extract_json_from_output(refactored_output)

                if json_data is None:
                    pytest.fail(f"Command {command} with 'json' argument did not produce valid JSON output")

                # JSON should be a list for list commands
                if command.startswith('list'):
                    if not isinstance(json_data, list):
                        pytest.fail(f"Command {command} should return JSON array, got {type(json_data)}")

    def test_error_message_format_compatibility(self):
        """Test that error messages follow original format patterns."""
        # Test various error conditions
        error_test_cases = [
            ("getAttribute", ""),  # Missing required parameter
            ("getFeature", ""),    # Missing required parameter
            ("addDataSource", ""), # Missing required parameter
        ]

        for command, args in error_test_cases:
            if hasattr(self.tester.shell, f'do_{command}'):
                refactored_output, _, _ = self.tester.run_refactored_command(command, args)

                # Should contain error indication
                if "error" not in refactored_output.lower() and "required" not in refactored_output.lower():
                    pytest.fail(f"Command {command} with invalid args should produce error message. Got: {refactored_output}")

                # Should not crash or produce empty output
                assert refactored_output.strip(), f"Command {command} produced empty output on error"


class TestFieldNamingCompatibility:
    """Specific tests for field naming compatibility issues."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tester = OutputComparisonTester()

    def test_database_schema_vs_api_names(self):
        """Test that API uses user-friendly names, not database schema names."""
        # Database schema names that should NOT appear in API
        forbidden_db_names = [
            "ATTR_ID", "ATTR_CODE", "ATTR_CLASS", "DEFAULT_VALUE",
            "FELEM_CODE", "FTYPE_CODE", "FELEM_REQ", "INTERNAL",
            "FTYPE_ID", "FTYPE_FREQ", "FTYPE_SHOW", "FTYPE_RULE",
            "DSRC_ID", "DSRC_CODE", "DSRC_DESC", "DSRC_RELY"
        ]

        # Expected user-friendly API names
        expected_api_names = [
            "id", "attribute", "class", "default", "element", "feature",
            "internal", "required", "behavior", "frequency", "show", "rule"
        ]

        # Test getAttribute specifically
        self.tester.config_manager.get_record.return_value = {
            "ATTR_ID": 1,
            "ATTR_CODE": "NAME_FIRST",
            "ATTR_CLASS": "NAME"
        }

        refactored_output, _, _ = self.tester.run_refactored_command("getAttribute", "NAME_FIRST json")
        json_data = self.tester.extract_json_from_output(refactored_output)

        if json_data:
            # Check for forbidden database schema names
            found_forbidden = [name for name in forbidden_db_names if name in json_data]
            if found_forbidden:
                pytest.fail(f"Found database schema names in API output: {found_forbidden}")

            # Check for expected user-friendly names
            found_expected = [name for name in expected_api_names if name in json_data]
            if not found_expected:
                pytest.fail(f"No user-friendly field names found. Expected some of: {expected_api_names}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])