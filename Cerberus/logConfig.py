import logging
import sys


def setupLogging(level=logging.INFO):
    # --- Color formatter ---
    class ColorFormatter(logging.Formatter):
        COLORS = {
            logging.DEBUG: "\033[38;5;244m",  # White
            logging.INFO: "\033[32m",       # Green
            logging.WARNING: "\033[33m",    # Yellow
            logging.ERROR: "\033[31m",      # Red
            logging.CRITICAL: "\033[41m",   # Red background
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelno, self.RESET)
            message = super().format(record)
            return f"{color}{message}{self.RESET}"

    formatter = ColorFormatter("[%(levelname)s] [%(module)s:%(lineno)d] %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # --- Configure root logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
