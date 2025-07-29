import logging
import pytest


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
