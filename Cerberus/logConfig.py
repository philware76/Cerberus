import logging
import sys

CERBERUS_LOGGER_NAME = "cerberus"


def setupLogging(level=logging.INFO, silence_external: bool = True) -> logging.Logger:
    """Configure and return the Cerberus application logger.

    Parameters:
        level: Base level for Cerberus log hierarchy.
        silence_external: If True, reduce noise from third-party libraries by
            elevating their log levels (keeps root at WARNING).
    """

    class ColorFormatter(logging.Formatter):
        COLORS = {
            logging.DEBUG: "\033[38;5;244m",  # dim
            logging.INFO: "\033[32m",
            logging.WARNING: "\033[33m",
            logging.ERROR: "\033[31m",
            logging.CRITICAL: "\033[41m",
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelno, self.RESET)
            message = super().format(record)
            return f"{color}{message}{self.RESET}"

    formatter = ColorFormatter("[%(levelname)s] [%(name)s:%(lineno)d] %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger: keep higher level to avoid third-party noise
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING if silence_external else level)

    # Cerberus logger hierarchy
    logger = logging.getLogger(CERBERUS_LOGGER_NAME)
    logger.setLevel(level)
    # Attach handler only if not already attached (avoid duplicates on re-init)
    if all(h is not handler for h in logger.handlers):
        logger.addHandler(handler)
    logger.propagate = False  # avoid duplicate emission via root

    if silence_external:
        # Quiet some noisy libraries
        for noisy in ["pyvisa", "urllib3", "PIL", "matplotlib"]:
            logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger


def getLogger(name: str | None = None) -> logging.Logger:
    """Return a Cerberus namespaced logger.

    getLogger("pluginDiscovery") -> cerberus.pluginDiscovery
    getLogger() -> cerberus
    """
    base = CERBERUS_LOGGER_NAME
    return logging.getLogger(base if not name else f"{base}.{name}")
