"""Test fixtures and utilities for sz_configtool tests.

Provides common test data, mock objects, and utility functions
for use across all test modules.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock


class SenzingMockFactory:
    """Factory for creating standardized Senzing mocks."""

    @staticmethod
    def create_config_manager_mock():
        """Create a mock SzConfigManager with common methods."""
        mock = Mock()
        mock.get_default_config_id.return_value = 1
        mock.get_configs.return_value = TestDataFixtures.get_sample_config_registry()
        mock.get_config.return_value = TestDataFixtures.get_sample_configuration()
        mock.add_config.return_value = 123
        mock.close.return_value = None
        return mock

    @staticmethod
    def create_config_mock():
        """Create a mock SzConfig with common methods."""
        mock = Mock()
        mock.export_config.return_value = TestDataFixtures.get_sample_configuration()
        mock.import_config.return_value = None
        mock.add_data_source.return_value = None
        mock.delete_data_source.return_value = None
        mock.close.return_value = None
        return mock

    @staticmethod
    def create_factory_mock():
        """Create a mock SzAbstractFactoryCore."""
        mock = Mock()
        mock.create_config_manager.return_value = SenzingMockFactory.create_config_manager_mock()
        mock.create_config.return_value = SenzingMockFactory.create_config_mock()
        return mock


class TestDataFixtures:
    """Test data fixtures for consistent testing."""

    @staticmethod
    def get_sample_configuration() -> str:
        """Get a sample Senzing configuration JSON."""
        config = {
            "G2_CONFIG": {
                "CFG_DSRC": [
                    {"DSRC_ID": 1, "DSRC_CODE": "CUSTOMERS"},
                    {"DSRC_ID": 2, "DSRC_CODE": "VENDORS"},
                    {"DSRC_ID": 3, "DSRC_CODE": "EMPLOYEES"}
                ],
                "CFG_ATTR": [
                    {
                        "ATTR_ID": 1001,
                        "ATTR_CODE": "DATA_SOURCE",
                        "ATTR_CLASS": "OBSERVATION",
                        "FTYPE_CODE": None,
                        "FELEM_CODE": None,
                        "FELEM_REQ": "Yes",
                        "DEFAULT_VALUE": None,
                        "INTERNAL": "No"
                    },
                    {
                        "ATTR_ID": 1003,
                        "ATTR_CODE": "RECORD_ID",
                        "ATTR_CLASS": "OBSERVATION",
                        "FTYPE_CODE": None,
                        "FELEM_CODE": None,
                        "FELEM_REQ": "No",
                        "DEFAULT_VALUE": None,
                        "INTERNAL": "No"
                    }
                ]
            }
        }
        return json.dumps(config, indent=2)

    @staticmethod
    def get_sample_config_registry() -> str:
        """Get a sample configuration registry JSON."""
        registry = {
            "CONFIGS": [
                {
                    "CONFIG_ID": 1,
                    "CONFIG_COMMENT": "Initial configuration",
                    "SYS_CREATE_DT": "2023-01-01T10:00:00.000Z"
                },
                {
                    "CONFIG_ID": 2,
                    "CONFIG_COMMENT": "Updated configuration with new data sources",
                    "SYS_CREATE_DT": "2023-01-02T15:30:00.000Z"
                },
                {
                    "CONFIG_ID": 3,
                    "CONFIG_COMMENT": "Production configuration",
                    "SYS_CREATE_DT": "2023-01-03T09:15:00.000Z"
                }
            ]
        }
        return json.dumps(registry, indent=2)

    @staticmethod
    def get_sample_data_sources() -> List[Dict[str, Any]]:
        """Get a sample list of data sources."""
        return [
            {"DSRC_ID": 1, "DSRC_CODE": "CUSTOMERS"},
            {"DSRC_ID": 2, "DSRC_CODE": "VENDORS"},
            {"DSRC_ID": 3, "DSRC_CODE": "EMPLOYEES"},
            {"DSRC_ID": 4, "DSRC_CODE": "PARTNERS"}
        ]

    @staticmethod
    def get_minimal_configuration() -> str:
        """Get a minimal Senzing configuration for testing."""
        config = {
            "G2_CONFIG": {
                "CFG_DSRC": [
                    {"DSRC_ID": 1, "DSRC_CODE": "TEST_SOURCE"}
                ]
            }
        }
        return json.dumps(config)

    @staticmethod
    def get_empty_configuration() -> str:
        """Get an empty Senzing configuration for testing."""
        config = {
            "G2_CONFIG": {
                "CFG_DSRC": []
            }
        }
        return json.dumps(config)

    @staticmethod
    def get_invalid_json() -> str:
        """Get invalid JSON for error testing."""
        return '{"invalid": json without proper ending'

    @staticmethod
    def get_malformed_configuration() -> str:
        """Get a malformed configuration structure."""
        config = {
            "INVALID_ROOT": {
                "WRONG_KEY": "wrong_value"
            }
        }
        return json.dumps(config)

    @staticmethod
    def get_large_configuration() -> str:
        """Get a large configuration for performance testing."""
        dsrc_list = [
            {"DSRC_ID": i, "DSRC_CODE": f"SOURCE_{i:04d}"}
            for i in range(1, 101)  # 100 data sources
        ]

        attr_list = [
            {
                "ATTR_ID": 1000 + i,
                "ATTR_CODE": f"ATTR_{i:04d}",
                "ATTR_CLASS": "TEST",
                "FTYPE_CODE": None,
                "FELEM_CODE": None,
                "FELEM_REQ": "No",
                "DEFAULT_VALUE": None,
                "INTERNAL": "No"
            }
            for i in range(1, 51)  # 50 attributes
        ]

        config = {
            "G2_CONFIG": {
                "CFG_DSRC": dsrc_list,
                "CFG_ATTR": attr_list
            }
        }
        return json.dumps(config, indent=2)

    @staticmethod
    def get_unicode_configuration() -> str:
        """Get a configuration with Unicode characters."""
        config = {
            "G2_CONFIG": {
                "CFG_DSRC": [
                    {"DSRC_ID": 1, "DSRC_CODE": "UNICODE_αβγ"},
                    {"DSRC_ID": 2, "DSRC_CODE": "CHINESE_中文"},
                    {"DSRC_ID": 3, "DSRC_CODE": "JAPANESE_日本語"},
                    {"DSRC_ID": 4, "DSRC_CODE": "EMOJI_🔧📊"}
                ]
            }
        }
        return json.dumps(config, ensure_ascii=False, indent=2)


class FileTestFixtures:
    """File-based test fixtures."""

    @staticmethod
    def create_temp_config_file(content: str = None) -> str:
        """Create a temporary configuration file."""
        if content is None:
            content = TestDataFixtures.get_sample_configuration()

        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.json',
            encoding='utf-8'
        )

        with temp_file as f:
            f.write(content)

        return temp_file.name

    @staticmethod
    def create_temp_command_file(commands: List[str]) -> str:
        """Create a temporary command file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.txt',
            encoding='utf-8'
        )

        with temp_file as f:
            for command in commands:
                f.write(f"{command}\\n")

        return temp_file.name

    @staticmethod
    def cleanup_temp_file(file_path: str) -> None:
        """Clean up a temporary file."""
        try:
            Path(file_path).unlink()
        except FileNotFoundError:
            pass  # File already deleted

    @staticmethod
    def create_readonly_file(content: str) -> str:
        """Create a read-only file for permission testing."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.json'
        )

        with temp_file as f:
            f.write(content)

        # Make file read-only
        Path(temp_file.name).chmod(0o444)

        return temp_file.name


class MockDisplayFormatter:
    """Mock display formatter for testing UI interactions."""

    def __init__(self, use_colors: bool = False):
        """Initialize mock display formatter."""
        self.use_colors = use_colors
        self.format_calls = []

    def format_success(self, message: str) -> str:
        """Mock format_success method."""
        self.format_calls.append(('success', message))
        return f"Success: {message}"

    def format_error(self, message: str, context: str = "") -> str:
        """Mock format_error method."""
        self.format_calls.append(('error', message, context))
        result = f"Error: {message}"
        if context:
            result += f"\\nContext: {context}"
        return result

    def format_warning(self, message: str) -> str:
        """Mock format_warning method."""
        self.format_calls.append(('warning', message))
        return f"Warning: {message}"

    def format_info(self, message: str) -> str:
        """Mock format_info method."""
        self.format_calls.append(('info', message))
        return f"Info: {message}"

    def format_help_topic(self, topic: str, content: str) -> str:
        """Mock format_help_topic method."""
        self.format_calls.append(('help', topic, content))
        return f"{topic.upper()}:\\n{content}"

    def format_json(self, json_str: str, pretty: bool = True) -> str:
        """Mock format_json method."""
        self.format_calls.append(('json', json_str, pretty))
        if pretty:
            try:
                data = json.loads(json_str)
                return json.dumps(data, indent=2)
            except json.JSONDecodeError:
                return json_str
        return json_str

    def format_config_registry(self, registry_json: str) -> str:
        """Mock format_config_registry method."""
        self.format_calls.append(('registry', registry_json))
        return f"Configuration Registry:\\n{registry_json}"

    def format_data_sources(self, data_sources: List[Dict[str, Any]]) -> str:
        """Mock format_data_sources method."""
        self.format_calls.append(('data_sources', data_sources))
        if not data_sources:
            return "No data sources found."

        result = "Data Sources:\\n"
        for ds in data_sources:
            result += f"ID: {ds.get('DSRC_ID', 'Unknown')}, Code: {ds.get('DSRC_CODE', 'Unknown')}\\n"
        return result

    def colorize(self, text: str, color_list: str = "None") -> str:
        """Mock colorize method."""
        if self.use_colors:
            return f"[{color_list}]{text}[/{color_list}]"
        return text

    def reset_calls(self) -> None:
        """Reset the format calls list."""
        self.format_calls = []

    def get_calls_by_type(self, call_type: str) -> List[tuple]:
        """Get calls of a specific type."""
        return [call for call in self.format_calls if call[0] == call_type]


class TestCommandSequences:
    """Predefined command sequences for testing."""

    @staticmethod
    def get_basic_workflow() -> List[str]:
        """Get a basic workflow command sequence."""
        return [
            "getDefaultConfigID",
            "getConfigRegistry",
            "listDataSources",
            "quit"
        ]

    @staticmethod
    def get_data_source_management() -> List[str]:
        """Get a data source management command sequence."""
        return [
            "listDataSources",
            "addDataSource NEW_TEST_SOURCE",
            "listDataSources",
            "deleteDataSource NEW_TEST_SOURCE",
            "listDataSources",
            "quit"
        ]

    @staticmethod
    def get_configuration_management() -> List[str]:
        """Get a configuration management command sequence."""
        return [
            "getDefaultConfigID",
            "reload_config",
            "save Test configuration update",
            "getConfigRegistry",
            "quit"
        ]

    @staticmethod
    def get_file_operations() -> List[str]:
        """Get a file operations command sequence."""
        return [
            "exportToFile /tmp/test_export.json",
            "importFromFile /tmp/test_import.json",
            "quit"
        ]

    @staticmethod
    def get_error_scenarios() -> List[str]:
        """Get a command sequence that triggers errors."""
        return [
            "exportToFile",  # Missing filename
            "importFromFile",  # Missing filename
            "addDataSource",  # Missing data source code
            "deleteDataSource",  # Missing data source code
            "reload_config invalid_id",  # Invalid config ID
            "quit"
        ]

    @staticmethod
    def get_help_commands() -> List[str]:
        """Get a help command sequence."""
        return [
            "help",
            "help getDefaultConfigID",
            "help getConfigRegistry",
            "help listDataSources",
            "help addDataSource",
            "help deleteDataSource",
            "help save",
            "help exportToFile",
            "help importFromFile",
            "help setTheme",
            "quit"
        ]

    @staticmethod
    def get_theme_commands() -> List[str]:
        """Get a theme management command sequence."""
        return [
            "setTheme color",
            "setTheme nocolor",
            "setTheme",  # Show current theme
            "setTheme invalid",  # Invalid theme
            "quit"
        ]

    @staticmethod
    def get_stress_test_commands() -> List[str]:
        """Get a command sequence for stress testing."""
        commands = []

        # Add many data sources
        for i in range(50):
            commands.append(f"addDataSource STRESS_TEST_SOURCE_{i:03d}")

        # List data sources multiple times
        for i in range(10):
            commands.append("listDataSources")

        # Delete some data sources
        for i in range(25):
            commands.append(f"deleteDataSource STRESS_TEST_SOURCE_{i:03d}")

        commands.append("quit")
        return commands


class AssertionHelpers:
    """Helper methods for test assertions."""

    @staticmethod
    def assert_valid_json(json_string: str) -> Dict[str, Any]:
        """Assert that a string is valid JSON and return parsed data."""
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON: {e}") from e

    @staticmethod
    def assert_contains_data_source(data_sources: List[Dict[str, Any]], dsrc_code: str) -> None:
        """Assert that a data source list contains a specific data source code."""
        codes = [ds.get("DSRC_CODE") for ds in data_sources]
        if dsrc_code not in codes:
            raise AssertionError(f"Data source '{dsrc_code}' not found in {codes}")

    @staticmethod
    def assert_senzing_config_structure(config_json: str) -> None:
        """Assert that a JSON string has the basic Senzing configuration structure."""
        data = AssertionHelpers.assert_valid_json(config_json)

        if "G2_CONFIG" not in data:
            raise AssertionError("Missing G2_CONFIG root key in configuration")

        g2_config = data["G2_CONFIG"]
        if not isinstance(g2_config, dict):
            raise AssertionError("G2_CONFIG must be a dictionary")

    @staticmethod
    def assert_output_contains_success(output: str) -> None:
        """Assert that output contains success message."""
        if "Success:" not in output and "✅" not in output:
            raise AssertionError(f"Output does not contain success message: {output}")

    @staticmethod
    def assert_output_contains_error(output: str) -> None:
        """Assert that output contains error message."""
        if "Error:" not in output and "❌" not in output:
            raise AssertionError(f"Output does not contain error message: {output}")

    @staticmethod
    def assert_mock_called_with_any(mock_obj, method_name: str, expected_arg: str) -> None:
        """Assert that a mock method was called with an argument containing expected text."""
        method = getattr(mock_obj, method_name)

        for call in method.call_args_list:
            args = call[0] if call[0] else call[1].values()
            for arg in args:
                if isinstance(arg, str) and expected_arg in arg:
                    return

        raise AssertionError(
            f"{method_name} was not called with argument containing '{expected_arg}'. "
            f"Actual calls: {method.call_args_list}"
        )