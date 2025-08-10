import getpass
import zlib
from datetime import datetime
from typing import Any, Dict, List, Self


class Plan(List[str]):
    def __init__(self, name: str, user: str | None = None, date: datetime | None = None):
        self.name = name
        self.user = user or getpass.getuser()
        self.date = date or datetime.now()
        self._dirty = False

    @classmethod
    def EmptyPlan(cls):
        return cls("Empty plan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "user": self.user,
            "date": self.date.isoformat(),
            "tests": list(self)
        }

    @classmethod
    def from_dict(cls, data) -> Self:
        plan = cls(data["name"])
        plan.user = data["user"]
        plan.date = datetime.fromisoformat(data["date"])
        plan.extend(data.get("tests", []))

        return plan


def calcCRC(plan: Plan) -> int:
    """Fast hash for a Plan's tests list.

    Compares only membership (add/remove), ignoring order. Duplicate entries still
    influence the hash (their count matters). Returns 0 for None.
    """
    if plan is None:
        return 0

    # Attempt to treat plan as iterable of test names
    tests: list[str]
    try:
        tests = [str(t) for t in plan]  # type: ignore[arg-type]
    except Exception:
        return 0

    # Order-insensitive: sort; include length to differentiate permutations with duplicates
    tests_sorted = sorted(tests)
    payload = ("|".join(tests_sorted) + f"#{len(tests_sorted)}").encode("utf-8")
    return zlib.crc32(payload) & 0xFFFFFFFF
