"""Breaking Changes Detection Tests.

These tests are designed to FAIL and identify specific backwards
compatibility issues in the refactored sz_configtool.
"""

import pytest
import json
import sys
import os
from io import StringIO
from unittest.mock import patch
from typing import Dict, Any, List

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


class BreakingChangesDetector:
    """Detect breaking changes in the refactored implementation."""

    def __init__(self):
        """Initialize detector with real instances."""
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter)

        # Initialize Senzing
        self.senzing_available = self.config_manager.initialize_senzing()

    def capture_command_json_output(self, command_name: str, args: str = "") -> Dict:
        """Capture JSON output from a command."""
        if not hasattr(self.shell, f'do_{command_name}'):
            return None

        method = getattr(self.shell, f'do_{command_name}')

        # Capture both stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            # Set test flag and capture stdout
            sys._called_from_test = True
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            method(args)

            stdout_content = sys.stdout.getvalue()
            stderr_content = sys.stderr.getvalue()

            # Try to parse JSON from stdout
            stdout_stripped = stdout_content.strip()

            # First try to parse the entire output as JSON
            if stdout_stripped:
                try:
                    return json.loads(stdout_stripped)
                except json.JSONDecodeError:
                    # If that fails, try line by line approach for single-line JSON
                    lines = stdout_stripped.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('[') or line.startswith('{'):
                            try:
                                return json.loads(line)
                            except json.JSONDecodeError:
                                continue

            return None

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            if hasattr(sys, '_called_from_test'):
                delattr(sys, '_called_from_test')


