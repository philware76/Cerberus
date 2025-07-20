# cerberus/testmanager.py
import sys

import logging

from testManager import TestManager

TRACE_LEVEL_NUM = 5

def setup_logging(level=logging.DEBUG):
    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            self._log(TRACE_LEVEL_NUM, message, args, **kwargs)
    logging.Logger.trace = trace

    def trace_global(message, *args, **kwargs):
        logging.log(TRACE_LEVEL_NUM, message, *args, **kwargs)
    logging.trace = trace_global

    # --- Color formatter ---
    class ColorFormatter(logging.Formatter):
        COLORS = {
            TRACE_LEVEL_NUM: "\033[90m",    # Grey
            logging.DEBUG: "\033[38;5;244m",      # White
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
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

if __name__ == "__main__":
    logging.TRACE = TRACE_LEVEL_NUM  # Optional convenience
    logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

    setup_logging(logging.DEBUG)

    logging.info("Starting TestManager...")
    manager = TestManager()

    logging.info("Available equipment plugins:")
    for equipment in manager.Equipement.listPlugins():
        logging.info(" - " + equipment)

    logging.info("Available test plugins:")
    for test in manager.Test.listPlugins():
        logging.info(" - " + test)

    test = manager.Test.createPlugin("TxLevelTest")
    if test:
        print(f"Created test plugin: {test.name}")
    else:
        print("Plugin not found.")

    if test:
        test.run()
        result = test.getResult()
        logging.info(f"Test result: {result.name} - {result.status}")