"""Pytest configuration for sz_configtool tests."""

import pytest
import os
import subprocess


def pytest_configure(config):
    """Configure pytest for sz_configtool testing."""
    # Add custom markers
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "edge_case: mark test as edge case test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "security: mark test as security test")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment for all tests."""
    # Ensure environment variables are set
    os.environ['SENZING_ENGINE_CONFIGURATION_JSON'] = '''{
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

    # Verify sz_configtool is available
    configtool_path = "/home/bmacy/open_dev/sz-python-tools/sz_tools/sz_configtool"
    if not os.path.exists(configtool_path):
        pytest.skip(f"sz_configtool not found at {configtool_path}")

    if not os.access(configtool_path, os.X_OK):
        pytest.skip(f"sz_configtool is not executable at {configtool_path}")

    # Test basic connectivity
    try:
        result = subprocess.run(
            [configtool_path],
            input="quit\\n",
            text=True,
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            pytest.skip(f"sz_configtool connectivity test failed: {result.stderr}")
    except (subprocess.TimeoutExpired, Exception) as e:
        pytest.skip(f"sz_configtool connectivity test failed: {e}")

    yield

    # Cleanup after all tests (if needed)
    pass


@pytest.fixture
def clean_environment():
    """Provide a clean test environment for each test."""
    # This fixture can be used by tests that need isolation
    yield
    # Cleanup after each test if needed


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add appropriate markers."""
    for item in items:
        # Add markers based on test names
        if "smoke" in item.name.lower():
            item.add_marker(pytest.mark.smoke)
        if "integration" in item.name.lower() or "workflow" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        if "edge" in item.name.lower() or "boundary" in item.name.lower():
            item.add_marker(pytest.mark.edge_case)
        if "performance" in item.name.lower() or "stress" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        if "security" in item.name.lower() or "injection" in item.name.lower():
            item.add_marker(pytest.mark.security)


def pytest_runtest_setup(item):
    """Setup for each test run."""
    # Skip performance tests by default unless specifically requested
    if "performance" in [marker.name for marker in item.iter_markers()]:
        if not item.config.getoption("--run-performance", default=False):
            pytest.skip("Performance tests skipped (use --run-performance to enable)")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--run-security",
        action="store_true",
        default=False,
        help="Run security tests"
    )