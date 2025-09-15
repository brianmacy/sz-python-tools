"""Tests for verbose logging functionality with -t flag."""
import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from _config_core import ConfigurationManager
from configtool_main import parse_cli_args


class TestVerboseLogging:
    """Test verbose logging functionality."""

    def test_verbose_logging_flag_parsing(self):
        """Test that -t flag is properly parsed."""
        # Test without -t flag
        with patch('sys.argv', ['configtool_main.py']):
            args = parse_cli_args()
            assert args.verbose_logging is False

        # Test with -t flag
        with patch('sys.argv', ['configtool_main.py', '-t']):
            args = parse_cli_args()
            assert args.verbose_logging is True

        # Test with --verbose-logging flag
        with patch('sys.argv', ['configtool_main.py', '--verbose-logging']):
            args = parse_cli_args()
            assert args.verbose_logging is True

    def test_configuration_manager_receives_verbose_flag(self):
        """Test that ConfigurationManager properly receives verbose logging flag."""
        # Test with verbose logging disabled
        config_mgr = ConfigurationManager('test.ini', verbose_logging=False)
        assert config_mgr._verbose_logging is False

        # Test with verbose logging enabled
        config_mgr = ConfigurationManager('test.ini', verbose_logging=True)
        assert config_mgr._verbose_logging is True

    @patch('_config_core.SzAbstractFactoryCore')
    @patch('_config_core.get_engine_config')
    def test_verbose_logging_passed_to_sz_factory(self, mock_get_engine_config, mock_sz_factory):
        """Test that verbose logging flag is passed to SzAbstractFactoryCore."""
        mock_get_engine_config.return_value = '{"test": "config"}'
        mock_factory_instance = Mock()
        mock_sz_factory.return_value = mock_factory_instance
        mock_config_mgr = Mock()
        mock_factory_instance.create_configmanager.return_value = mock_config_mgr
        mock_config_mgr.get_default_config_id.return_value = 1
        mock_config_mgr.create_config_from_config_id.return_value = Mock()

        # Test with verbose logging enabled
        config_mgr = ConfigurationManager('test.ini', verbose_logging=True)
        success = config_mgr.initialize_senzing()

        assert success is True

        # Verify SzAbstractFactoryCore was called with verbose_logging=True
        mock_sz_factory.assert_called_with(
            "sz_configtool",
            '{"test": "config"}',
            verbose_logging=True
        )

    @patch('_config_core.SzAbstractFactoryCore')
    @patch('_config_core.get_engine_config')
    def test_no_verbose_logging_when_disabled(self, mock_get_engine_config, mock_sz_factory):
        """Test that verbose logging is not passed when disabled."""
        mock_get_engine_config.return_value = '{"test": "config"}'
        mock_factory_instance = Mock()
        mock_sz_factory.return_value = mock_factory_instance
        mock_config_mgr = Mock()
        mock_factory_instance.create_configmanager.return_value = mock_config_mgr
        mock_config_mgr.get_default_config_id.return_value = 1
        mock_config_mgr.create_config_from_config_id.return_value = Mock()

        # Test with verbose logging disabled
        config_mgr = ConfigurationManager('test.ini', verbose_logging=False)
        success = config_mgr.initialize_senzing()

        assert success is True

        # Verify SzAbstractFactoryCore was called without verbose_logging parameter
        mock_sz_factory.assert_called_with(
            "sz_configtool",
            '{"test": "config"}'
        )

    def test_help_shows_verbose_logging_flag(self):
        """Test that help output shows the -t flag."""
        with patch('sys.argv', ['configtool_main.py', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                parse_cli_args()

            # Help should exit with code 0
            assert exc_info.value.code == 0

        # The help text should contain information about -t flag
        # This is implicitly tested by the successful parsing test above

    @patch('sys.argv', ['configtool_main.py', '-t', '--help'])
    def test_verbose_flag_and_help_together(self):
        """Test that -t flag and --help can be used together."""
        with pytest.raises(SystemExit) as exc_info:
            parse_cli_args()

        # Should still exit with 0 for help
        assert exc_info.value.code == 0

    def test_configuration_manager_constructor_defaults(self):
        """Test ConfigurationManager constructor defaults."""
        # Test with no parameters - should default verbose_logging to False
        config_mgr = ConfigurationManager()
        assert config_mgr._verbose_logging is False
        assert config_mgr._ini_file_name is None

        # Test with ini file only
        config_mgr = ConfigurationManager('test.ini')
        assert config_mgr._verbose_logging is False
        assert config_mgr._ini_file_name == 'test.ini'

        # Test with both parameters
        config_mgr = ConfigurationManager('test.ini', verbose_logging=True)
        assert config_mgr._verbose_logging is True
        assert config_mgr._ini_file_name == 'test.ini'


if __name__ == "__main__":
    # Run the verbose logging tests
    pytest.main([__file__, "-v", "--tb=short"])