
from typing import List, Tuple

import pytest

from Cerberus.chamberService import ChamberService
from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.plan import Plan
from Cerberus.planService import PlanService
from Cerberus.pluginService import PluginService

TestPlanName1 = "Test Plan 1"


@pytest.fixture(scope="module")
def db_env() -> Tuple[FileDatabase, PluginService, PlanService, ChamberService]:
    db = FileDatabase("test.db")
    pluginService = PluginService()
    plan_service = PlanService(pluginService, db)
    chamber_service = ChamberService(pluginService, db)
    return db, pluginService, plan_service, chamber_service


def test_WipeFileDatabase(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    db._data = {}
    db._save_data()

    plans = db.listTestPlans()
    assert len(plans) == 0, "Database should be empty after wipe."


def test_SetGetChamber(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    _, _, _, chamber_service = db_env
    chamber = "CT200"
    assert chamber_service.saveChamber(chamber), "CT200 should be an available chamber type."

    retrieved_chamber = chamber_service.loadChamber()
    assert retrieved_chamber == chamber, "Retrieved chamber should match the saved chamber type."


def test_SaveEmptyPlan(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    _, _, plan_service, _ = db_env
    plan_service.newPlan(TestPlanName1)

    id = plan_service.savePlan()

    assert id is not None, "New plan should return a valid ID."
    assert id == 1, f"New plan ID should be 1, not {id} on a wiped database."


def test_SetGetTestPlanId(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    _, _, plan_service, _ = db_env
    plans = plan_service.listTestPlans()
    id, plan = plans[0]
    assert plan.name == TestPlanName1, "First plan should match the created plan name."


def test_SaveLoadPlan(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    _, _, plan_service, _ = db_env
    plan_name = "Test Plan"
    plan_service.newPlan(plan_name)
    assert plan_service._plan.name == plan_name, "Plan name should match the created plan name."

    assert plan_service.addTestToPlan("Simple Test #1"), "Adding a valid test to the plan should succeed."
    id = plan_service.savePlan()
    assert id is not None, "Saving the plan should return a valid ID."

    plan_service.setTestPlan(id)

    assert plan_service._plan.name == plan_name, "Plan name should match the created plan name."
