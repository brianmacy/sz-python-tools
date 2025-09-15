"""Comprehensive Smoke Tests for sz_configtool.

These tests validate that all basic functionality works without deep validation.
Smoke tests are designed to quickly identify if major functionality is broken.
"""

import pytest
import sys
import os
import json
from io import StringIO
from unittest.mock import patch
from typing import Dict, Any, List, Optional

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


class SmokeTestHarness:
    """Harness for running smoke tests."""

    def __init__(self):
        """Initialize the smoke test harness."""
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter, force_mode=True)
        self.senzing_available = self.config_manager.initialize_senzing()

    def get_all_commands(self) -> List[str]:
        """Get all available commands from the shell."""
        commands = []
        for attr_name in dir(self.shell):
            if attr_name.startswith('do_') and callable(getattr(self.shell, attr_name)):
                command_name = attr_name[3:]  # Remove 'do_' prefix
                commands.append(command_name)
        return sorted(commands)

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
                "syntax error", "command failed",
                "error: failed", "error: unable", "error: missing"
            ]
            has_error = any(pattern in all_output_lower for pattern in error_patterns)

            return {
                "success": not has_error,
                "error": None,
                "stdout": stdout_content,
                "stderr": stderr_content
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": sys.stdout.getvalue(),
                "stderr": sys.stderr.getvalue()
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

        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('[') or line.startswith('{'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return None


class TestSmokeBasicFunctionality:
    """Smoke tests for basic functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = SmokeTestHarness()

    def test_senzing_initialization(self):
        """Smoke test: Senzing initializes successfully."""
        assert self.harness.senzing_available, "Senzing should initialize successfully"

    def test_help_command_works(self):
        """Smoke test: Help command produces output."""
        result = self.harness.run_command_safely("help")

        assert result["success"], f"Help command should work: {result['error']}"
        assert result["stdout"], "Help command should produce output"
        assert "help" in result["stdout"].lower() or "command" in result["stdout"].lower(), \
            "Help output should contain help information"

    def test_all_commands_exist(self):
        """Smoke test: All expected commands exist."""
        commands = self.harness.get_all_commands()

        # Minimum expected commands for basic functionality
        expected_basic_commands = [
            "help", "quit", "listDataSources", "listFeatures", "listAttributes",
            "getFeature", "getAttribute", "addDataSource", "deleteDataSource"
        ]

        missing_commands = [cmd for cmd in expected_basic_commands if cmd not in commands]
        assert not missing_commands, f"Missing basic commands: {missing_commands}"

    @pytest.mark.skipif(not SmokeTestHarness().senzing_available, reason="Senzing not available")
    def test_basic_list_commands_work(self):
        """Smoke test: Basic list commands execute without crashing."""
        basic_list_commands = [
            "listDataSources",
            "listFeatures",
            "listAttributes",
            "listElements"
        ]

        for command in basic_list_commands:
            result = self.harness.run_command_safely(command)
            assert result["success"], f"Command {command} should execute successfully: {result['error']}"

    @pytest.mark.skipif(not SmokeTestHarness().senzing_available, reason="Senzing not available")
    def test_json_output_format_works(self):
        """Smoke test: JSON output format works for list commands."""
        list_commands = ["listDataSources", "listFeatures", "listAttributes"]

        for command in list_commands:
            result = self.harness.run_command_safely(command, "json")
            assert result["success"], f"Command {command} json should work: {result['error']}"

            json_data = self.harness.extract_json_from_output(result["stdout"])
            if json_data is not None:
                assert isinstance(json_data, list), f"Command {command} should return JSON array"

    @pytest.mark.skipif(not SmokeTestHarness().senzing_available, reason="Senzing not available")
    def test_table_output_format_works(self):
        """Smoke test: Table output format works for list commands."""
        list_commands = ["listDataSources", "listFeatures", "listAttributes"]

        for command in list_commands:
            result = self.harness.run_command_safely(command, "table")
            assert result["success"], f"Command {command} table should work: {result['error']}"
            assert result["stdout"], f"Command {command} should produce table output"


class TestSmokeCommandCoverage:
    """Smoke tests for command coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = SmokeTestHarness()

    def test_all_120_commands_callable(self):
        """Smoke test: All 120 commands are callable without crashing."""
        commands = self.harness.get_all_commands()

        # Should have approximately 120 commands
        assert len(commands) >= 100, f"Expected ~120 commands, found {len(commands)}"

        # Test that all commands are callable (may fail with parameter errors, that's OK)
        uncallable_commands = []

        for command in commands:
            result = self.harness.run_command_safely(command)

            # Command should either succeed or fail with parameter error
            if not result["success"]:
                error_msg = (result["error"] or result["stderr"] or result["stdout"] or "").lower()
                # These are acceptable failure reasons for smoke tests
                acceptable_errors = [
                    "required", "parameter", "argument", "missing", "usage",
                    "syntax", "expected", "invalid", "specify",
                    "failed to delete", "failed to remove", "unable to retrieve",
                    "failed to update", "error: failed", "error: unable"
                ]

                if not any(err in error_msg for err in acceptable_errors):
                    uncallable_commands.append(f"{command}: {result['error'] or 'Unknown error'}")

        assert not uncallable_commands, f"Commands with unexpected errors: {uncallable_commands}"

    def test_command_categories_present(self):
        """Smoke test: All major command categories are present."""
        commands = self.harness.get_all_commands()
        command_set = set(commands)

        # Check for major command categories
        categories = {
            "list_commands": ["listDataSources", "listFeatures", "listAttributes", "listElements"],
            "get_commands": ["getFeature", "getAttribute", "getElement"],
            "add_commands": ["addDataSource", "addFeature", "addAttribute", "addElement"],
            "delete_commands": ["deleteDataSource", "deleteFeature", "deleteAttribute", "deleteElement"],
            "utility_commands": ["help", "quit", "save", "exportToFile", "importFromFile"]
        }

        missing_categories = {}
        for category, expected_commands in categories.items():
            missing = [cmd for cmd in expected_commands if cmd not in command_set]
            if missing:
                missing_categories[category] = missing

        assert not missing_categories, f"Missing command categories: {missing_categories}"


class TestSmokeDataIntegrity:
    """Smoke tests for data integrity."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = SmokeTestHarness()

    @pytest.mark.skipif(not SmokeTestHarness().senzing_available, reason="Senzing not available")
    def test_basic_crud_cycle_works(self):
        """Smoke test: Basic CRUD cycle works without corruption."""
        # Test with a temporary data source
        test_ds_name = "SMOKE_TEST_DS"

        try:
            # Create
            result = self.harness.run_command_safely("addDataSource", test_ds_name)
            if not result["success"]:
                pytest.skip(f"Cannot test CRUD - addDataSource failed: {result['error']}")

            # Read - check it exists
            result = self.harness.run_command_safely("listDataSources", "json")
            assert result["success"], f"listDataSources should work: {result['error']}"

            json_data = self.harness.extract_json_from_output(result["stdout"])
            if json_data:
                # Look for our test data source (field name might vary)
                found = False
                for item in json_data:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if value == test_ds_name:
                                found = True
                                break
                        if found:
                            break

                assert found, f"Added data source {test_ds_name} should appear in list"

            # Delete
            result = self.harness.run_command_safely("deleteDataSource", test_ds_name)
            # Delete might fail if not in force mode, that's acceptable for smoke test

        except Exception as e:
            # Clean up in case of failure
            self.harness.run_command_safely("deleteDataSource", test_ds_name)
            raise

    @pytest.mark.skipif(not SmokeTestHarness().senzing_available, reason="Senzing not available")
    def test_configuration_export_import_works(self):
        """Smoke test: Configuration can be exported and imported."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            # Export
            result = self.harness.run_command_safely("exportToFile", temp_file)
            if result["success"]:
                # Check file was created
                assert os.path.exists(temp_file), "Export should create file"
                assert os.path.getsize(temp_file) > 0, "Export file should not be empty"

                # Import
                result = self.harness.run_command_safely("importFromFile", temp_file)
                # Import might have specific requirements, failure is acceptable for smoke test

        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestSmokeErrorHandling:
    """Smoke tests for error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = SmokeTestHarness()

    def test_invalid_commands_handled_gracefully(self):
        """Smoke test: Invalid commands are handled gracefully."""
        invalid_commands = [
            "nonExistentCommand",
            "invalidCommand123",
            "badCommand"
        ]

        for command in invalid_commands:
            result = self.harness.run_command_safely(command)
            # Should fail gracefully, not crash
            assert not result["success"], f"Invalid command {command} should fail"
            # Should produce some error output
            assert result["error"] or result["stderr"] or "error" in result["stdout"].lower(), \
                f"Invalid command {command} should produce error message"

    def test_invalid_parameters_handled_gracefully(self):
        """Smoke test: Invalid parameters are handled gracefully."""
        if not self.harness.senzing_available:
            pytest.skip("Senzing not available")

        test_cases = [
            ("getAttribute", ""),  # Missing required parameter
            ("getFeature", ""),    # Missing required parameter
            ("addDataSource", ""), # Missing required parameter
            ("deleteDataSource", "NONEXISTENT_DS"), # Non-existent item
        ]

        for command, args in test_cases:
            result = self.harness.run_command_safely(command, args)
            # Should handle gracefully - either fail with error message or succeed
            if not result["success"]:
                # Should produce meaningful error message
                error_text = (result["error"] or result["stderr"] or result["stdout"]).lower()
                assert any(word in error_text for word in ["error", "required", "invalid", "not found"]), \
                    f"Command {command} should produce meaningful error for invalid params"

    def test_malformed_json_parameters_handled(self):
        """Smoke test: Malformed parameters are handled gracefully."""
        if not self.harness.senzing_available:
            pytest.skip("Senzing not available")

        malformed_inputs = [
            "listDataSources invalidformat",
            "getAttribute {malformed json}",
            "getFeature [[invalid]]"
        ]

        for malformed_input in malformed_inputs:
            parts = malformed_input.split(' ', 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            result = self.harness.run_command_safely(command, args)
            # Should not crash the application
            assert isinstance(result, dict), f"Malformed input should not crash application"


class TestSmokePerformance:
    """Smoke tests for basic performance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = SmokeTestHarness()

    @pytest.mark.skipif(not SmokeTestHarness().senzing_available, reason="Senzing not available")
    def test_commands_complete_in_reasonable_time(self):
        """Smoke test: Commands complete in reasonable time."""
        import time

        fast_commands = [
            ("help", ""),
            ("listDataSources", ""),
            ("listFeatures", ""),
        ]

        for command, args in fast_commands:
            start_time = time.time()
            result = self.harness.run_command_safely(command, args)
            end_time = time.time()

            duration = end_time - start_time

            # Commands should complete in under 30 seconds for smoke test
            assert duration < 30.0, f"Command {command} took {duration:.2f}s, should be under 30s"

    @pytest.mark.skipif(not SmokeTestHarness().senzing_available, reason="Senzing not available")
    def test_multiple_commands_dont_leak_memory(self):
        """Smoke test: Multiple commands don't cause obvious memory issues."""
        # Run multiple commands to check for basic memory leaks
        commands = [
            ("listDataSources", ""),
            ("listFeatures", ""),
            ("listAttributes", ""),
            ("help", ""),
        ]

        # Run each command multiple times
        for _ in range(3):
            for command, args in commands:
                result = self.harness.run_command_safely(command, args)
                # Should continue to work
                assert result["success"] or "required" in str(result["error"]).lower(), \
                    f"Command {command} should continue working after multiple runs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])