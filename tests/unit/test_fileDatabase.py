from typing import Tuple

import pytest

from Cerberus.chamberService import ChamberService
from Cerberus.database.fileDatabase import FileDatabase
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


# --- Calibration Cable Tests ------------------------------------------------------------------------------------

def test_CalCable_Insert_And_Fetch(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, *_ = db_env
    tx_serial = "TXCAL-001"
    rx_serial = "RXCAL-001"
    tx_id = db.upsertCalCable('TX', tx_serial, method='chebyshev', degree=3, domain=(100.0, 6000.0), coeffs=[0.1, 0.01, -0.0005, 0.00001])
    rx_id = db.upsertCalCable('RX', rx_serial, method='chebyshev', degree=2, domain=(100.0, 6000.0), coeffs=[0.2, 0.02, -0.0007])
    assert tx_id is not None and rx_id is not None
    tx_row = db.fetchCalCable('TX')
    rx_row = db.fetchCalCable('RX')
    assert tx_row is not None and rx_row is not None
    assert tx_row.get('serial') == tx_serial
    assert rx_row.get('serial') == rx_serial
    assert tx_row.get('degree') == 3
    assert rx_row.get('degree') == 2


def test_CalCable_Update(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, *_ = db_env
    # Update TX cable with new coeffs and degree
    new_coeffs = [0.15, 0.012, -0.0004, 0.00002, -0.0000001]
    tx_id2 = db.upsertCalCable('TX', 'TXCAL-001', method='chebyshev', degree=4, domain=(50.0, 8000.0), coeffs=new_coeffs)
    assert tx_id2 is not None
    tx_row = db.fetchCalCable('TX')
    assert tx_row is not None
    assert tx_row.get('degree') == 4
    assert tx_row.get('domain') == [50.0, 8000.0]
    assert tx_row.get('coeffs') == new_coeffs


def test_CalCable_List(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, *_ = db_env
    lst = db.listCalCables()
    roles = {c['role'] for c in lst}
    assert roles == {"TX", "RX"}


def test_CalCable_LossFn(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, *_ = db_env
    loss_fn, meta = db.buildCalCableLossFn('TX')
    assert callable(loss_fn)
    v = loss_fn(1000.0)
    assert isinstance(v, float)
    # Evaluate multiple points to ensure function responds
    for f in [100.0, 500.0, 2500.0, 6000.0]:
        val = loss_fn(f)
        assert isinstance(val, float)


def test_CalCable_Delete(db_env: Tuple[FileDatabase, PluginService, PlanService, ChamberService]):
    db, *_ = db_env
    assert db.deleteCalCable('RX')
    assert db.fetchCalCable('RX') is None
    # Recreate RX for potential later tests
    db.upsertCalCable('RX', 'RXCAL-002', method='chebyshev', degree=2, domain=(100.0, 6000.0), coeffs=[0.25, 0.015, -0.0006])