class TestBreakingChangesDetection:
    """Test suite designed to catch breaking changes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = BreakingChangesDetector()

    @pytest.mark.skipif(not BreakingChangesDetector().senzing_available,
                       reason="Senzing not available")
    def test_listDataSources_field_names_breaking_change(self):
        """EXPECTED TO FAIL: listDataSources uses database schema field names."""
        json_output = self.detector.capture_command_json_output("listDataSources", "json")

        if json_output and isinstance(json_output, list) and json_output:
            first_item = json_output[0]

            # Check for database schema field names (these should NOT exist in API)
            database_schema_fields = ["DSRC_ID", "DSRC_CODE", "DSRC_DESC"]
            found_db_fields = [field for field in database_schema_fields if field in first_item]

            if found_db_fields:
                pytest.fail(
                    f"BREAKING CHANGE DETECTED: listDataSources returns database schema field names {found_db_fields}. "
                    f"Expected user-friendly names: ['id', 'dataSource', 'description']. "
                    f"Actual output: {first_item}"
                )

            # Check for expected user-friendly field names
            expected_api_fields = ["id", "dataSource", "description"]
            missing_api_fields = [field for field in expected_api_fields if field not in first_item]

            if missing_api_fields:
                pytest.fail(
                    f"BREAKING CHANGE DETECTED: listDataSources missing user-friendly field names {missing_api_fields}. "
                    f"Actual fields: {list(first_item.keys())}"
                )

    @pytest.mark.skipif(not BreakingChangesDetector().senzing_available,
                       reason="Senzing not available")
    def test_listAttributes_field_names_breaking_change(self):
        """EXPECTED TO FAIL: listAttributes uses database schema field names."""
        json_output = self.detector.capture_command_json_output("listAttributes", "json")

        if json_output and isinstance(json_output, list) and json_output:
            first_item = json_output[0]

            # Check for database schema field names (these should NOT exist in API)
            database_schema_fields = ["ATTR_ID", "ATTR_CODE", "ATTR_CLASS"]
            found_db_fields = [field for field in database_schema_fields if field in first_item]

            if found_db_fields:
                pytest.fail(
                    f"BREAKING CHANGE DETECTED: listAttributes returns database schema field names {found_db_fields}. "
                    f"Expected user-friendly names: ['id', 'attribute', 'class']. "
                    f"Actual output: {first_item}"
                )

    @pytest.mark.skipif(not BreakingChangesDetector().senzing_available,
                       reason="Senzing not available")
    def test_listFeatures_field_names_breaking_change(self):
        """EXPECTED TO FAIL: listFeatures uses database schema field names."""
        json_output = self.detector.capture_command_json_output("listFeatures", "json")

        if json_output and isinstance(json_output, list) and json_output:
            first_item = json_output[0]

            # Check for database schema field names (these should NOT exist in API)
            database_schema_fields = ["FTYPE_ID", "FTYPE_CODE", "FTYPE_FREQ"]
            found_db_fields = [field for field in database_schema_fields if field in first_item]

            if found_db_fields:
                pytest.fail(
                    f"BREAKING CHANGE DETECTED: listFeatures returns database schema field names {found_db_fields}. "
                    f"Expected user-friendly names: ['id', 'feature', 'frequency']. "
                    f"Actual output: {first_item}"
                )

    @pytest.mark.skipif(not BreakingChangesDetector().senzing_available,
                       reason="Senzing not available")
    def test_getAttribute_field_names_breaking_change(self):
        """EXPECTED TO FAIL: getAttribute uses database schema field names."""
        # First get a list of attributes to test with
        list_json = self.detector.capture_command_json_output("listAttributes", "json")

        if list_json and isinstance(list_json, list) and list_json:
            # Get the first attribute name (try both possible field names)
            first_attr = list_json[0]
            attr_name = first_attr.get("ATTR_CODE") or first_attr.get("attribute")

            if attr_name:
                json_output = self.detector.capture_command_json_output("getAttribute", f"{attr_name} json")

                if json_output and isinstance(json_output, dict):
                    # Check for database schema field names (these should NOT exist in API)
                    database_schema_fields = ["ATTR_ID", "ATTR_CODE", "ATTR_CLASS", "DEFAULT_VALUE", "FELEM_CODE", "FTYPE_CODE"]
                    found_db_fields = [field for field in database_schema_fields if field in json_output]

                    if found_db_fields:
                        pytest.fail(
                            f"BREAKING CHANGE DETECTED: getAttribute returns database schema field names {found_db_fields}. "
                            f"Expected user-friendly names: ['id', 'attribute', 'class', 'default', 'element', 'feature']. "
                            f"Actual output: {json_output}"
                        )

    @pytest.mark.skipif(not BreakingChangesDetector().senzing_available,
                       reason="Senzing not available")
    def test_getFeature_missing_elementList_breaking_change(self):
        """EXPECTED TO FAIL: getFeature missing elementList structure."""
        # First get a list of features to test with
        list_json = self.detector.capture_command_json_output("listFeatures", "json")

        if list_json and isinstance(list_json, list) and list_json:
            # Get the first feature name (try both possible field names)
            first_feature = list_json[0]
            feature_name = first_feature.get("FTYPE_CODE") or first_feature.get("feature")

            if feature_name:
                json_output = self.detector.capture_command_json_output("getFeature", f"{feature_name} json")

                if json_output and isinstance(json_output, dict):
                    # Check for missing elementList
                    if "elementList" not in json_output:
                        pytest.fail(
                            f"BREAKING CHANGE DETECTED: getFeature missing required 'elementList' field. "
                            f"This field is critical for understanding feature configuration. "
                            f"Actual output: {json_output}"
                        )

                    # If elementList exists, check its structure
                    element_list = json_output.get("elementList", [])
                    if not isinstance(element_list, list):
                        pytest.fail(
                            f"BREAKING CHANGE DETECTED: getFeature 'elementList' should be an array. "
                            f"Got {type(element_list)}. Actual output: {json_output}"
                        )

    @pytest.mark.skipif(not BreakingChangesDetector().senzing_available,
                       reason="Senzing not available")
    def test_listComparisonCalls_missing_relationship_fields_breaking_change(self):
        """EXPECTED TO FAIL: listComparisonCalls missing relationship fields."""
        json_output = self.detector.capture_command_json_output("listComparisonCalls", "json")

        if json_output and isinstance(json_output, list) and json_output:
            first_item = json_output[0]

            # Check for missing relationship fields that original API provides
            expected_relationship_fields = ["element", "order", "feature", "featureLink", "required"]
            missing_fields = [field for field in expected_relationship_fields if field not in first_item]

            if missing_fields:
                pytest.fail(
                    f"BREAKING CHANGE DETECTED: listComparisonCalls missing relationship fields {missing_fields}. "
                    f"These fields are critical for understanding function relationships. "
                    f"Actual fields: {list(first_item.keys())}"
                )

    def test_command_existence_breaking_change(self):
        """Test that all expected commands exist."""
        expected_commands = [
            "getAttribute", "getFeature", "getElement",
            "listAttributes", "listFeatures", "listDataSources", "listElements",
            "addAttribute", "addFeature", "addDataSource", "addElement",
            "deleteAttribute", "deleteFeature", "deleteDataSource", "deleteElement",
            "listComparisonCalls", "listDistinctCalls", "listExpressionCalls"
        ]

        missing_commands = []
        for command in expected_commands:
            if not hasattr(self.detector.shell, f'do_{command}'):
                missing_commands.append(command)

        if missing_commands:
            pytest.fail(f"BREAKING CHANGE DETECTED: Missing commands {missing_commands}")

    def test_json_output_format_breaking_change(self):
        """Test that commands support json output format."""
        if not self.detector.senzing_available:
            pytest.skip("Senzing not available")

        commands_to_test = ["listDataSources", "listFeatures", "listAttributes"]

        format_issues = []
        for command in commands_to_test:
            json_output = self.detector.capture_command_json_output(command, "json")

            if json_output is None:
                format_issues.append(f"{command} did not produce valid JSON output")
            elif not isinstance(json_output, list):
                format_issues.append(f"{command} should return JSON array, got {type(json_output)}")

        if format_issues:
            pytest.fail(f"BREAKING CHANGE DETECTED: JSON format issues: {format_issues}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])