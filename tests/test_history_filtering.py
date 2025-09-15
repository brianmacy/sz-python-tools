"""Tests for enhanced history filtering functionality."""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _tool_helpers import _should_keep_history_item, _deduplicate_history


class TestHistoryFiltering:
    """Test enhanced history filtering functionality."""

    def test_should_keep_valid_commands(self):
        """Test that valid commands are kept."""
        valid_commands = [
            "listRules",
            "getFeature TEST_FEATURE",
            "addDataSource '{\"DSRC_CODE\": \"TEST\"}'",
            "listFragments json",
            "exportToFile config.json",
            "custom_command_123"
        ]

        for command in valid_commands:
            assert _should_keep_history_item(command), f"Valid command should be kept: {command}"

    def test_should_filter_quit_commands(self):
        """Test that quit commands are filtered out."""
        quit_commands = ["quit", "exit", "q", "QUIT", "Exit", "Q"]

        for command in quit_commands:
            assert not _should_keep_history_item(command), f"Quit command should be filtered: {command}"

    def test_should_filter_help_commands(self):
        """Test that help commands are filtered out."""
        help_commands = ["help", "h", "Help", "HELP", "help listRules", "help getFeature"]

        for command in help_commands:
            assert not _should_keep_history_item(command), f"Help command should be filtered: {command}"

    def test_should_filter_yn_responses(self):
        """Test that y/n responses are filtered out."""
        yn_responses = ["y", "yes", "n", "no", "Y", "Yes", "N", "No", "YES", "NO"]

        for response in yn_responses:
            assert not _should_keep_history_item(response), f"Y/N response should be filtered: {response}"

    def test_should_filter_invalid_commands(self):
        """Test that invalid command patterns are filtered out."""
        invalid_commands = [
            "*** Unknown syntax: invalid_command",
            "error: command failed",
            "unknown command",
            "invalid syntax",
            "command not found",
            "no such command",
            "bash: command not found",
            "sh: invalid",
            "-bash: test: command not found",
            "zsh: command not found",
            "?invalid",
            "***ERROR***",
        ]

        for command in invalid_commands:
            assert not _should_keep_history_item(command), f"Invalid command should be filtered: {command}"

    def test_should_filter_shell_commands(self):
        """Test that shell commands are filtered out."""
        shell_commands = [
            "ls -la",
            "cd /path",
            "pwd",
            "cat file.txt",
            "grep pattern",
            "find . -name",
            "ps aux",
            "top",
            "htop"
        ]

        for command in shell_commands:
            assert not _should_keep_history_item(command), f"Shell command should be filtered: {command}"

    def test_should_filter_short_typos(self):
        """Test that short likely typos are filtered out."""
        short_typos = ["x", "z", "aa", "bb", "cc", "dd", "ff"]

        for typo in short_typos:
            assert not _should_keep_history_item(typo), f"Short typo should be filtered: {typo}"

    def test_should_keep_short_commands_with_args(self):
        """Test that short commands with arguments are kept."""
        short_with_args = ["x 123", "z test", "aa param"]

        for command in short_with_args:
            assert _should_keep_history_item(command), f"Short command with args should be kept: {command}"

    def test_should_filter_empty_commands(self):
        """Test that empty or whitespace-only commands are filtered."""
        empty_commands = ["", "   ", "\t", "\n", "  \t  \n  "]

        for command in empty_commands:
            assert not _should_keep_history_item(command), f"Empty command should be filtered: '{command}'"

    def test_deduplicate_history_keeps_most_recent(self):
        """Test that deduplication keeps the most recent instance."""
        history_items = [
            "listRules",
            "getFeature TEST",
            "listRules",  # Duplicate
            "addDataSource TEST",
            "getFeature TEST",  # Duplicate
            "listFragments",
            "listRules",  # Another duplicate
        ]

        result = _deduplicate_history(history_items)

        # Should keep only unique items in original order (most recent)
        expected = [
            "addDataSource TEST",
            "getFeature TEST",
            "listFragments",
            "listRules"
        ]

        assert result == expected, f"Expected {expected}, got {result}"

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        result = _deduplicate_history([])
        assert result == []

    def test_deduplicate_single_item(self):
        """Test deduplication with single item."""
        result = _deduplicate_history(["listRules"])
        assert result == ["listRules"]

    def test_deduplicate_no_duplicates(self):
        """Test deduplication when no duplicates exist."""
        history_items = ["listRules", "getFeature", "addDataSource"]
        result = _deduplicate_history(history_items)
        assert result == history_items

    def test_case_sensitivity_in_filtering(self):
        """Test that filtering is case-insensitive where appropriate."""
        # These should be filtered regardless of case
        commands_to_filter = [
            ("QUIT", False),
            ("Help", False),
            ("YES", False),
            ("ERROR: test", False),
            ("LS -la", False)
        ]

        for command, should_keep in commands_to_filter:
            result = _should_keep_history_item(command)
            assert result == should_keep, f"Command '{command}' filtering result should be {should_keep}"

    def test_complex_valid_commands(self):
        """Test that complex but valid commands are kept."""
        complex_commands = [
            "addFeature '{\"FTYPE_CODE\": \"TEST_FEATURE\", \"FTYPE_DESC\": \"Test Feature\"}'",
            "setRule 123 '{\"RESOLVE\": \"Yes\", \"RELATE\": \"No\"}'",
            "listGenericThresholds jsonl",
            "exportConfig /tmp/config.json",
            "deleteDataSource CONFIRM_DELETE",
        ]

        for command in complex_commands:
            assert _should_keep_history_item(command), f"Complex valid command should be kept: {command}"


if __name__ == "__main__":
    # Run the history filtering tests
    pytest.main([__file__, "-v", "--tb=short"])