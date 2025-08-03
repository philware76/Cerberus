import getpass
from datetime import datetime
from typing import Dict, List, Self


class Plan(List[str]):
    def __init__(self, name: str):
        self.name = name
        self.user = getpass.getuser()
        self.date = datetime.now()

    @classmethod
    def EmptyPlan(cls):
        return cls("New1")

    def to_dict(self) -> Dict[str, str]:
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
