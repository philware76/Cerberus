
from typing import List

import pytest

from Cerberus.chamberService import ChamberService
from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.plan import Plan
from Cerberus.planService import PlanService
from Cerberus.pluginService import PluginService

TestPlanName1 = "Test Plan 1"

@pytest.fixture(scope="module")
def db_env():
    db = FileDatabase("test.db")
    pluginService = PluginService()
    plan_service = PlanService(pluginService, db)
    chamber_service = ChamberService(pluginService, db)
    return db, pluginService, plan_service, chamber_service


def test_WipeFileDatabase(db_env):
    db, _, _, _ = db_env
    db._data = {}
    db._save_data()
    plans = db.listTestPlans()
    assert len(plans) == 0, "Database should be empty after wipe."

def test_SetGetChamber(db_env):
    _, _, _, chamber_service = db_env
    chamber = "CT200"
    assert chamber_service.saveChamber(chamber)
    retrieved_chamber = chamber_service.loadChamber()
    assert retrieved_chamber == chamber

def test_SaveEmptyPlan(db_env):
    _, _, plan_service, _ = db_env
    id = plan_service.newPlan(TestPlanName1)
    assert id is not None
    assert id == 1

def test_SetGetTestPlanId(db_env):
    _, _, plan_service, _ = db_env
    plans:List[Plan] = plan_service.listTestPlans()
    assert plans[0].name == TestPlanName1

def test_SaveLoadPlan(db_env):
    _, _, plan_service, _ = db_env
    plan_name = "Test Plan"
    plan_service.newPlan(plan_name)
    assert plan_service._plan.name == plan_name
    plan_service.addTestToPlan("Simple Test #1")
    id = plan_service.savePlan()
    assert id is not None
    plan_service.setTestPlan(id)
    assert plan_service._plan.name == plan_name


