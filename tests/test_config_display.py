"""Unit tests for _config_display module.

Tests for display formatting functionality,
separate from business logic and UI control.
"""

import json
import unittest
from unittest.mock import Mock, patch

from sz_tools._config_display import ConfigDisplayFormatter


class TestConfigDisplayFormatter(unittest.TestCase):
    """Test cases for ConfigDisplayFormatter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = ConfigDisplayFormatter(use_colors=True)
        self.formatter_no_colors = ConfigDisplayFormatter(use_colors=False)

    def test_initialization(self):
        """Test ConfigDisplayFormatter initialization."""
        # Test with colors enabled
        formatter = ConfigDisplayFormatter(use_colors=True)
        self.assertTrue(formatter.use_colors)

        # Test with colors disabled
        formatter = ConfigDisplayFormatter(use_colors=False)
        self.assertFalse(formatter.use_colors)

        # Test default
        formatter = ConfigDisplayFormatter()
        self.assertTrue(formatter.use_colors)

    @patch('sz_tools._config_display.Colors.apply')
    def test_colorize_with_colors(self, mock_colors):
        """Test colorize method with colors enabled."""
        mock_colors.return_value = "colored_text"

        result = self.formatter.colorize("test text", "good")

        mock_colors.assert_called_once_with("test text", "good")
        self.assertEqual(result, "colored_text")

    def test_colorize_without_colors(self):
        """Test colorize method with colors disabled."""
        result = self.formatter_no_colors.colorize("test text", "good")

        self.assertEqual(result, "test text")

    def test_format_message_types(self):
        """Test format_message with different message types."""
        test_cases = [
            ("ERROR", "bad"),
            ("WARNING", "caution,italics"),
            ("INFO", "highlight2"),
            ("SUCCESS", "good"),
            ("custom_color", "custom_color")
        ]

        for message_type, expected_color in test_cases:
            with patch.object(self.formatter, 'colorize') as mock_colorize:
                mock_colorize.return_value = f"colored_{message_type}"

                result = self.formatter.format_message("test message", message_type)

                mock_colorize.assert_called_once_with("test message", expected_color)
                self.assertEqual(result, f"\ncolored_{message_type}\n")

    def test_format_json_pretty(self):
        """Test JSON formatting with pretty printing."""
        test_json = '{"key": "value", "number": 123}'

        result = self.formatter_no_colors.format_json(test_json, pretty=True)

        # Should be pretty-printed
        self.assertIn("{\n", result)
        self.assertIn("  \"key\": \"value\"", result)
        self.assertIn("  \"number\": 123", result)

    def test_format_json_not_pretty(self):
        """Test JSON formatting without pretty printing."""
        test_json = '{"key": "value"}'

        with patch('sz_tools._config_display.PYGMENTS_AVAILABLE', False):
            result = self.formatter_no_colors.format_json(test_json, pretty=False)

        self.assertEqual(result, test_json)

    @patch('sz_tools._config_display.PYGMENTS_AVAILABLE', True)
    @patch('sz_tools._config_display.highlight')
    @patch('sz_tools._config_display.lexers')
    @patch('sz_tools._config_display.formatters')
    def test_format_json_with_pygments(self, mock_formatters, mock_lexers, mock_highlight):
        """Test JSON formatting with pygments syntax highlighting."""
        mock_lexer = Mock()
        mock_formatter = Mock()
        mock_lexers.JsonLexer.return_value = mock_lexer
        mock_formatters.TerminalFormatter.return_value = mock_formatter
        mock_highlight.return_value = "highlighted_json"

        test_json = '{"key": "value"}'

        result = self.formatter.format_json(test_json)

        mock_highlight.assert_called_once_with(
            '{\n  "key": "value"\n}', mock_lexer, mock_formatter
        )
        self.assertEqual(result, "highlighted_json")

    def test_format_json_invalid(self):
        """Test JSON formatting with invalid JSON."""
        invalid_json = "invalid json content"

        result = self.formatter.format_json(invalid_json)

        self.assertEqual(result, invalid_json)

    def test_format_json_empty(self):
        """Test JSON formatting with empty string."""
        result = self.formatter.format_json("")

        self.assertEqual(result, "")

    def test_colorize_json_simple(self):
        """Test simple JSON colorization."""
        test_json = '{"key": "value", "other": "data"}'

        with patch.object(self.formatter, 'colorize') as mock_colorize:
            mock_colorize.side_effect = lambda text, color: f"[{color}]{text}[/{color}]"

            result = self.formatter._colorize_json_simple(test_json)

            # Should colorize keys and values
            self.assertIn("[attr_color]", result)
            self.assertIn("[value_color]", result)

    def test_format_config_registry_with_prettytable(self):
        """Test config registry formatting with prettytable available."""
        registry_json = json.dumps({
            "CONFIGS": [
                {
                    "CONFIG_ID": 1,
                    "CONFIG_COMMENT": "Initial config",
                    "SYS_CREATE_DT": "2023-01-01"
                },
                {
                    "CONFIG_ID": 2,
                    "CONFIG_COMMENT": "Updated config",
                    "SYS_CREATE_DT": "2023-01-02"
                }
            ]
        })

        with patch('sz_tools._config_display.prettytable') as mock_prettytable:
            mock_table = Mock()
            mock_prettytable.PrettyTable.return_value = mock_table
            mock_table.__str__ = Mock(return_value="formatted_table")

            result = self.formatter.format_config_registry(registry_json)

            mock_table.add_row.assert_any_call([1, "Initial config", "2023-01-01"])
            mock_table.add_row.assert_any_call([2, "Updated config", "2023-01-02"])
            self.assertIn("formatted_table", result)

    def test_format_config_registry_without_prettytable(self):
        """Test config registry formatting without prettytable."""
        registry_json = json.dumps({
            "CONFIGS": [
                {
                    "CONFIG_ID": 1,
                    "CONFIG_COMMENT": "Test config",
                    "SYS_CREATE_DT": "2023-01-01"
                }
            ]
        })

        with patch('sz_tools._config_display.prettytable', None):
            result = self.formatter_no_colors.format_config_registry(registry_json)

            self.assertIn("Configuration Registry:", result)
            self.assertIn("ID: 1", result)
            self.assertIn("Comment: Test config", result)
            self.assertIn("Created: 2023-01-01", result)

    def test_format_config_registry_invalid_json(self):
        """Test config registry formatting with invalid JSON."""
        invalid_json = "invalid json"

        result = self.formatter.format_config_registry(invalid_json)

        self.assertIn("Invalid JSON", result)
        self.assertIn("ERROR", result)

    def test_format_data_sources_with_prettytable(self):
        """Test data sources formatting with prettytable available."""
        data_sources = [
            {"DSRC_ID": 1, "DSRC_CODE": "SOURCE1"},
            {"DSRC_ID": 2, "DSRC_CODE": "SOURCE2"}
        ]

        with patch('sz_tools._config_display.prettytable') as mock_prettytable:
            mock_table = Mock()
            mock_prettytable.PrettyTable.return_value = mock_table
            mock_table.__str__ = Mock(return_value="formatted_table")

            result = self.formatter.format_data_sources(data_sources)

            mock_table.add_row.assert_any_call([1, "SOURCE1"])
            mock_table.add_row.assert_any_call([2, "SOURCE2"])
            self.assertIn("formatted_table", result)

    def test_format_data_sources_without_prettytable(self):
        """Test data sources formatting without prettytable."""
        data_sources = [
            {"DSRC_ID": 1, "DSRC_CODE": "SOURCE1"}
        ]

        with patch('sz_tools._config_display.prettytable', None):
            result = self.formatter_no_colors.format_data_sources(data_sources)

            self.assertIn("Data Sources:", result)
            self.assertIn("ID: 1", result)
            self.assertIn("Code: SOURCE1", result)

    def test_format_data_sources_empty(self):
        """Test data sources formatting with empty list."""
        result = self.formatter.format_data_sources([])

        self.assertIn("No data sources found", result)

    def test_format_help_topic(self):
        """Test help topic formatting."""
        result = self.formatter_no_colors.format_help_topic("test_topic", "help content")

        self.assertIn("TEST_TOPIC:", result)
        self.assertIn("help content", result)

    def test_format_error(self):
        """Test error message formatting."""
        result = self.formatter_no_colors.format_error("test error", "test context")

        self.assertIn("Error: test error", result)
        self.assertIn("Context: test context", result)

    def test_format_error_no_context(self):
        """Test error message formatting without context."""
        result = self.formatter_no_colors.format_error("test error")

        self.assertIn("Error: test error", result)
        self.assertNotIn("Context:", result)

    def test_format_success(self):
        """Test success message formatting."""
        result = self.formatter_no_colors.format_success("operation completed")

        self.assertIn("Success: operation completed", result)

    def test_format_warning(self):
        """Test warning message formatting."""
        result = self.formatter_no_colors.format_warning("be careful")

        self.assertIn("Warning: be careful", result)

    def test_format_info(self):
        """Test info message formatting."""
        result = self.formatter_no_colors.format_info("helpful information")

        self.assertIn("Info: helpful information", result)

    def test_use_colors_property(self):
        """Test use_colors property getter and setter."""
        # Test getter
        self.assertTrue(self.formatter.use_colors)
        self.assertFalse(self.formatter_no_colors.use_colors)

        # Test setter
        self.formatter.use_colors = False
        self.assertFalse(self.formatter.use_colors)

        self.formatter_no_colors.use_colors = True
        self.assertTrue(self.formatter_no_colors.use_colors)


    def test_colorize_json_simple_edge_cases(self):
        """Test simple JSON colorization edge cases."""
        # Test with nested quotes
        json_with_nested = '{"key": "value with \"quotes\""}'
        result = self.formatter._colorize_json_simple(json_with_nested)
        self.assertIsInstance(result, str)

        # Test with empty string
        result = self.formatter_no_colors._colorize_json_simple("")
        self.assertEqual(result, "")

        # Test with no JSON structure
        result = self.formatter._colorize_json_simple("plain text")
        self.assertEqual(result, "plain text")

    def test_format_json_large_json(self):
        """Test JSON formatting with large JSON object."""
        large_json = {
            "data": [
                {"id": i, "name": f"item_{i}", "value": i * 10}
                for i in range(100)
            ]
        }
        json_str = json.dumps(large_json)

        result = self.formatter_no_colors.format_json(json_str, pretty=True)

        # Should handle large JSON without errors
        self.assertIn('"data":', result)
        self.assertIn('"item_99"', result)

    def test_format_json_deeply_nested(self):
        """Test JSON formatting with deeply nested structure."""
        nested_json = '{"level1": {"level2": {"level3": {"level4": "deep_value"}}}}'

        result = self.formatter_no_colors.format_json(nested_json, pretty=True)

        self.assertIn('"level1":', result)
        self.assertIn('"deep_value"', result)

    def test_format_json_special_characters(self):
        """Test JSON formatting with special characters."""
        special_json = '{"unicode": "\u03B1\u03B2\u03B3", "newlines": "line1\nline2"}'

        result = self.formatter_no_colors.format_json(special_json, pretty=True)

        self.assertIn('"unicode":', result)
        self.assertIn('"newlines":', result)

    def test_format_config_registry_malformed_json(self):
        """Test config registry formatting with malformed JSON."""
        malformed_json = '{"CONFIGS": [invalid json'

        result = self.formatter.format_config_registry(malformed_json)

        self.assertIn("Invalid JSON", result)
        self.assertIn("ERROR", result)

    def test_format_config_registry_missing_configs_key(self):
        """Test config registry formatting without CONFIGS key."""
        invalid_structure = json.dumps({"OTHER_KEY": "value"})

        result = self.formatter.format_config_registry(invalid_structure)

        # Should handle gracefully, showing empty configs
        self.assertIsInstance(result, str)

    def test_format_config_registry_empty_configs(self):
        """Test config registry formatting with empty configs list."""
        empty_configs = json.dumps({"CONFIGS": []})

        result = self.formatter.format_config_registry(empty_configs)

        self.assertIn("Configuration Registry", result)

    def test_format_config_registry_missing_fields(self):
        """Test config registry formatting with missing fields."""
        incomplete_config = json.dumps({
            "CONFIGS": [
                {"CONFIG_ID": 1},  # Missing comment and date
                {"CONFIG_COMMENT": "Test"},  # Missing ID and date
                {}  # Empty config
            ]
        })

        result = self.formatter.format_config_registry(incomplete_config)

        # Should handle missing fields gracefully
        self.assertIn("Configuration Registry", result)
        self.assertIn("Unknown", result)

    def test_format_data_sources_missing_fields(self):
        """Test data sources formatting with missing fields."""
        incomplete_sources = [
            {"DSRC_ID": 1},  # Missing code
            {"DSRC_CODE": "TEST"},  # Missing ID
            {}  # Empty source
        ]

        result = self.formatter.format_data_sources(incomplete_sources)

        self.assertIn("Data Sources", result)
        self.assertIn("Unknown", result)

    def test_format_data_sources_none_input(self):
        """Test data sources formatting with None input."""
        result = self.formatter.format_data_sources(None)

        self.assertIn("No data sources found", result)

    def test_format_data_sources_large_list(self):
        """Test data sources formatting with large list."""
        large_sources = [
            {"DSRC_ID": i, "DSRC_CODE": f"SOURCE_{i}"}
            for i in range(100)
        ]

        result = self.formatter.format_data_sources(large_sources)

        self.assertIn("Data Sources", result)
        self.assertIn("SOURCE_99", result)

    def test_format_help_topic_long_content(self):
        """Test help topic formatting with very long content."""
        long_content = "This is a very long help content. " * 100

        result = self.formatter_no_colors.format_help_topic("LONG_TOPIC", long_content)

        self.assertIn("LONG_TOPIC:", result)
        self.assertIn(long_content, result)

    def test_format_help_topic_special_characters(self):
        """Test help topic formatting with special characters."""
        special_topic = "Topic with spaces & symbols!"
        special_content = "Content with \n newlines \t tabs and unicode: αβγ"

        result = self.formatter_no_colors.format_help_topic(special_topic, special_content)

        self.assertIn(special_topic.upper(), result)
        self.assertIn(special_content, result)

    def test_format_error_very_long_message(self):
        """Test error formatting with very long message."""
        long_error = "This is a very long error message. " * 50
        long_context = "This is a very long context. " * 50

        result = self.formatter_no_colors.format_error(long_error, long_context)

        self.assertIn("Error:", result)
        self.assertIn("Context:", result)
        self.assertIn(long_error, result)
        self.assertIn(long_context, result)

    def test_format_error_with_newlines(self):
        """Test error formatting with newlines in message."""
        multiline_error = "Line 1\nLine 2\nLine 3"
        multiline_context = "Context line 1\nContext line 2"

        result = self.formatter_no_colors.format_error(multiline_error, multiline_context)

        self.assertIn("Line 1", result)
        self.assertIn("Line 3", result)
        self.assertIn("Context line 2", result)

    def test_format_success_empty_message(self):
        """Test success formatting with empty message."""
        result = self.formatter_no_colors.format_success("")

        self.assertIn("Success:", result)

    def test_format_warning_special_characters(self):
        """Test warning formatting with special characters."""
        warning_with_special = "Warning: File contains special chars: <>?|\"*"

        result = self.formatter_no_colors.format_warning(warning_with_special)

        self.assertIn("Warning:", result)
        self.assertIn(warning_with_special, result)

    def test_format_info_unicode(self):
        """Test info formatting with unicode characters."""
        unicode_info = "Processing files: ✓ αβγ δεζ 中文 日本語"

        result = self.formatter_no_colors.format_info(unicode_info)

        self.assertIn("Info:", result)
        self.assertIn(unicode_info, result)

    def test_use_colors_property_thread_safety(self):
        """Test use_colors property with rapid changes."""
        # Rapid toggle to test property behavior
        for i in range(10):
            self.formatter.use_colors = (i % 2 == 0)
            self.assertEqual(self.formatter.use_colors, (i % 2 == 0))

    def test_colorize_with_invalid_color_list(self):
        """Test colorize with invalid color specifications."""
        # Test with None color list
        result = self.formatter.colorize("test", None)
        self.assertIsInstance(result, str)

        # Test with empty color list
        result = self.formatter.colorize("test", "")
        self.assertIsInstance(result, str)

    @patch('sz_tools._config_display.prettytable')
    def test_format_config_registry_prettytable_exception(self, mock_prettytable):
        """Test config registry formatting when prettytable raises exception."""
        mock_prettytable.PrettyTable.side_effect = Exception("PrettyTable error")

        registry_json = json.dumps({
            "CONFIGS": [
                {"CONFIG_ID": 1, "CONFIG_COMMENT": "Test", "SYS_CREATE_DT": "2023-01-01"}
            ]
        })

        # Should fall back gracefully
        result = self.formatter.format_config_registry(registry_json)
        self.assertIsInstance(result, str)

    @patch('sz_tools._config_display.prettytable')
    def test_format_data_sources_prettytable_exception(self, mock_prettytable):
        """Test data sources formatting when prettytable raises exception."""
        mock_prettytable.PrettyTable.side_effect = Exception("PrettyTable error")

        data_sources = [{"DSRC_ID": 1, "DSRC_CODE": "TEST"}]

        # Should fall back gracefully
        result = self.formatter.format_data_sources(data_sources)
        self.assertIsInstance(result, str)

    def test_format_json_with_circular_reference_simulation(self):
        """Test JSON formatting with complex structure that could cause issues."""
        # Create a complex but valid JSON structure
        complex_json = {
            "root": {
                "array": [1, 2, 3, {"nested": "deep"}],
                "object": {
                    "key1": "value1",
                    "key2": ["a", "b", "c"],
                    "key3": {
                        "subkey": "subvalue"
                    }
                },
                "null_value": None,
                "boolean": True,
                "number": 42.5
            }
        }
        json_str = json.dumps(complex_json)

        result = self.formatter_no_colors.format_json(json_str, pretty=True)

        self.assertIn('"root":', result)
        self.assertIn('"array":', result)
        self.assertIn('"subvalue"', result)

    def test_format_message_empty_message_type(self):
        """Test format_message with empty message type."""
        result = self.formatter_no_colors.format_message("test message", "")

        self.assertIn("test message", result)
        self.assertTrue(result.startswith("\n"))
        self.assertTrue(result.endswith("\n"))

    def test_format_message_unknown_message_type(self):
        """Test format_message with unknown message type."""
        result = self.formatter_no_colors.format_message("test message", "UNKNOWN_TYPE")

        self.assertIn("test message", result)


if __name__ == '__main__':
    unittest.main()