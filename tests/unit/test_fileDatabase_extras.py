import json

import pytest

from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.plan import Plan


def test_empty_database_lists_no_plans(tmp_path):
    db = FileDatabase(str(tmp_path / "empty.json"))
    assert db.listTestPlans() == []


def test_delete_plan_clears_current(tmp_path):
    db = FileDatabase(str(tmp_path / "plans.json"))
    p1 = Plan("P1")
    id1 = db.saveTestPlan(p1)
    p2 = Plan("P2")
    id2 = db.saveTestPlan(p2)
    assert id1 and id2
    assert db.set_TestPlanForStation(id2)
    assert db.get_TestPlanForStation().name == "P2"
    assert db.deleteTestPlan(id2)
    assert db.get_TestPlanForStation() is None
    assert db._data.get('testPlanId') is None


def test_get_plan_returns_none_when_missing(tmp_path):
    db = FileDatabase(str(tmp_path / "plans2.json"))
    p1 = Plan("P1")
    id1 = db.saveTestPlan(p1)
    db.set_TestPlanForStation(id1)
    assert db.get_TestPlanForStation().name == "P1"
    # delete underlying entry manually to simulate inconsistency
    db._data['test_plans'] = []
    db._save_data()
    assert db.get_TestPlanForStation() is None


def test_corrupt_json_recovery(tmp_path, caplog):
    path = tmp_path / "corrupt.json"
    path.write_text('{bad json')
    db = FileDatabase(str(path))  # should recover with empty data
    assert db.listTestPlans() == []
    assert any("Error decoding JSON" in rec.message for rec in caplog.records)


def test_unique_ids_after_delete(tmp_path):
    db = FileDatabase(str(tmp_path / "ids.json"))
    ids = []
    for name in ["A", "B", "C"]:
        ids.append(db.saveTestPlan(Plan(name)))
    # delete middle
    db.deleteTestPlan(ids[1])
    new_id = db.saveTestPlan(Plan("D"))
    # Ensure no duplicate IDs in current test_plans
    current_ids = {entry['id'] for entry in db._data.get('test_plans', [])}
    assert len(current_ids) == len(db._data.get('test_plans', []))
    assert new_id in current_ids
