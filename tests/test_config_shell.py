"""Unit tests for ConfigToolShell UI class.

Tests for the main interactive shell UI component,
testing command processing and user interaction.
"""

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, call
from contextlib import redirect_stdout, redirect_stderr

# We need to add the sz_tools directory to the path to import our modules
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell, parse_cli_args


class TestConfigToolShell(unittest.TestCase):
    """Test cases for ConfigToolShell class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config_manager = Mock()
        self.mock_display_formatter = Mock()

        # Set up default mock returns
        self.mock_display_formatter.format_success.return_value = "Success: test"
        self.mock_display_formatter.format_error.return_value = "Error: test"
        self.mock_display_formatter.format_warning.return_value = "Warning: test"
        self.mock_display_formatter.format_info.return_value = "Info: test"
        self.mock_display_formatter.format_help_topic.return_value = "Help: test"
        self.mock_display_formatter.colorize.return_value = "colored text"

        # Create shell instance
        self.shell = ConfigToolShell(
            self.mock_config_manager,
            self.mock_display_formatter,
            force_mode=False,
            hist_disable=True
        )

    def test_initialization(self):
        """Test ConfigToolShell initialization."""
        # Test normal initialization
        shell = ConfigToolShell(
            self.mock_config_manager,
            self.mock_display_formatter,
            force_mode=True,
            hist_disable=True
        )

        self.assertEqual(shell.config_manager, self.mock_config_manager)
        self.assertEqual(shell.display_formatter, self.mock_display_formatter)
        self.assertTrue(shell.force_mode)
        self.assertIsNotNone(shell.intro)
        self.assertIsNotNone(shell.prompt)

    def test_do_help_no_topic(self):
        """Test help command without specific topic."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_help("")

        output = fake_stdout.getvalue()
        self.mock_display_formatter.format_help_topic.assert_called_once()
        # Verify it shows general help
        call_args = self.mock_display_formatter.format_help_topic.call_args[0]
        self.assertEqual(call_args[0], "Commands")
        self.assertIn("COMMANDS AVAILABLE:", call_args[1])

    def test_do_help_specific_command(self):
        """Test help command with specific topic."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_help("getDefaultConfigID")

        self.mock_display_formatter.format_help_topic.assert_called_once()
        call_args = self.mock_display_formatter.format_help_topic.call_args[0]
        self.assertEqual(call_args[0], "getDefaultConfigID")

    def test_do_help_unknown_command(self):
        """Test help command with unknown topic."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_help("nonexistent_command")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Unknown command: nonexistent_command"
        )

    def test_do_quit(self):
        """Test quit command."""
        result = self.shell.do_quit("")
        self.assertTrue(result)
        self.mock_display_formatter.format_info.assert_called_once_with("Goodbye!")

    def test_do_exit(self):
        """Test exit command."""
        result = self.shell.do_exit("")
        self.assertTrue(result)
        self.mock_display_formatter.format_info.assert_called_once_with("Goodbye!")

    def test_do_getDefaultConfigID_success(self):
        """Test getDefaultConfigID command with successful result."""
        self.mock_config_manager.get_default_config_id.return_value = 42

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_getDefaultConfigID("")

        self.mock_config_manager.get_default_config_id.assert_called_once()
        self.mock_display_formatter.format_success.assert_called_once_with(
            "Default configuration ID: 42"
        )

    def test_do_getDefaultConfigID_failure(self):
        """Test getDefaultConfigID command with failure."""
        self.mock_config_manager.get_default_config_id.return_value = None

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_getDefaultConfigID("")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Unable to retrieve default configuration ID"
        )

    def test_do_getConfigRegistry_success(self):
        """Test getConfigRegistry command with successful result."""
        test_registry = '{"CONFIGS": [{"CONFIG_ID": 1}]}'
        self.mock_config_manager.get_config_registry.return_value = test_registry

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_getConfigRegistry("")

        self.mock_config_manager.get_config_registry.assert_called_once()
        self.mock_display_formatter.format_config_registry.assert_called_once_with(test_registry)

    def test_do_getConfigRegistry_failure(self):
        """Test getConfigRegistry command with failure."""
        self.mock_config_manager.get_config_registry.return_value = None

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_getConfigRegistry("")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Unable to retrieve configuration registry"
        )

    def test_do_reload_config_default(self):
        """Test reload_config command without specifying ID."""
        self.mock_config_manager.load_config.return_value = True
        self.mock_config_manager.get_default_config_id.return_value = 5

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_reload_config("")

        self.mock_config_manager.load_config.assert_called_once_with(None)
        self.mock_display_formatter.format_success.assert_called_once()

    def test_do_reload_config_specific_id(self):
        """Test reload_config command with specific ID."""
        self.mock_config_manager.load_config.return_value = True

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_reload_config("123")

        self.mock_config_manager.load_config.assert_called_once_with(123)
        self.mock_display_formatter.format_success.assert_called_once_with(
            "Configuration 123 loaded successfully"
        )

    def test_do_reload_config_invalid_id(self):
        """Test reload_config command with invalid ID."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_reload_config("invalid")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Invalid configuration ID: invalid"
        )
        self.mock_config_manager.load_config.assert_not_called()

    def test_do_reload_config_failure(self):
        """Test reload_config command with load failure."""
        self.mock_config_manager.load_config.return_value = False

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_reload_config("123")

        self.mock_display_formatter.format_error.assert_called_once()

    def test_do_save_with_comment(self):
        """Test save command with comment."""
        self.mock_config_manager.save_config.return_value = 456

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_save("Test configuration update")

        self.mock_config_manager.save_config.assert_called_once_with("Test configuration update")
        self.mock_display_formatter.format_success.assert_called_once_with(
            "Configuration saved with ID: 456"
        )

    def test_do_save_without_comment(self):
        """Test save command without comment."""
        self.mock_config_manager.save_config.return_value = 789

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_save("")

        self.mock_config_manager.save_config.assert_called_once_with("Updated by sz_configtool")

    def test_do_save_failure(self):
        """Test save command with failure."""
        self.mock_config_manager.save_config.return_value = None

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_save("Test comment")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Failed to save configuration"
        )

    def test_do_exportToFile_success(self):
        """Test exportToFile command with success."""
        self.mock_config_manager.export_config_to_file.return_value = True

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_exportToFile("/tmp/test_config.json")

        self.mock_config_manager.export_config_to_file.assert_called_once_with("/tmp/test_config.json")
        self.mock_display_formatter.format_success.assert_called_once()

    def test_do_exportToFile_no_filename(self):
        """Test exportToFile command without filename."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_exportToFile("")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Filename is required"
        )
        self.mock_config_manager.export_config_to_file.assert_not_called()

    def test_do_exportToFile_failure(self):
        """Test exportToFile command with failure."""
        self.mock_config_manager.export_config_to_file.return_value = False

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_exportToFile("/tmp/test.json")

        self.mock_display_formatter.format_error.assert_called_once()

    def test_do_importFromFile_success(self):
        """Test importFromFile command with success."""
        self.mock_config_manager.import_config_from_file.return_value = True

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_importFromFile("/tmp/test_config.json")

        self.mock_config_manager.import_config_from_file.assert_called_once_with("/tmp/test_config.json")
        self.mock_display_formatter.format_success.assert_called_once()

    def test_do_importFromFile_no_filename(self):
        """Test importFromFile command without filename."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_importFromFile("")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Filename is required"
        )
        self.mock_config_manager.import_config_from_file.assert_not_called()

    def test_do_listDataSources_success(self):
        """Test listDataSources command with data."""
        test_sources = [{"DSRC_ID": 1, "DSRC_CODE": "TEST"}]
        self.mock_config_manager.get_data_sources.return_value = test_sources

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_listDataSources("")

        self.mock_config_manager.get_data_sources.assert_called_once()
        self.mock_display_formatter.format_data_sources.assert_called_once_with(test_sources)

    def test_do_listDataSources_failure(self):
        """Test listDataSources command with failure."""
        self.mock_config_manager.get_data_sources.return_value = None

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_listDataSources("")

        self.mock_display_formatter.format_info.assert_called_once_with(
            "No data sources found"
        )

    def test_do_addDataSource_success(self):
        """Test addDataSource command with success."""
        self.mock_config_manager.add_data_source.return_value = True

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_addDataSource("NEW_SOURCE")

        self.mock_config_manager.add_data_source.assert_called_once_with("NEW_SOURCE")
        self.mock_display_formatter.format_success.assert_called_once()

    def test_do_addDataSource_no_code(self):
        """Test addDataSource command without code."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_addDataSource("")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Data source code is required"
        )
        self.mock_config_manager.add_data_source.assert_not_called()

    def test_do_deleteDataSource_force_mode(self):
        """Test deleteDataSource command in force mode."""
        shell = ConfigToolShell(
            self.mock_config_manager,
            self.mock_display_formatter,
            force_mode=True,
            hist_disable=True
        )
        self.mock_config_manager.delete_data_source.return_value = True

        with redirect_stdout(io.StringIO()) as fake_stdout:
            shell.do_deleteDataSource("OLD_SOURCE")

        self.mock_config_manager.delete_data_source.assert_called_once_with("OLD_SOURCE")
        self.mock_display_formatter.format_success.assert_called_once()

    def test_do_deleteDataSource_interactive_yes(self):
        """Test deleteDataSource command with interactive confirmation (yes)."""
        self.mock_config_manager.delete_data_source.return_value = True

        with patch('builtins.input', return_value='yes'):
            with redirect_stdout(io.StringIO()) as fake_stdout:
                self.shell.do_deleteDataSource("OLD_SOURCE")

        self.mock_config_manager.delete_data_source.assert_called_once_with("OLD_SOURCE")

    def test_do_deleteDataSource_interactive_no(self):
        """Test deleteDataSource command with interactive confirmation (no)."""
        with patch('builtins.input', return_value='no'):
            with redirect_stdout(io.StringIO()) as fake_stdout:
                self.shell.do_deleteDataSource("OLD_SOURCE")

        self.mock_config_manager.delete_data_source.assert_not_called()
        self.mock_display_formatter.format_info.assert_called_once_with("Deletion cancelled")

    def test_do_deleteDataSource_no_code(self):
        """Test deleteDataSource command without code."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_deleteDataSource("")

        self.mock_display_formatter.format_error.assert_called_once_with(
            "Data source code is required"
        )
        self.mock_config_manager.delete_data_source.assert_not_called()

    def test_do_setTheme_enable_colors(self):
        """Test setTheme command to enable colors."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_setTheme("color")

        self.mock_display_formatter.use_colors = True
        self.mock_display_formatter.format_success.assert_called_once_with(
            "Colored output enabled"
        )

    def test_do_setTheme_disable_colors(self):
        """Test setTheme command to disable colors."""
        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_setTheme("nocolor")

        self.assertFalse(self.mock_display_formatter.use_colors)

    def test_do_setTheme_show_current(self):
        """Test setTheme command to show current theme."""
        self.mock_display_formatter.use_colors = True

        with redirect_stdout(io.StringIO()) as fake_stdout:
            self.shell.do_setTheme("invalid")

        self.mock_display_formatter.format_info.assert_called_once()

    def test_onecmd_keyboard_interrupt(self):
        """Test onecmd handling of keyboard interrupt."""
        with patch.object(self.shell, 'default') as mock_default:
            mock_default.side_effect = KeyboardInterrupt()

            with redirect_stdout(io.StringIO()) as fake_stdout:
                result = self.shell.onecmd("test")

            self.assertFalse(result)
            self.mock_display_formatter.format_info.assert_called_once()

    def test_onecmd_unexpected_error(self):
        """Test onecmd handling of unexpected errors."""
        with patch.object(self.shell, 'default') as mock_default:
            mock_default.side_effect = RuntimeError("Test error")

            with redirect_stdout(io.StringIO()) as fake_stdout:
                result = self.shell.onecmd("test")

            self.assertFalse(result)
            self.mock_display_formatter.format_error.assert_called_once()

    def test_emptyline(self):
        """Test emptyline behavior."""
        result = self.shell.emptyline()
        self.assertFalse(result)


