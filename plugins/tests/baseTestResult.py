from dataclasses import dataclass
from enum import Enum

class ResultStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class BaseTestResult:
    name: str
    status: ResultStatus