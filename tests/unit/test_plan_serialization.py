from datetime import datetime

import pytest

from Cerberus.plan import Plan


def test_plan_round_trip():
    p = Plan("AlphaPlan", user="tester", date=datetime(2024, 1, 1, 12, 0, 0))
    p.extend(["TestA", "TestB"])    
    data = p.to_dict()
    p2 = Plan.from_dict(data)
    assert p2.name == p.name
    assert p2.user == p.user
    assert p2.date.isoformat() == p.date.isoformat()
    assert list(p2) == ["TestA", "TestB"]
