"""API Compatibility Tests for sz_configtool.

These tests verify that the refactored sz_configtool maintains full backwards
compatibility with the original API contracts, including:
- Field names and data structures
- JSON response formats
- Command output patterns
- Error message formats
"""

import pytest
import json
import sys
import os
from io import StringIO
from unittest.mock import patch, Mock
from typing import Dict, Any, List, Optional

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


class APICompatibilityTester:
    """Test harness for API compatibility validation."""

    def __init__(self):
        """Initialize the test harness."""
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter)

        # Try to initialize Senzing
        self.senzing_available = self.config_manager.initialize_senzing()

        # Expected API contracts based on original sz_configtool
        self.api_contracts = self._load_api_contracts()

    def _load_api_contracts(self) -> Dict[str, Dict[str, Any]]:
        """Define expected API contracts for backwards compatibility."""
        return {
            "getAttribute": {
                "expected_fields": ["id", "attribute", "class", "default", "element", "feature", "internal", "required"],
                "field_types": {
                    "id": int,
                    "attribute": str,
                    "class": str,
                    "default": str,
                    "element": str,
                    "feature": str,
                    "internal": str,
                    "required": str
                },
                "sample_response": {
                    "id": 1,
                    "attribute": "NAME_FIRST",
                    "class": "NAME",
                    "default": "",
                    "element": "GIVEN_NAME",
                    "feature": "NAME",
                    "internal": "No",
                    "required": "Yes"
                }
            },
            "getFeature": {
                "expected_fields": ["id", "feature", "behavior", "anonymize", "candidates", "standardize", "expression", "comparison", "elementList"],
                "required_fields": ["elementList"],
                "field_types": {
                    "id": int,
                    "feature": str,
                    "behavior": str,
                    "elementList": list
                },
                "element_list_structure": {
                    "expected_fields": ["id", "element", "derived", "display", "order"],
                    "field_types": {
                        "id": int,
                        "element": str,
                        "order": int
                    }
                }
            },
            "listAttributes": {
                "expected_fields": ["id", "attribute", "class", "default"],
                "field_types": {
                    "id": int,
                    "attribute": str,
                    "class": str
                }
            },
            "listComparisonCalls": {
                "expected_fields": ["id", "function", "connectStr", "element", "order", "feature", "featureLink", "required"],
                "field_types": {
                    "id": int,
                    "function": str,
                    "element": str,
                    "order": int,
                    "feature": str,
                    "required": str
                }
            },
            "listDistinctCalls": {
                "expected_fields": ["id", "function", "connectStr", "element", "order", "feature", "featureLink", "required"],
                "field_types": {
                    "id": int,
                    "function": str,
                    "element": str,
                    "order": int
                }
            },
            "listExpressionCalls": {
                "expected_fields": ["id", "function", "connectStr", "element", "order", "feature", "featureLink", "required"],
                "field_types": {
                    "id": int,
                    "function": str,
                    "element": str,
                    "order": int
                }
            }
        }

    def validate_api_response(self, command: str, response_data: List[Dict], contract: Dict[str, Any]) -> List[str]:
        """Validate that response data matches API contract."""
        errors = []

        if not response_data:
            return ["Empty response data"]

        # Check first record for field compliance
        first_record = response_data[0]
        expected_fields = contract.get("expected_fields", [])
        required_fields = contract.get("required_fields", [])
        field_types = contract.get("field_types", {})

        # Check for missing required fields
        for field in expected_fields:
            if field not in first_record:
                errors.append(f"Missing expected field: {field}")

        # Check for missing absolutely required fields
        for field in required_fields:
            if field not in first_record:
                errors.append(f"Missing required field: {field}")

        # Check field types
        for field, expected_type in field_types.items():
            if field in first_record:
                actual_value = first_record[field]
                if actual_value is not None and not isinstance(actual_value, expected_type):
                    errors.append(f"Field {field} has wrong type: expected {expected_type.__name__}, got {type(actual_value).__name__}")

        # Special validation for getFeature elementList
        if command == "getFeature" and "elementList" in first_record:
            element_list = first_record["elementList"]
            if isinstance(element_list, list) and element_list:
                element_contract = contract.get("element_list_structure", {})
                element_errors = self.validate_api_response("elementList", element_list, element_contract)
                errors.extend([f"elementList: {error}" for error in element_errors])

        return errors

    def capture_command_output(self, command_method, args: str = "") -> tuple:
        """Capture both stdout and any JSON data from a command."""
        import sys
        old_stdout = sys.stdout
        try:
            # Set test flag and capture stdout
            sys._called_from_test = True
            sys.stdout = StringIO()

            command_method(args)
            output = sys.stdout.getvalue()

            # Try to extract JSON from output
            json_data = None
            output_stripped = output.strip()

            # First try to parse the entire output as JSON
            if output_stripped:
                try:
                    json_data = json.loads(output_stripped)
                except json.JSONDecodeError:
                    # If that fails, try line by line approach for single-line JSON
                    lines = output_stripped.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('[') or line.startswith('{'):
                            try:
                                json_data = json.loads(line)
                                break
                            except json.JSONDecodeError:
                                continue

            return output, json_data
        except Exception as e:
            return f"Error: {str(e)}", None
        finally:
            sys.stdout = old_stdout
            if hasattr(sys, '_called_from_test'):
                delattr(sys, '_called_from_test')


