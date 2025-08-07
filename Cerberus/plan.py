import getpass
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
