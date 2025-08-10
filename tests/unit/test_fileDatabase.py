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
    plan = plan_service.newPlan(plan_name)
    assert plan is not None
    assert plan.name == plan_name, "Plan name should match the created plan name."

    assert plan_service.addTestToPlan("Simple Test #1"), "Adding a valid test to the plan should succeed."
    id = plan_service.savePlan()
    assert id is not None, "Saving the plan should return a valid ID."
    id2 = plan_service.savePlan()
    assert id2 == id, "Saving the same plan should return the same ID."

    plan_service.setTestPlan(id)
    assert plan.name == plan_name, "Plan name should match the created plan name."

# --- New Equipment Tests -------------------------------------------------------------------------------------------


def test_AddMultipleEquipment(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env

    # Upsert several BB60C devices
    bb_ids = []
    for i in range(3):
        serial = f"BB60C-SN-{i}"
        equip_id = db.upsertEquipment(
            equipType="BB60C",
            manufacturer="SignalHound",
            model="BB60C",
            serial=serial,
            version="1.0",
            ip=f"192.168.0.{10+i}",
            port=5025 + i,
            timeout=1000
        )
        assert equip_id is not None, "BB60C upsert should return an ID"
        bb_ids.append(equip_id)

    # Upsert several VSG60C devices
    vsg_ids = []
    for i in range(2):
        serial = f"VSG60C-SN-{i}"
        equip_id = db.upsertEquipment(
            equipType="VSG60C",
            manufacturer="SignalHound",
            model="VSG60C",
            serial=serial,
            version="2.0",
            ip=f"192.168.1.{20+i}",
            port=5024 + i,
            timeout=1500
        )
        assert equip_id is not None, "VSG60C upsert should return an ID"
        vsg_ids.append(equip_id)

    # Ensure IDs are unique
    all_ids = set(bb_ids + vsg_ids)
    assert len(all_ids) == len(bb_ids) + len(vsg_ids), "Equipment IDs should be unique across types"

    # Ensure records stored
    eq_map = {e['serial']: e for e in db._data.get('equipment', [])}
    for s in [f"BB60C-SN-{i}" for i in range(3)]:
        assert s in eq_map, f"Equipment serial {s} should exist"
    for s in [f"VSG60C-SN-{i}" for i in range(2)]:
        assert s in eq_map, f"Equipment serial {s} should exist"


def test_AssignEquipmentToStation(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    # Pick first BB and VSG
    bb_serial = "BB60C-SN-0"
    vsg_serial = "VSG60C-SN-0"

    # Find their IDs
    bb_id = next(e['id'] for e in db._data['equipment'] if e['serial'] == bb_serial)
    vsg_id = next(e['id'] for e in db._data['equipment'] if e['serial'] == vsg_serial)

    assert db.assignEquipmentToStation("BB60C", bb_id), "Should assign BB60C to station"
    assert db.assignEquipmentToStation("VSG60C", vsg_id), "Should assign VSG60C to station"

    station_eq = db.getStationEquipment()
    assert 'BB60C' in station_eq, "Station should have BB60C mapping"
    assert 'VSG60C' in station_eq, "Station should have VSG60C mapping"
    assert station_eq['BB60C']['serial'] == bb_serial, "Stored BB60C serial mismatch"
    assert station_eq['VSG60C']['serial'] == vsg_serial, "Stored VSG60C serial mismatch"


def test_EquipmentCalibrationFields(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    serial = "BB60C-CAL-1"
    cal_date = "2024-01-15"
    cal_due = "2025-01-15"
    eid = db.upsertEquipment(
        equipType="BB60C",
        manufacturer="SignalHound",
        model="BB60C",
        serial=serial,
        version="1.1",
        ip="192.168.2.10",
        port=5025,
        timeout=1200,
        calibration_date=cal_date,
        calibration_due=cal_due
    )
    assert eid is not None, "Equipment insert with calibration should return ID"

    # Update with new due date only (same serial)
    new_due = "2025-06-30"
    eid2 = db.upsertEquipment(
        equipType="BB60C",
        manufacturer="SignalHound",
        model="BB60C",
        serial=serial,
        version="1.1",
        ip="192.168.2.10",
        port=5025,
        timeout=1200,
        calibration_date=cal_date,
        calibration_due=new_due
    )
    assert eid == eid2, "Upsert should return same ID for existing serial"

    # Find record
    rec = next(e for e in db._data['equipment'] if e['serial'] == serial)
    assert rec.get('calibration_date') == cal_date, "Calibration date should persist"
    assert rec.get('calibration_due') == new_due, "Calibration due date should update"