class TestParseCliArgs(unittest.TestCase):
    """Test cases for parse_cli_args function."""

    def test_parse_cli_args_defaults(self):
        """Test parsing with default arguments."""
        with patch('sys.argv', ['sz_configtool_refactored']):
            args = parse_cli_args()

        self.assertIsNone(args.file_to_process)
        self.assertIsNone(args.ini_file_name)
        self.assertFalse(args.force_mode)
        self.assertFalse(args.hist_disable)
        self.assertFalse(args.no_color)

    def test_parse_cli_args_all_options(self):
        """Test parsing with all options specified."""
        test_args = [
            'sz_configtool_refactored',
            'commands.txt',
            '-c', 'test.ini',
            '-f',
            '-H',
            '--no-color'
        ]

        with patch('sys.argv', test_args):
            args = parse_cli_args()

        self.assertEqual(args.file_to_process, 'commands.txt')
        self.assertEqual(args.ini_file_name, 'test.ini')
        self.assertTrue(args.force_mode)
        self.assertTrue(args.hist_disable)
        self.assertTrue(args.no_color)

    def test_parse_cli_args_long_options(self):
        """Test parsing with long option names."""
        test_args = [
            'sz_configtool_refactored',
            '--ini-file-name', 'config.ini',
            '--force',
            '--hist_disable'
        ]

        with patch('sys.argv', test_args):
            args = parse_cli_args()

        self.assertEqual(args.ini_file_name, 'config.ini')
        self.assertTrue(args.force_mode)
        self.assertTrue(args.hist_disable)


if __name__ == '__main__':
    unittest.main()