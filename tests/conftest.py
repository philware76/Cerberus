import logging
import warnings
from pathlib import Path

import pytest
from iniconfig import IniConfig

from Cerberus.database.fileDB import FileDB
from Cerberus.manager import Manager
from Cerberus.pluginService import PluginService


def pytest_configure(config):
    """Configure pytest-specific settings."""
    # Suppress pytest collection warnings for classes that are not test classes
    warnings.filterwarnings(
        "ignore",
        category=pytest.PytestCollectionWarning,
        message=".*cannot collect test class.*because it has a __init__ constructor.*"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--strict-warnings",
        action="store_true",
        default=False,
        help="Treat warning-level assertions as test failures"
    )


@pytest.fixture
def warn_assert(request):
    def _assert(condition, message):
        if request.config.getoption("--strict-warnings"):
            if not condition:
                pytest.fail(f"[STRICT] {message}", pytrace=False)  # 👈 RIGHT HERE
        elif not condition:
            logging.warning(f"[WARN] {message}")
    return _assert


@pytest.fixture(autouse=True, scope="session")
def configure_logging():
    logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="session")
def pluginService():
    """Create and enumerate a PluginService for testing."""
    service = PluginService()
    service.enumerate()
    return service


@pytest.fixture(scope="session")
def manager(pluginService):
    config_path = Path(__file__).resolve().parent.parent / 'cerberus.ini'
    if not config_path.exists():
        config_path = Path(__file__).resolve().parent.parent.parent / 'cerberus.ini'

    station_id = 'UNKNOWN_STATION'
    if config_path.exists():
        try:
            cfg = IniConfig(str(config_path))
            station_id = cfg['cerberus']['identity']  # type: ignore[index]
        except Exception:  # Broad: missing section/key or parse issue
            pass

    fileDB = FileDB(station_id, "testDatabase.json")
    return Manager(station_id, fileDB, pluginService)
