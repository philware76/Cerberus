from typing import List, Tuple

import pytest

from Cerberus.chamberService import ChamberService
from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.equipmentService import EquipmentService
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
    assert retrieved_chamber is not None
    assert retrieved_chamber.name == chamber, "Retrieved chamber should match the saved chamber type."


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

    # Upsert several Spectrum Analysers (role SPECAN)
    sa_ids = []
    for i in range(3):
        serial = f"SPECAN-SN-{i}"
        equip_id = db.upsertEquipment(
            equipRole="SPECAN",
            manufacturer="Acme",
            model="SpecModelX",
            serial=serial,
            version="1.0",
            ip=f"192.168.0.{10+i}",
            port=6000 + i,
            timeout=1000
        )
        assert equip_id is not None, "SPECAN upsert should return an ID"
        sa_ids.append(equip_id)

    # Upsert several Signal Generators (role SIGGEN)
    sg_ids = []
    for i in range(2):
        serial = f"SIGGEN-SN-{i}"
        equip_id = db.upsertEquipment(
            equipRole="SIGGEN",
            manufacturer="Acme",
            model="SigGenPro",
            serial=serial,
            version="2.0",
            ip=f"192.168.1.{20+i}",
            port=7000 + i,
            timeout=1500
        )
        assert equip_id is not None, "SIGGEN upsert should return an ID"
        sg_ids.append(equip_id)

    all_ids = set(sa_ids + sg_ids)
    assert len(all_ids) == len(sa_ids) + len(sg_ids), "Equipment IDs should be unique across roles"

    eq_map = {e['serial']: e for e in db._data.get('equipment', [])}
    for s in [f"SPECAN-SN-{i}" for i in range(3)]:
        assert s in eq_map, f"Equipment serial {s} should exist"
    for s in [f"SIGGEN-SN-{i}" for i in range(2)]:
        assert s in eq_map, f"Equipment serial {s} should exist"


def test_AssignEquipmentToStation(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    spec_serial = "SPECAN-SN-0"
    sig_serial = "SIGGEN-SN-0"

    spec_id = next(e['id'] for e in db._data['equipment'] if e['serial'] == spec_serial)
    sig_id = next(e['id'] for e in db._data['equipment'] if e['serial'] == sig_serial)

    assert db.assignEquipmentToStation("SPECAN", spec_id), "Should assign SPECAN to station"
    assert db.assignEquipmentToStation("SIGGEN", sig_id), "Should assign SIGGEN to station"

    station_eq = db.getStationEquipment()
    assert 'SPECAN' in station_eq, "Station should have SPECAN mapping"
    assert 'SIGGEN' in station_eq, "Station should have SIGGEN mapping"
    assert station_eq['SPECAN']['serial'] == spec_serial, "Stored SPECAN serial mismatch"
    assert station_eq['SIGGEN']['serial'] == sig_serial, "Stored SIGGEN serial mismatch"


def test_EquipmentCalibrationFields(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    serial = "SPECAN-CAL-1"
    cal_date = "2024-01-15"
    cal_due = "2025-01-15"
    eid = db.upsertEquipment(
        equipRole="SPECAN",
        manufacturer="Acme",
        model="SpecModelX",
        serial=serial,
        version="1.1",
        ip="192.168.2.10",
        port=6100,
        timeout=1200,
        calibration_date=cal_date,
        calibration_due=cal_due
    )
    assert eid is not None, "Equipment insert with calibration should return ID"

    new_due = "2025-06-30"
    eid2 = db.upsertEquipment(
        equipRole="SPECAN",
        manufacturer="Acme",
        model="SpecModelX",
        serial=serial,
        version="1.1",
        ip="192.168.2.10",
        port=6100,
        timeout=1200,
        calibration_date=cal_date,
        calibration_due=new_due
    )
    assert eid == eid2, "Upsert should return same ID for existing serial"

    rec = next(e for e in db._data['equipment'] if e['serial'] == serial)
    assert rec.get('calibration_date') == cal_date, "Calibration date should persist"
    assert rec.get('calibration_due') == new_due, "Calibration due date should update"


def test_EquipmentService_registration_and_assignment(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, pluginService, _, _ = db_env
    equipService = EquipmentService(pluginService, db)

    # Register (upsert) devices via service using roles
    sig_id = db.upsertEquipment(
        equipRole="SIGGEN",
        manufacturer="Acme",
        model="SigModelAlpha",
        serial="SIGGEN-SVC-1",
        version="3.0",
        ip="10.0.0.10",
        port=7100,
        timeout=2000
    )
    spec_id = db.upsertEquipment(
        equipRole="SPECAN",
        manufacturer="Acme",
        model="SpecModelBeta",
        serial="SPECAN-SVC-1",
        version="3.1",
        ip="10.0.0.11",
        port=6200,
        timeout=2200
    )
    assert sig_id is not None and spec_id is not None, "Service upserts should return IDs"

    assert equipService.assignSignalGenerator(sig_id), "Should assign SIGGEN via EquipmentService"
    assert equipService.assignSpectrumAnalyser(spec_id), "Should assign SPECAN via EquipmentService"

    assigned = equipService.getAssigned()
    assert 'SIGGEN' in assigned and 'SPECAN' in assigned, "Both roles should be assigned"
    assert assigned['SIGGEN']['id'] == sig_id, "SIGGEN ID mismatch"
    assert assigned['SPECAN']['id'] == spec_id, "SPECAN ID mismatch"
