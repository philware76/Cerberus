import pytest

from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.planService import PlanService


class EmptyPluginService:
    def __init__(self):
        self.testPlugins = {}
    def findTest(self, name: str):
        return None


def test_plan_save_crc_no_change(tmp_path):
    db = FileDatabase(str(tmp_path / "db.json"))
    ps = PlanService(EmptyPluginService(), db)
    ps.newPlan("Alpha")
    first_id = ps.savePlan()
    assert first_id is not None
    second_id = ps.savePlan()  # no modifications; CRC path
    assert second_id == first_id


def test_plan_set_invalid_id(tmp_path):
    db = FileDatabase(str(tmp_path / "db.json"))
    ps = PlanService(EmptyPluginService(), db)
    ps.newPlan("Alpha")
    ps.savePlan()
    assert ps.setTestPlan(999) is False


def test_add_unknown_test_rejected(tmp_path):
    db = FileDatabase(str(tmp_path / "db.json"))
    ps = PlanService(EmptyPluginService(), db)
    ps.newPlan("Alpha")
    ps.savePlan()
    assert ps.addTestToPlan("NonExistentTest") is False
