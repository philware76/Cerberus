import getpass
from datetime import datetime
from typing import List


class Plan(List[str]):
    def __init__(self, name: str):
        self.name = name
        self.user = getpass.getuser()
        self.date = datetime.now()
        self.tests: list[str] = []

    def to_dict(self):
        return {
            "name": self.name,
            "user": self.user,
            "date": self.date.isoformat(),
            "tests": self.tests
        }

    @classmethod
    def from_dict(cls, data):
        plan = cls(data["name"])
        plan.user = data["user"]
        plan.date = datetime.fromisoformat(data["date"])
        plan.tests = list(data["tests"])
        return plan
