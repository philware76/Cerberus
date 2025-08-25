import pytest

from Cerberus.database.fileDB import FileDB
from Cerberus.planService import PlanService


class EmptyPluginService:
    def __init__(self):
        self.testPlugins = {}

    def findTest(self, name: str):
        return None


# THIS TEST NEEDS FIXED FOR THE NEW CERBERUS DATABASE API


def natest_plan_save_crc_no_change(tmp_path):
    db = FileDB(str(tmp_path / "db.json"))
    ps = PlanService(EmptyPluginService(), db)
    ps.newPlan("Alpha")
    first_id = ps.savePlan()
    assert first_id is not None
    second_id = ps.savePlan()  # no modifications; CRC path
    assert second_id == first_id


def natest_plan_set_invalid_id(tmp_path):
    db = FileDatabase(str(tmp_path / "db.json"))
    ps = PlanService(EmptyPluginService(), db)
    ps.newPlan("Alpha")
    ps.savePlan()
    assert ps.setTestPlan(999) is False


def natest_add_unknown_test_rejected(tmp_path):
    db = FileDatabase(str(tmp_path / "db.json"))
    ps = PlanService(EmptyPluginService(), db)
    ps.newPlan("Alpha")
    ps.savePlan()
    assert ps.addTestToPlan("NonExistentTest") is False
