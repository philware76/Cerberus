from typing import Tuple

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

# --- Equipment Tests (station-centric) ---------------------------------------------------------------------------


def test_AddMultipleEquipment(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    sa_ids = []
    for i in range(3):
        serial = f"SPECAN-SN-{i}"
        equip_id = db.upsertEquipment(
            manufacturer="Acme",
            model="SpecModelX",
            serial=serial,
            version="1.0",
            ip=f"192.168.0.{10+i}",
            port=6000 + i,
            timeout=1000
        )
        assert equip_id is not None
        sa_ids.append(equip_id)
    sg_ids = []
    for i in range(2):
        serial = f"SIGGEN-SN-{i}"
        equip_id = db.upsertEquipment(
            manufacturer="Acme",
            model="SigGenPro",
            serial=serial,
            version="2.0",
            ip=f"192.168.1.{20+i}",
            port=7000 + i,
            timeout=1500
        )
        assert equip_id is not None
        sg_ids.append(equip_id)
    all_ids = set(sa_ids + sg_ids)
    assert len(all_ids) == len(sa_ids) + len(sg_ids)
    eq_map = {e['serial']: e for e in db._data.get('equipment', [])}
    for s in [f"SPECAN-SN-{i}" for i in range(3)]:
        assert s in eq_map
    for s in [f"SIGGEN-SN-{i}" for i in range(2)]:
        assert s in eq_map


def test_AttachEquipmentToStation(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    # Attach first two equipment entries
    equipment = list(db._data.get('equipment', []))
    assert len(equipment) >= 2
    first_id = equipment[0]['id']
    second_id = equipment[1]['id']
    assert db.attachEquipmentToStation(first_id)
    assert db.attachEquipmentToStation(second_id)
    attached = db.listStationEquipment()
    attached_ids = {e['id'] for e in attached}
    assert first_id in attached_ids and second_id in attached_ids


def test_EquipmentCalibrationFields(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    serial = "SPECAN-CAL-1"
    cal_date = "2024-01-15"
    cal_due = "2025-01-15"
    eid = db.upsertEquipment(
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
    assert eid is not None
    new_due = "2025-06-30"
    eid2 = db.upsertEquipment(
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
    assert eid == eid2
    rec = next(e for e in db._data['equipment'] if e['serial'] == serial)
    assert rec.get('calibration_date') == cal_date
    assert rec.get('calibration_due') == new_due


def test_EquipmentService_register_and_attach(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, pluginService, _, _ = db_env
    equipService = EquipmentService(pluginService, db)
    sig_id = db.upsertEquipment(
        manufacturer="Acme",
        model="SigModelAlpha",
        serial="SIGGEN-SVC-1",
        version="3.0",
        ip="10.0.0.10",
        port=7100,
        timeout=2000
    )
    spec_id = db.upsertEquipment(
        manufacturer="Acme",
        model="SpecModelBeta",
        serial="SPECAN-SVC-1",
        version="3.1",
        ip="10.0.0.11",
        port=6200,
        timeout=2200
    )
    assert sig_id is not None and spec_id is not None
    assert equipService.attach(sig_id)
    assert equipService.attach(spec_id)
    attached_models = {e['model'] for e in equipService.listAttached()}
    assert "SigModelAlpha" in attached_models and "SpecModelBeta" in attached_models


def test_FetchEquipmentByModel_not_attached(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    serial = "FETCH-SN-1"
    model = "FetchModelA"
    eid = db.upsertEquipment(
        manufacturer="Acme",
        model=model,
        serial=serial,
        version="0.1",
        ip="192.168.50.10",
        port=9000,
        timeout=500
    )
    assert eid is not None
    # Not attached yet, should return None
    rec = db.fetchStationEquipmentByModel(model)
    assert rec is None


def test_FetchEquipmentByModel_after_attach(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, _, _, _ = db_env
    serial = "FETCH-SN-2"
    model = "FetchModelB"
    eid = db.upsertEquipment(
        manufacturer="Acme",
        model=model,
        serial=serial,
        version="0.2",
        ip="192.168.50.11",
        port=9001,
        timeout=600
    )
    assert eid is not None
    assert db.attachEquipmentToStation(eid)
    rec = db.fetchStationEquipmentByModel(model)
    assert rec is not None
    assert rec.get('serial') == serial
    assert rec.get('model') == model
