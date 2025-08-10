import getpass
from datetime import datetime

from Cerberus.common import calcCRC
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


def test_plan_crc_changes_on_add():
    p = Plan("CRC Plan")
    crc_initial = calcCRC(p)
    p.append("Example Test 1")
    crc_after_add = calcCRC(p)
    assert crc_after_add != crc_initial, "CRC should change after adding a test"


def test_plan_crc_changes_on_remove_and_restore():
    p = Plan("CRC Plan 2")
    p.append("T1")
    p.append("T2")
    crc_with_two = calcCRC(p)
    p.remove("T2")
    crc_after_remove = calcCRC(p)
    assert crc_after_remove != crc_with_two, "CRC should change after removing a test"
    # Restore same membership
    p.append("T2")
    crc_restored = calcCRC(p)
    assert crc_restored == crc_with_two, "CRC should return to previous value after restoring tests"
