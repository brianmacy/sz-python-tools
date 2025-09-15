"""Integration tests for sz_configtool modules.

Tests for interactions between ConfigurationManager, ConfigDisplayFormatter,
and ConfigToolShell to ensure they work together correctly.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from contextlib import redirect_stdout

# Add the sz_tools directory to the path
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

# Mock senzing modules to avoid import errors
mock_senzing = Mock()
mock_senzing.SzError = Exception  # Use Exception as base for SzError
sys.modules['senzing'] = mock_senzing

mock_senzing_core = Mock()
mock_senzing_core.SzAbstractFactoryCore = Mock
sys.modules['senzing_core'] = mock_senzing_core


class TestModuleIntegration(unittest.TestCase):
    """Integration tests for module interactions."""

    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid issues with path setup
        from sz_tools._config_core import ConfigurationManager
        from sz_tools._config_display import ConfigDisplayFormatter
        from sz_tools.configtool_main import ConfigToolShell

        self.ConfigurationManager = ConfigurationManager
        self.ConfigDisplayFormatter = ConfigDisplayFormatter
        self.ConfigToolShell = ConfigToolShell

    def test_core_and_display_integration(self):
        """Test integration between core and display modules."""
        # Mock Senzing components to avoid external dependencies
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory:
            mock_config_mgr = Mock()
            mock_config = Mock()

            mock_factory.return_value.create_configmanager.return_value = mock_config_mgr
            mock_factory.return_value.create_config.return_value = mock_config

            # Set up mock returns
            mock_config_mgr.get_default_config_id.return_value = 42
            mock_config_mgr.get_configs.return_value = json.dumps({
                "CONFIGS": [
                    {"CONFIG_ID": 1, "CONFIG_COMMENT": "Initial", "SYS_CREATE_DT": "2023-01-01"},
                    {"CONFIG_ID": 2, "CONFIG_COMMENT": "Updated", "SYS_CREATE_DT": "2023-01-02"}
                ]
            })

            # Create instances
            config_manager = self.ConfigurationManager()
            display_formatter = self.ConfigDisplayFormatter(use_colors=False)

            # Test initialization
            self.assertTrue(config_manager.initialize_senzing())

            # Test core operation and display formatting
            config_id = config_manager.get_default_config_id()
            success_message = display_formatter.format_success(f"Default config ID: {config_id}")

            self.assertIn("Success:", success_message)
            self.assertIn("42", success_message)

            # Test registry retrieval and formatting
            registry_json = config_manager.get_config_registry()
            formatted_registry = display_formatter.format_config_registry(registry_json)

            self.assertIn("Configuration Registry", formatted_registry)
            self.assertIn("Initial", formatted_registry)
            self.assertIn("Updated", formatted_registry)

    def test_shell_with_mocked_dependencies(self):
        """Test ConfigToolShell with properly mocked dependencies."""
        mock_config_manager = Mock()
        mock_display_formatter = Mock()

        # Set up mock returns
        mock_config_manager.get_default_config_id.return_value = 123
        mock_display_formatter.format_success.return_value = "Success: Config ID 123"
        mock_display_formatter.colorize.return_value = "colored prompt"

        shell = self.ConfigToolShell(
            mock_config_manager,
            mock_display_formatter,
            force_mode=False
        )

        # Test command execution
        with redirect_stdout(StringIO()) as fake_stdout:
            shell.do_getDefaultConfigID("")

        output = fake_stdout.getvalue()

        # Verify interactions
        mock_config_manager.get_default_config_id.assert_called_once()
        mock_display_formatter.format_success.assert_called_once()

    def test_full_command_workflow(self):
        """Test a complete command workflow through all modules."""
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory:
            # Set up mocks
            mock_config_mgr = Mock()
            mock_config = Mock()

            mock_factory.return_value.create_configmanager.return_value = mock_config_mgr
            mock_factory.return_value.create_config.return_value = mock_config

            # Set up config manager mocks for initialization
            mock_config_mgr.get_default_config_id.return_value = 1
            mock_config_mgr.create_config_from_config_id.return_value = mock_config

            test_data_sources = [
                {"DSRC_ID": 1, "DSRC_CODE": "CUSTOMERS"},
                {"DSRC_ID": 2, "DSRC_CODE": "VENDORS"}
            ]

            test_config = {
                "G2_CONFIG": {
                    "CFG_DSRC": test_data_sources
                }
            }

            mock_config.export.return_value = json.dumps(test_config)  # export(), not export_config()
            mock_config_mgr.register_config.return_value = 456

            # Create instances
            config_manager = self.ConfigurationManager()
            display_formatter = self.ConfigDisplayFormatter(use_colors=False)
            shell = self.ConfigToolShell(config_manager, display_formatter)

            # Initialize
            config_manager.initialize_senzing()

            # Test workflow: list data sources
            with patch.object(display_formatter, 'print_with_paging') as mock_paging:
                shell.do_listDataSources("")

                # Get the output that would have been paged
                mock_paging.assert_called_once()
                call_args = mock_paging.call_args[0]
                output = call_args[0] if call_args else ""

            # Verify the full pipeline worked - export called during init and listDataSources
            self.assertEqual(mock_config.export.call_count, 2)  # Called during init and listDataSources
            self.assertIn("Data Sources", output)

    def test_error_propagation_through_modules(self):
        """Test how errors propagate through the module stack."""
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory:
            # Set up factory to fail
            mock_factory.side_effect = Exception("Senzing initialization failed")

            config_manager = self.ConfigurationManager()
            display_formatter = self.ConfigDisplayFormatter(use_colors=False)
            shell = self.ConfigToolShell(config_manager, display_formatter)

            # Test that initialization failure is handled
            result = config_manager.initialize_senzing()
            self.assertFalse(result)

            # Test that shell handles uninitialized manager gracefully
            with redirect_stdout(StringIO()) as fake_stdout:
                shell.do_getDefaultConfigID("")

            output = fake_stdout.getvalue()
            self.assertIn("Error:", output)

    def test_file_operations_integration(self):
        """Test file import/export operations through all modules."""
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory:
            mock_config_mgr = Mock()
            mock_config = Mock()
            mock_factory.return_value.create_config.return_value = mock_config
            mock_factory.return_value.create_configmanager.return_value = mock_config_mgr

            # Set up config manager mocks for initialization
            mock_config_mgr.get_default_config_id.return_value = 1
            mock_config_mgr.create_config_from_config_id.return_value = mock_config
            mock_config.import_config.return_value = None  # import_config doesn't return anything

            test_config_data = {
                "G2_CONFIG": {
                    "CFG_DSRC": [{"DSRC_ID": 1, "DSRC_CODE": "TEST"}]
                }
            }
            test_config_json = json.dumps(test_config_data, indent=2)

            # Set up export to return test data for load_config to work
            mock_config.export.return_value = test_config_json

            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(test_config_json)
                temp_file = f.name

            try:
                config_manager = self.ConfigurationManager()
                display_formatter = self.ConfigDisplayFormatter(use_colors=False)
                shell = self.ConfigToolShell(config_manager, display_formatter)

                config_manager.initialize_senzing()

                # Test import command
                with redirect_stdout(StringIO()) as fake_stdout:
                    shell.do_importFromFile(temp_file)

                output = fake_stdout.getvalue()

                # Verify import was attempted via import_config
                mock_config.import_config.assert_called_once_with(test_config_json)
                self.assertIn("Success:", output)

            finally:
                Path(temp_file).unlink()

    def test_data_source_management_workflow(self):
        """Test complete data source management workflow."""
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory:
            mock_config_mgr = Mock()
            mock_config = Mock()

            mock_factory.return_value.create_configmanager.return_value = mock_config_mgr
            mock_factory.return_value.create_config.return_value = mock_config

            # Set up config manager mocks for initialization
            mock_config_mgr.get_default_config_id.return_value = 1
            mock_config_mgr.create_config_from_config_id.return_value = mock_config
            mock_config_mgr.create_config_from_json.return_value = mock_config

            # Set up initial config data
            test_config_data = {
                "G2_CONFIG": {
                    "CFG_DSRC": [
                        {"DSRC_ID": 1, "DSRC_CODE": "ORIGINAL_SOURCE"}
                    ]
                }
            }

            # Use a dynamic export that reflects the current state
            def dynamic_export():
                return json.dumps(config_manager.config_data if hasattr(config_manager, 'config_data') and config_manager.config_data else test_config_data)

            mock_config.export.side_effect = dynamic_export

            config_manager = self.ConfigurationManager()
            display_formatter = self.ConfigDisplayFormatter(use_colors=False)
            shell = self.ConfigToolShell(config_manager, display_formatter, force_mode=True)

            config_manager.initialize_senzing()

            # Set up the config data for the modular approach
            config_manager.config_data = test_config_data

            # Test add data source
            with redirect_stdout(StringIO()) as fake_stdout:
                shell.do_addDataSource("NEW_SOURCE")

            add_output = fake_stdout.getvalue()
            self.assertIn("Success:", add_output)
            # Verify that the data source was added to the config data
            self.assertEqual(len(config_manager.config_data["G2_CONFIG"]["CFG_DSRC"]), 2)

            # Test list data sources
            with patch.object(display_formatter, 'print_with_paging') as mock_paging:
                shell.do_listDataSources("")

                # Get the output that would have been paged
                mock_paging.assert_called_once()
                call_args = mock_paging.call_args[0]
                list_output = call_args[0] if call_args else ""

            self.assertIn("NEW_SOURCE", list_output)
            self.assertIn("ORIGINAL_SOURCE", list_output)

            # Test delete data source (force mode, no confirmation)
            with redirect_stdout(StringIO()) as fake_stdout:
                shell.do_deleteDataSource("ORIGINAL_SOURCE")

            delete_output = fake_stdout.getvalue()
            self.assertIn("Success:", delete_output)
            # Verify that the data source was removed from config data
            remaining_sources = [ds["DSRC_CODE"] for ds in config_manager.config_data["G2_CONFIG"]["CFG_DSRC"]]
            self.assertNotIn("ORIGINAL_SOURCE", remaining_sources)

    def test_configuration_save_load_cycle(self):
        """Test complete configuration save/load cycle."""
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory:
            mock_config_mgr = Mock()
            mock_config = Mock()

            mock_factory.return_value.create_configmanager.return_value = mock_config_mgr
            mock_factory.return_value.create_config.return_value = mock_config

            # Set up save/load cycle
            mock_config.export.return_value = '{"test": "config"}'
            mock_config_mgr.register_config.return_value = 789
            mock_config_mgr.get_config.return_value = '{"saved": "config"}'
            mock_config_mgr.get_default_config_id.return_value = 1
            mock_config_mgr.create_config_from_config_id.return_value = mock_config

            config_manager = self.ConfigurationManager()
            display_formatter = self.ConfigDisplayFormatter(use_colors=False)
            shell = self.ConfigToolShell(config_manager, display_formatter)

            config_manager.initialize_senzing()

            # Test save configuration
            with redirect_stdout(StringIO()) as fake_stdout:
                shell.do_save("Integration test configuration")

            save_output = fake_stdout.getvalue()
            self.assertIn("Success:", save_output)
            self.assertIn("789", save_output)

            # Test load configuration
            with redirect_stdout(StringIO()) as fake_stdout:
                shell.do_reload_config("789")

            load_output = fake_stdout.getvalue()
            self.assertIn("Success:", load_output)
            self.assertIn("789", load_output)

    def test_theme_and_display_integration(self):
        """Test theme changes and display formatting integration."""
        mock_config_manager = Mock()
        display_formatter = self.ConfigDisplayFormatter(use_colors=True)
        shell = self.ConfigToolShell(mock_config_manager, display_formatter)

        # Test initial colored state
        self.assertTrue(display_formatter.use_colors)

        # Test theme change to no color
        with redirect_stdout(StringIO()) as fake_stdout:
            shell.do_setTheme("nocolor")

        output = fake_stdout.getvalue()
        self.assertFalse(display_formatter.use_colors)

        # Test theme change back to color
        with redirect_stdout(StringIO()) as fake_stdout:
            shell.do_setTheme("color")

        output = fake_stdout.getvalue()
        self.assertTrue(display_formatter.use_colors)

    def test_help_system_integration(self):
        """Test help system integration across modules."""
        mock_config_manager = Mock()
        mock_display_formatter = Mock()

        mock_display_formatter.format_help_topic.return_value = "Formatted help"

        shell = self.ConfigToolShell(mock_config_manager, mock_display_formatter)

        # Test general help
        with redirect_stdout(StringIO()) as fake_stdout:
            shell.do_help("")

        # Should call display formatter for help formatting
        mock_display_formatter.format_help_topic.assert_called_once()

        # Test specific command help
        mock_display_formatter.reset_mock()

        with redirect_stdout(StringIO()) as fake_stdout:
            shell.do_help("getDefaultConfigID")

        mock_display_formatter.format_help_topic.assert_called_once()

    def test_error_handling_integration(self):
        """Test error handling across all modules."""
        with patch('sz_tools._config_core.SzAbstractFactoryCore') as mock_factory:
            from senzing import SzError

            mock_config_mgr = Mock()
            mock_config = Mock()

            mock_factory.return_value.create_configmanager.return_value = mock_config_mgr
            mock_factory.return_value.create_config.return_value = mock_config

            # Set up to raise SzError
            mock_config_mgr.get_default_config_id.side_effect = SzError("Test error")

            config_manager = self.ConfigurationManager()
            display_formatter = self.ConfigDisplayFormatter(use_colors=False)
            shell = self.ConfigToolShell(config_manager, display_formatter)

            config_manager.initialize_senzing()

            # Test that SzError is handled and formatted properly
            with redirect_stdout(StringIO()) as fake_stdout:
                shell.do_getDefaultConfigID("")

            output = fake_stdout.getvalue()
            self.assertIn("Error:", output)

    def test_command_argument_validation_integration(self):
        """Test command argument validation across modules."""
        mock_config_manager = Mock()
        mock_display_formatter = Mock()

        mock_display_formatter.format_error.return_value = "Error: Invalid argument"

        shell = self.ConfigToolShell(mock_config_manager, mock_display_formatter)

        # Test commands that require arguments
        test_cases = [
            ("do_exportToFile", ""),
            ("do_importFromFile", ""),
            ("do_addDataSource", ""),
            ("do_deleteDataSource", "")
        ]

        for command, arg in test_cases:
            with redirect_stdout(StringIO()) as fake_stdout:
                getattr(shell, command)(arg)

            mock_display_formatter.format_error.assert_called()
            mock_display_formatter.reset_mock()


if __name__ == '__main__':
    unittest.main()