import getpass
from datetime import datetime

from Cerberus.plan import Plan


def test_plan_creation():
    plan = Plan("Test Plan")
    assert plan.name == "Test Plan"
    assert plan.user == getpass.getuser()
    assert plan.date is not None
    assert len(plan) == 0
    
def test_plan_to_dict():
    plan = Plan("Test Plan")
    plan.append("Test 1")
    plan.append("Test 2")
    plan_dict = plan.to_dict()
    
    assert plan_dict["name"] == "Test Plan"
    assert plan_dict["user"] == getpass.getuser()
    assert "tests" in plan_dict
    assert len(plan_dict["tests"]) == 2
    assert "Test 1" in plan_dict["tests"]
    assert "Test 2" in plan_dict["tests"]

def test_plan_from_dict():
    plan_data = {
        "name": "Test Plan",
        "user": getpass.getuser(),
        "date": datetime.now().isoformat(),
        "tests": ["Test 1", "Test 2"]
    }
    plan = Plan.from_dict(plan_data)
    
    assert plan.name == "Test Plan"
    assert plan.user == getpass.getuser()
    assert len(plan) == 2
    assert "Test 1" in plan
    assert "Test 2" in plan