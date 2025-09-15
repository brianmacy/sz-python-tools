"""Common mock setup for sz_configtool tests.

This module provides centralized mock setup for Senzing dependencies
to allow tests to run in environments without the Senzing SDK installed.
"""

import sys
from unittest.mock import Mock


def setup_senzing_mocks():
    """Set up mock senzing modules to avoid import errors.

    This function should be called before importing any sz_tools modules
    that depend on senzing or senzing_core packages.
    """
    # Mock senzing module
    mock_senzing = Mock()
    mock_senzing.SzError = Exception  # Use Exception as base for SzError
    mock_senzing.SzEngineFlags = Mock()
    mock_senzing.constants = Mock()
    sys.modules['senzing'] = mock_senzing

    # Mock senzing_core module
    mock_senzing_core = Mock()
    mock_senzing_core.SzAbstractFactoryCore = Mock
    sys.modules['senzing_core'] = mock_senzing_core

    return mock_senzing, mock_senzing_core


def setup_test_environment():
    """Set up complete test environment with mocks and path setup.

    Returns:
        tuple: (mock_senzing, mock_senzing_core) for additional customization
    """
    import os

    # Add sz_tools directory to path
    sz_tools_path = os.path.join(os.path.dirname(__file__), '..', 'sz_tools')
    if sz_tools_path not in sys.path:
        sys.path.insert(0, sz_tools_path)

    # Set up senzing mocks
    return setup_senzing_mocks()


def create_mock_factory_setup():
    """Create a standard mock factory setup for configuration manager tests.

    Returns:
        dict: Dictionary containing standard mock objects for testing
    """
    mock_factory = Mock()
    mock_config_mgr = Mock()
    mock_config = Mock()

    # Set up factory returns
    mock_factory.return_value.create_configmanager.return_value = mock_config_mgr
    mock_factory.return_value.create_config.return_value = mock_config

    # Set up standard config manager mocks
    mock_config_mgr.get_default_config_id.return_value = 1
    mock_config_mgr.create_config_from_config_id.return_value = mock_config
    mock_config_mgr.create_config_from_json.return_value = mock_config
    mock_config_mgr.register_config.return_value = 123

    # Set up standard config mocks
    test_config_data = {
        "G2_CONFIG": {
            "CFG_DSRC": [
                {"DSRC_ID": 1, "DSRC_CODE": "TEST_SOURCE"}
            ]
        }
    }

    import json
    mock_config.export.return_value = json.dumps(test_config_data)
    mock_config.import_config.return_value = None

    return {
        'mock_factory': mock_factory,
        'mock_config_mgr': mock_config_mgr,
        'mock_config': mock_config,
        'test_config_data': test_config_data
    }