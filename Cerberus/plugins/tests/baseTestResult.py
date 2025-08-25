from datetime import datetime
from enum import Enum
from typing import Any, Optional

from Cerberus.logConfig import getLogger

logger = getLogger("BaseTestResult")


class ResultStatus(Enum):
    # Beginning status types
    PENDING = "Pending"

    # Passed status types
    PASSED = "Passed"

    # Failed status types
    FAILED = "Failed"
    SKIPPED = "Skipped"
    WAIVED = "Waived"
    FLAGGED = "Flaged"

    # Error status types
    ERROR = "Error"


class BaseTestResult:
    """Base test result for all tests"""

    def __init__(self, name: str, status: Optional[ResultStatus] = None) -> None:
        self.name = name
        if status is not None:
            self.status: ResultStatus = status
        else:
            self.status: ResultStatus = ResultStatus.PENDING

        self.timestanmp = datetime.now()
        self.log = ""

        # Test References are to store the equipment settings and the test settings refence id's
        # so that we know how the test was run. This is so we can go back and check/verify
        # the test results. Here we simply list the equipment used and the settings of that equipment
        # as well as the test settings.
        # self.testReferences = {"Equipment": [], "Test": []}

        # This contains all the results from the test runs.
        # This could be one long list of a value, or a complex dictionary of lists of various objects
        self.testResult = {}

    def addTestResult(self, name: str, result: Any):
        """Adds a test result object to a named result list"""
        logger.debug(f"Added '{name}' to {self.name} result list")
        if name not in self.testResult:
            self.testResult[name] = []
        self.testResult[name].append(result)