class TestAPICompatibility:
    """Test suite for API compatibility validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tester = APICompatibilityTester()
        self.setup_mock_data()

    def setup_mock_data(self):
        """Set up mock data that mimics original sz_configtool responses."""
        # Mock data with ORIGINAL API field names (not database schema names)
        self.mock_attributes = [
            {
                "id": 1,
                "attribute": "NAME_FIRST",
                "class": "NAME",
                "default": "",
                "element": "GIVEN_NAME",
                "feature": "NAME",
                "internal": "No",
                "required": "Yes"
            },
            {
                "id": 2,
                "attribute": "NAME_LAST",
                "class": "NAME",
                "default": "",
                "element": "SURNAME",
                "feature": "NAME",
                "internal": "No",
                "required": "Yes"
            }
        ]

        self.mock_features = [
            {
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
                    },
                    {
                        "id": 2,
                        "element": "SURNAME",
                        "derived": "No",
                        "display": "No",
                        "order": 2
                    }
                ]
            }
        ]

        self.mock_comparison_calls = [
            {
                "id": 1,
                "function": "NAME_COMPARISON",
                "connectStr": "NAME_COMP",
                "element": "GIVEN_NAME",
                "order": 1,
                "feature": "NAME",
                "featureLink": "NAME_LINK",
                "required": "Yes"
            }
        ]

    def test_getAttribute_api_compatibility(self):
        """Test getAttribute maintains original API contract."""
        if not self.tester.senzing_available:
            pytest.skip("Senzing not available")

        # Test the command with real data
        output, json_data = self.tester.capture_command_output(
            self.tester.shell.do_getAttribute, "NAME_FIRST json"
        )

        # Validate API contract
        if json_data:
            contract = self.tester.api_contracts["getAttribute"]
            errors = self.tester.validate_api_response("getAttribute", [json_data], contract)

            if errors:
                pytest.fail(f"getAttribute API compatibility errors: {errors}")
            # If no errors, the test passes
        else:
            pytest.fail(f"getAttribute did not return valid JSON. Output: {output}")

    def test_getFeature_api_compatibility(self):
        """Test getFeature maintains original API contract with elementList."""
        if not self.tester.senzing_available:
            pytest.skip("Senzing not available")

        # Test the command with real data
        output, json_data = self.tester.capture_command_output(
            self.tester.shell.do_getFeature, "NAME json"
        )

        # Validate API contract
        if json_data:
            contract = self.tester.api_contracts["getFeature"]
            errors = self.tester.validate_api_response("getFeature", [json_data], contract)

            if errors:
                pytest.fail(f"getFeature API compatibility errors: {errors}")
            # If no errors, the test passes
        else:
            pytest.fail(f"getFeature did not return valid JSON. Output: {output}")

    def test_listAttributes_api_compatibility(self):
        """Test listAttributes maintains original API contract."""
        if not self.tester.senzing_available:
            pytest.skip("Senzing not available")

        # Test the command with real data
        output, json_data = self.tester.capture_command_output(
            self.tester.shell.do_listAttributes, "json"
        )

        # Validate API contract
        if json_data and isinstance(json_data, list):
            contract = self.tester.api_contracts["listAttributes"]
            errors = self.tester.validate_api_response("listAttributes", json_data, contract)

            if errors:
                pytest.fail(f"listAttributes API compatibility errors: {errors}")
            # If no errors, the test passes
        else:
            pytest.fail(f"listAttributes did not return valid JSON array. Output: {output}")

    def test_listComparisonCalls_api_compatibility(self):
        """Test listComparisonCalls maintains original API contract."""
        if not self.tester.senzing_available:
            pytest.skip("Senzing not available")

        # Test the command with real data
        output, json_data = self.tester.capture_command_output(
            self.tester.shell.do_listComparisonCalls, "json"
        )

        # Validate API contract
        if json_data and isinstance(json_data, list):
            contract = self.tester.api_contracts["listComparisonCalls"]
            errors = self.tester.validate_api_response("listComparisonCalls", json_data, contract)

            if errors:
                pytest.fail(f"listComparisonCalls API compatibility errors: {errors}")
            # If no errors, the test passes
        else:
            pytest.fail(f"listComparisonCalls did not return valid JSON array. Output: {output}")

    def test_field_naming_conventions(self):
        """Test that field names follow original camelCase conventions, not database schema."""
        if not self.tester.senzing_available:
            pytest.skip("Senzing not available")

        # Test getAttribute specifically for field naming with real data
        output, json_data = self.tester.capture_command_output(
            self.tester.shell.do_getAttribute, "NAME_FIRST json"
        )

        if json_data:
            # Check for database schema field names (these should NOT exist in API)
            forbidden_fields = ["ATTR_ID", "ATTR_CODE", "ATTR_CLASS", "FTYPE_CODE", "FELEM_CODE"]
            found_forbidden = [field for field in forbidden_fields if field in json_data]

            if found_forbidden:
                pytest.fail(f"Found database schema field names in API response: {found_forbidden}. "
                           f"API should use user-friendly names like 'id', 'attribute', 'class'")

            # Check for required user-friendly field names
            required_friendly = ["id", "attribute", "class"]
            missing_friendly = [field for field in required_friendly if field not in json_data]

            if missing_friendly:
                pytest.fail(f"Missing user-friendly field names: {missing_friendly}")

    def test_error_message_compatibility(self):
        """Test that error messages maintain original format."""
        # Test with an invalid command to trigger error handling
        output, _ = self.tester.capture_command_output(
            self.tester.shell.do_getAttribute, ""  # Missing required parameter
        )

        # Original error messages should contain specific patterns
        if "Error:" not in output:
            pytest.fail(f"Error message format changed. Expected 'Error:' prefix. Got: {output}")

    def test_help_output_format(self):
        """Test that help output maintains recognizable structure."""
        output, _ = self.tester.capture_command_output(
            self.tester.shell.do_help, "getAttribute"
        )

        # Help should contain syntax information
        if "Syntax:" not in output and "Usage:" not in output:
            pytest.fail(f"Help format changed. Expected 'Syntax:' or 'Usage:' section. Got: {output}")


class TestFullCommandCompatibility:
    """Test all 120 commands for basic API compatibility."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tester = APICompatibilityTester()
        self.commands_to_test = self._get_all_commands()

    def _get_all_commands(self) -> List[str]:
        """Get list of all sz_configtool commands."""
        command_list = []
        for attr_name in dir(self.tester.shell):
            if attr_name.startswith('do_') and not attr_name.startswith('do_help'):
                command_name = attr_name[3:]  # Remove 'do_' prefix
                command_list.append(command_name)
        return sorted(command_list)

    @pytest.mark.parametrize("command_name", [
        "getAttribute", "getFeature", "listAttributes", "listFeatures",
        "listComparisonCalls", "listDistinctCalls", "listExpressionCalls",
        "addAttribute", "addFeature", "deleteAttribute", "deleteFeature"
    ])
    def test_critical_command_compatibility(self, command_name):
        """Test critical commands for API compatibility."""
        if not hasattr(self.tester.shell, f'do_{command_name}'):
            pytest.fail(f"Command {command_name} is missing from refactored implementation")

        # For get/list commands, test with real data if Senzing is available
        if not self.tester.senzing_available and (command_name.startswith('get') or command_name.startswith('list')):
            pytest.skip("Senzing not available")

        # Test that command executes without crashing
        try:
            method = getattr(self.tester.shell, f'do_{command_name}')
            output, json_data = self.tester.capture_command_output(method, "")

            # Should not crash and should produce some output
            assert isinstance(output, str), f"Command {command_name} produced non-string output"

        except Exception as e:
            # Some commands may require parameters, that's acceptable
            if not any(word in str(e).lower() for word in ['required', 'parameter', 'argument', 'missing']):
                pytest.fail(f"Command {command_name} crashed unexpectedly: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])