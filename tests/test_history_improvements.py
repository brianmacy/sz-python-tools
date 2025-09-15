"""Tests for history improvements: history limit and disable functionality."""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter
from configtool_main import ConfigToolShell, parse_cli_args


class TestHistoryImprovements:
    """Test history limit and disable functionality."""

    def test_history_disabled_by_argument(self):
        """Test that history is disabled when hist_disable flag is True."""
        config_manager = Mock()
        display_formatter = Mock()

        shell = ConfigToolShell(
            config_manager,
            display_formatter,
            force_mode=False,
            hist_disable=True
        )

        assert shell.hist_disable is True

    def test_history_enabled_by_default(self):
        """Test that history is enabled by default."""
        config_manager = Mock()
        display_formatter = Mock()

        shell = ConfigToolShell(
            config_manager,
            display_formatter,
            force_mode=False,
            hist_disable=False
        )

        assert shell.hist_disable is False

    @patch('configtool_main.readline')
    @patch('configtool_main.history_setup')
    def test_history_setup_not_called_when_disabled(self, mock_history_setup, mock_readline):
        """Test that history_setup is not called when history is disabled."""
        mock_readline.__bool__ = lambda x: True  # Mock readline as available
        config_manager = Mock()
        display_formatter = Mock()

        shell = ConfigToolShell(
            config_manager,
            display_formatter,
            force_mode=False,
            hist_disable=True
        )

        # history_setup should not have been called
        mock_history_setup.assert_not_called()

    @patch('configtool_main.readline')
    @patch('configtool_main.history_setup')
    def test_history_setup_called_when_enabled(self, mock_history_setup, mock_readline):
        """Test that history_setup is called when history is enabled."""
        mock_readline.__bool__ = lambda x: True  # Mock readline as available
        config_manager = Mock()
        display_formatter = Mock()

        shell = ConfigToolShell(
            config_manager,
            display_formatter,
            force_mode=False,
            hist_disable=False
        )

        # history_setup should have been called
        mock_history_setup.assert_called_once()

    def test_history_command_shows_disabled_message(self):
        """Test that history command shows disabled message when history is disabled."""
        config_manager = Mock()
        display_formatter = Mock()
        display_formatter.format_info.return_value = "Command history is disabled"

        shell = ConfigToolShell(
            config_manager,
            display_formatter,
            force_mode=False,
            hist_disable=True
        )

        # Call history command
        shell.do_history("")

        # Should have called format_info with disabled message
        display_formatter.format_info.assert_called_with("Command history is disabled")

    @patch('configtool_main.readline')
    def test_history_command_shows_entries_when_enabled(self, mock_readline):
        """Test that history command shows entries when enabled."""
        config_manager = Mock()
        display_formatter = Mock()
        display_formatter.format_info.return_value = "History info"

        # Mock readline history
        mock_readline.__bool__ = lambda x: True
        mock_readline.get_current_history_length.return_value = 5
        mock_readline.get_history_item.side_effect = lambda i: f"command_{i}"

        shell = ConfigToolShell(
            config_manager,
            display_formatter,
            force_mode=False,
            hist_disable=False
        )

        with patch('builtins.print') as mock_print:
            shell.do_history("")

            # Should show history info - check that it was called with the expected message
            calls = display_formatter.format_info.call_args_list
            history_info_call = [call for call in calls if "Command history" in str(call)]
            assert len(history_info_call) > 0, "Expected history info call not found"

    def test_cli_args_include_hist_disable(self):
        """Test that command line arguments include hist_disable."""
        with patch('sys.argv', ['configtool_main.py', '-H']):
            args = parse_cli_args()
            assert args.hist_disable is True

        with patch('sys.argv', ['configtool_main.py']):
            args = parse_cli_args()
            assert args.hist_disable is False

    @patch('_tool_helpers.readline', create=True)
    @patch('_tool_helpers.atexit', create=True)
    def test_history_setup_with_limit(self, mock_atexit, mock_readline):
        """Test that history_setup applies history limit."""
        from _tool_helpers import history_setup

        # Mock readline being available
        mock_readline.__bool__ = lambda x: True
        mock_readline.get_current_history_length.return_value = 1500  # Exceeds limit
        mock_readline.get_history_item.side_effect = lambda i: f"command_{i}"
        mock_readline.read_history_file = Mock()
        mock_readline.clear_history = Mock()
        mock_readline.add_history = Mock()

        # Mock file operations
        with patch('_tool_helpers.open', create=True) as mock_open:
            with patch('_tool_helpers.Path.exists', return_value=True):
                mock_open.return_value.__enter__ = Mock(return_value=mock_open)
                mock_open.return_value.__exit__ = Mock(return_value=None)

                # Test with default limit (1000)
                result = history_setup("test_module")

                # Should have read the history file
                mock_readline.read_history_file.assert_called_once()

                # Should have cleared and re-added history due to limit
                mock_readline.clear_history.assert_called_once()

                # Should have added 1000 entries (the limit)
                assert mock_readline.add_history.call_count == 1000

                # Should have registered the write function with the limit
                mock_atexit.register.assert_called_once()

    @patch('_tool_helpers.readline', create=True)
    def test_history_write_file_with_limit(self, mock_readline):
        """Test that history_write_file applies history limit."""
        from _tool_helpers import history_write_file

        # Mock readline with too many entries
        mock_readline.get_current_history_length.return_value = 1200
        mock_readline.get_history_item.side_effect = lambda i: f"command_{i}"
        mock_readline.clear_history = Mock()
        mock_readline.add_history = Mock()
        mock_readline.write_history_file = Mock()

        # Create a mock file path
        mock_file = Mock(spec=Path)

        # Test write with limit
        history_write_file(mock_file, max_history=1000)

        # Should have cleared and re-added limited history
        mock_readline.clear_history.assert_called_once()
        assert mock_readline.add_history.call_count == 1000

        # Should have written the file
        mock_readline.write_history_file.assert_called_once_with(mock_file)

    @patch('_tool_helpers.readline', create=True)
    def test_history_write_file_no_limit_needed(self, mock_readline):
        """Test that history_write_file filters and deduplicates even when under max."""
        from _tool_helpers import history_write_file

        # Mock readline with fewer entries than limit
        mock_readline.get_current_history_length.return_value = 500
        mock_readline.get_history_item.side_effect = lambda i: f"valid_command_{i}"
        mock_readline.clear_history = Mock()
        mock_readline.add_history = Mock()
        mock_readline.write_history_file = Mock()

        # Create a mock file path
        mock_file = Mock(spec=Path)

        # Test write with limit
        history_write_file(mock_file, max_history=1000)

        # Should ALWAYS clear and re-add history for filtering/deduplication
        mock_readline.clear_history.assert_called_once()
        # Should add back the same number of entries since under limit
        assert mock_readline.add_history.call_count == 500

        # Should have written the file
        mock_readline.write_history_file.assert_called_once_with(mock_file)


if __name__ == "__main__":
    # Run the history improvement tests
    pytest.main([__file__, "-v", "--tb=short"])