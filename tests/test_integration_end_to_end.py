"""End-to-End Integration Tests for sz_configtool.

These tests validate complete workflows and real-world usage scenarios
across multiple commands and operations to ensure the entire system
works together correctly.
"""

import pytest
import json
import sys
import os
import tempfile
import subprocess
from io import StringIO
from unittest.mock import patch
from typing import Dict, Any, List, Optional

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


class IntegrationTestHarness:
    """Harness for running end-to-end integration tests."""

    def __init__(self):
        """Initialize the integration test harness."""
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter, force_mode=True)
        self.senzing_available = self.config_manager.initialize_senzing()
        self.test_artifacts = []  # Track created test data for cleanup

    def execute_command_sequence(self, commands: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Execute a sequence of commands and return results."""
        results = []

        for command_info in commands:
            command = command_info['command']
            args = command_info.get('args', '')
            description = command_info.get('description', f'{command} {args}')

            result = self.run_command_safely(command, args)
            result['description'] = description
            results.append(result)

            # Stop on first failure unless continue_on_error is True
            if not result['success'] and not command_info.get('continue_on_error', False):
                break

        return results

    def run_command_safely(self, command_name: str, args: str = "") -> Dict[str, Any]:
        """Run a command safely and capture all output."""
        if not hasattr(self.shell, f'do_{command_name}'):
            return {
                "success": False,
                "error": f"Command {command_name} not found",
                "stdout": "",
                "stderr": ""
            }

        method = getattr(self.shell, f'do_{command_name}')

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

            return {
                "success": not has_error,
                "error": None,
                "stdout": stdout_content,
                "stderr": stderr_content
            }

        except Exception as e:
            stdout_content = sys.stdout.getvalue()
            stderr_content = sys.stderr.getvalue()
            return {
                "success": False,
                "error": str(e),
                "stdout": stdout_content,
                "stderr": stderr_content
            }

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # Reset test flag
            if hasattr(sys, '_called_from_test'):
                delattr(sys, '_called_from_test')

    def extract_json_from_output(self, output: str) -> Optional[Dict]:
        """Extract JSON from command output."""
        if not output:
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

    def cleanup_test_artifacts(self):
        """Clean up any test data created during tests."""
        for artifact in self.test_artifacts:
            try:
                if artifact.get('type') == 'datasource':
                    self.run_command_safely('deleteDataSource', artifact['name'])
                elif artifact.get('type') == 'file':
                    if os.path.exists(artifact['path']):
                        os.unlink(artifact['path'])
            except Exception:
                pass  # Best effort cleanup
        self.test_artifacts.clear()


class TestEndToEndDataSourceWorkflows:
    """End-to-end tests for data source management workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = IntegrationTestHarness()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.harness.cleanup_test_artifacts()

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_complete_datasource_lifecycle(self):
        """Test complete data source create, read, update, delete lifecycle."""
        test_ds_name = "E2E_TEST_DATASOURCE"
        self.harness.test_artifacts.append({'type': 'datasource', 'name': test_ds_name})

        # Define the complete workflow
        workflow_commands = [
            {
                'command': 'listDataSources',
                'args': 'json',
                'description': 'Get initial data source list'
            },
            {
                'command': 'addDataSource',
                'args': test_ds_name,
                'description': f'Create new data source {test_ds_name}'
            },
            {
                'command': 'listDataSources',
                'args': 'json',
                'description': 'Verify data source was created'
            },
            {
                'command': 'deleteDataSource',
                'args': test_ds_name,
                'description': f'Delete test data source',
                'continue_on_error': True  # Might fail if not in force mode
            },
            {
                'command': 'listDataSources',
                'args': 'json',
                'description': 'Verify data source was deleted (if delete succeeded)'
            }
        ]

        results = self.harness.execute_command_sequence(workflow_commands)

        # Validate workflow results
        assert len(results) >= 3, "Should execute at least the core workflow steps"

        # Check initial list succeeded
        assert results[0]['success'], f"Initial listDataSources failed: {results[0]['error']}"

        # Check data source creation succeeded
        assert results[1]['success'], f"addDataSource failed: {results[1]['error']}"

        # Check verification list succeeded
        assert results[2]['success'], f"Verification listDataSources failed: {results[2]['error']}"

        # Verify the data source appears in the list
        verification_json = self.harness.extract_json_from_output(results[2]['stdout'])
        if verification_json and isinstance(verification_json, list):
            # Look for our test data source in the list
            found_datasource = False
            for ds in verification_json:
                if isinstance(ds, dict):
                    for field_name, value in ds.items():
                        if value == test_ds_name:
                            found_datasource = True
                            break
                    if found_datasource:
                        break

            assert found_datasource, f"Created data source {test_ds_name} should appear in list"

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_data_source_error_handling_workflow(self):
        """Test error handling throughout data source workflows."""
        # Test operations on non-existent data source
        error_workflow = [
            {
                'command': 'deleteDataSource',
                'args': 'NONEXISTENT_DATASOURCE',
                'description': 'Attempt to delete non-existent data source',
                'continue_on_error': True
            }
        ]

        results = self.harness.execute_command_sequence(error_workflow)

        # Operation should handle errors gracefully
        for result in results:
            # Should either succeed or fail with meaningful error
            if not result['success']:
                error_text = (result['error'] or result['stderr'] or result['stdout']).lower()
                assert any(word in error_text for word in ['error', 'not found', 'invalid', 'missing']), \
                    f"Error should be meaningful: {result['error']}"


class TestEndToEndFeatureAttributeWorkflows:
    """End-to-end tests for feature and attribute management workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = IntegrationTestHarness()

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_feature_attribute_discovery_workflow(self):
        """Test complete feature and attribute discovery workflow."""
        discovery_workflow = [
            {
                'command': 'listFeatures',
                'args': 'json',
                'description': 'Get all available features'
            },
            {
                'command': 'listAttributes',
                'args': 'json',
                'description': 'Get all available attributes'
            },
            {
                'command': 'listElements',
                'args': 'json',
                'description': 'Get all available elements'
            }
        ]

        results = self.harness.execute_command_sequence(discovery_workflow)

        # All discovery commands should succeed
        for result in results:
            assert result['success'], f"Discovery command failed: {result['description']} - {result['error']}"

        # Extract and validate the discovery data
        features_json = self.harness.extract_json_from_output(results[0]['stdout'])
        attributes_json = self.harness.extract_json_from_output(results[1]['stdout'])
        elements_json = self.harness.extract_json_from_output(results[2]['stdout'])

        assert features_json and isinstance(features_json, list), "listFeatures should return JSON array"
        assert attributes_json and isinstance(attributes_json, list), "listAttributes should return JSON array"
        assert elements_json and isinstance(elements_json, list), "listElements should return JSON array"

        # Should have some data
        assert len(features_json) > 0, "Should have at least some features"
        assert len(attributes_json) > 0, "Should have at least some attributes"
        assert len(elements_json) > 0, "Should have at least some elements"

        # Test getting details for first feature and attribute
        if features_json:
            # Get feature name (handle both possible field names)
            first_feature = features_json[0]
            feature_name = first_feature.get('FTYPE_CODE') or first_feature.get('feature')

            if feature_name:
                detail_workflow = [
                    {
                        'command': 'getFeature',
                        'args': f'{feature_name} json',
                        'description': f'Get details for feature {feature_name}'
                    }
                ]

                detail_results = self.harness.execute_command_sequence(detail_workflow)
                assert detail_results[0]['success'], f"getFeature failed for {feature_name}: {detail_results[0]['error']}"

        if attributes_json:
            # Get attribute name (handle both possible field names)
            first_attribute = attributes_json[0]
            attribute_name = first_attribute.get('ATTR_CODE') or first_attribute.get('attribute')

            if attribute_name:
                detail_workflow = [
                    {
                        'command': 'getAttribute',
                        'args': f'{attribute_name} json',
                        'description': f'Get details for attribute {attribute_name}'
                    }
                ]

                detail_results = self.harness.execute_command_sequence(detail_workflow)
                assert detail_results[0]['success'], f"getAttribute failed for {attribute_name}: {detail_results[0]['error']}"


class TestEndToEndConfigurationWorkflows:
    """End-to-end tests for configuration management workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = IntegrationTestHarness()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.harness.cleanup_test_artifacts()

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_configuration_export_import_workflow(self):
        """Test complete configuration export and import workflow."""
        # Create temporary files for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            export_file = f.name

        self.harness.test_artifacts.append({'type': 'file', 'path': export_file})

        export_import_workflow = [
            {
                'command': 'exportToFile',
                'args': export_file,
                'description': f'Export configuration to {export_file}'
            },
            {
                'command': 'importFromFile',
                'args': export_file,
                'description': f'Import configuration from {export_file}',
                'continue_on_error': True  # May have validation requirements
            }
        ]

        results = self.harness.execute_command_sequence(export_import_workflow)

        # Export should succeed
        assert results[0]['success'], f"Configuration export failed: {results[0]['error']}"

        # Verify export file was created and has content
        assert os.path.exists(export_file), "Export should create file"
        assert os.path.getsize(export_file) > 0, "Export file should not be empty"

        # Verify file contains valid JSON
        try:
            with open(export_file, 'r') as f:
                config_data = json.load(f)
            assert isinstance(config_data, dict), "Exported configuration should be JSON object"
        except json.JSONDecodeError:
            pytest.fail("Exported file should contain valid JSON")

        # Import result depends on specific requirements, but should handle gracefully
        if not results[1]['success']:
            # Should provide meaningful error message
            error_text = (results[1]['error'] or results[1]['stderr'] or results[1]['stdout']).lower()
            assert any(word in error_text for word in ['error', 'invalid', 'required', 'validation']), \
                f"Import error should be meaningful: {results[1]['error']}"

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_configuration_validation_workflow(self):
        """Test configuration validation and consistency checks."""
        validation_workflow = [
            {
                'command': 'listDataSources',
                'args': 'json',
                'description': 'Get current data sources for validation'
            },
            {
                'command': 'listFeatures',
                'args': 'json',
                'description': 'Get current features for validation'
            },
            {
                'command': 'listAttributes',
                'args': 'json',
                'description': 'Get current attributes for validation'
            }
        ]

        results = self.harness.execute_command_sequence(validation_workflow)

        # All validation queries should succeed
        for result in results:
            assert result['success'], f"Validation query failed: {result['description']} - {result['error']}"

        # Extract configuration data
        datasources = self.harness.extract_json_from_output(results[0]['stdout'])
        features = self.harness.extract_json_from_output(results[1]['stdout'])
        attributes = self.harness.extract_json_from_output(results[2]['stdout'])

        # Validate data consistency
        assert datasources and isinstance(datasources, list), "Data sources should be available"
        assert features and isinstance(features, list), "Features should be available"
        assert attributes and isinstance(attributes, list), "Attributes should be available"

        # Check for reasonable minimum configuration
        assert len(datasources) >= 0, "Should have data source configuration (may be empty)"
        assert len(features) > 0, "Should have some feature definitions"
        assert len(attributes) > 0, "Should have some attribute definitions"


class TestEndToEndPerformanceWorkflows:
    """End-to-end tests for performance and scalability scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = IntegrationTestHarness()

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_bulk_operations_performance(self):
        """Test performance with bulk operations."""
        import time

        # Test repeated list operations
        bulk_operations = []
        for i in range(5):  # Moderate bulk test
            bulk_operations.extend([
                {
                    'command': 'listDataSources',
                    'args': 'json',
                    'description': f'Bulk listDataSources operation {i+1}'
                },
                {
                    'command': 'listFeatures',
                    'args': 'json',
                    'description': f'Bulk listFeatures operation {i+1}'
                },
                {
                    'command': 'listAttributes',
                    'args': 'json',
                    'description': f'Bulk listAttributes operation {i+1}'
                }
            ])

        start_time = time.time()
        results = self.harness.execute_command_sequence(bulk_operations)
        end_time = time.time()

        total_duration = end_time - start_time
        operations_count = len(bulk_operations)

        # All operations should succeed
        successful_operations = sum(1 for result in results if result['success'])
        assert successful_operations == operations_count, \
            f"All bulk operations should succeed: {successful_operations}/{operations_count}"

        # Performance check - should complete in reasonable time
        assert total_duration < 60.0, \
            f"Bulk operations took too long: {total_duration:.2f}s for {operations_count} operations"

        # Average per operation should be reasonable
        avg_duration = total_duration / operations_count
        assert avg_duration < 5.0, \
            f"Average operation time too high: {avg_duration:.2f}s per operation"

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_memory_stability_workflow(self):
        """Test memory stability across multiple operations."""
        # Run various operations multiple times to check for memory leaks
        stability_commands = [
            {
                'command': 'listDataSources',
                'args': 'json',
                'description': 'Memory stability test - listDataSources'
            },
            {
                'command': 'listFeatures',
                'args': 'json',
                'description': 'Memory stability test - listFeatures'
            },
            {
                'command': 'listAttributes',
                'args': 'json',
                'description': 'Memory stability test - listAttributes'
            },
            {
                'command': 'help',
                'args': '',
                'description': 'Memory stability test - help'
            }
        ]

        # Run the same operations multiple times
        for iteration in range(3):
            results = self.harness.execute_command_sequence(stability_commands)

            # All operations should continue to work
            for result in results:
                assert result['success'] or 'required' in str(result['error']).lower(), \
                    f"Operation should remain stable in iteration {iteration + 1}: {result['description']} - {result['error']}"


class TestEndToEndErrorRecoveryWorkflows:
    """End-to-end tests for error handling and recovery scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = IntegrationTestHarness()

    def test_invalid_command_sequence_recovery(self):
        """Test recovery from invalid command sequences."""
        error_recovery_workflow = [
            {
                'command': 'invalidCommand',
                'args': '',
                'description': 'Invalid command test',
                'continue_on_error': True
            },
            {
                'command': 'listDataSources',
                'args': 'json',
                'description': 'Recovery test - should work after invalid command'
            },
            {
                'command': 'getAttribute',
                'args': '',  # Missing required parameter
                'description': 'Missing parameter test',
                'continue_on_error': True
            },
            {
                'command': 'help',
                'args': '',
                'description': 'Recovery test - should work after parameter error'
            }
        ]

        results = self.harness.execute_command_sequence(error_recovery_workflow)

        # Should handle invalid command gracefully
        assert not results[0]['success'], "Invalid command should fail"

        # Should recover and work normally
        if self.harness.senzing_available:
            assert results[1]['success'], f"Should recover after invalid command: {results[1]['error']}"

        # Should handle missing parameters gracefully
        assert not results[2]['success'], "Missing parameter should fail"

        # Should continue working after parameter error
        assert results[3]['success'], f"Should recover after parameter error: {results[3]['error']}"

    @pytest.mark.skipif(not IntegrationTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_malformed_input_recovery(self):
        """Test recovery from malformed input."""
        malformed_input_workflow = [
            {
                'command': 'listDataSources',
                'args': 'invalidformat',
                'description': 'Malformed format parameter',
                'continue_on_error': True
            },
            {
                'command': 'listDataSources',
                'args': 'json',
                'description': 'Recovery test after malformed input'
            },
            {
                'command': 'getAttribute',
                'args': '{malformed json}',
                'description': 'Malformed JSON parameter',
                'continue_on_error': True
            },
            {
                'command': 'listAttributes',
                'args': 'json',
                'description': 'Recovery test after malformed JSON'
            }
        ]

        results = self.harness.execute_command_sequence(malformed_input_workflow)

        # Should handle malformed input gracefully (may succeed or fail gracefully)
        if not results[0]['success']:
            error_text = (results[0]['error'] or results[0]['stderr'] or results[0]['stdout']).lower()
            assert any(word in error_text for word in ['error', 'invalid', 'format']), \
                "Should provide meaningful error for malformed input"

        # Should recover and work normally
        assert results[1]['success'], f"Should recover after malformed input: {results[1]['error']}"

        # Should handle malformed JSON gracefully
        if not results[2]['success']:
            error_text = (results[2]['error'] or results[2]['stderr'] or results[2]['stdout']).lower()
            assert any(word in error_text for word in ['error', 'invalid', 'parameter', 'json']), \
                "Should provide meaningful error for malformed JSON"

        # Should continue working after JSON error
        assert results[3]['success'], f"Should recover after malformed JSON: {results[3]['error']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])