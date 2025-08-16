import pytest

from Cerberus.manager import Manager
from Cerberus.plugins.equipment.baseCommsEquipment import BaseCommsEquipment


class FakeEquip(BaseCommsEquipment):
    def __init__(self, name):
        self.name = name
        self.initted = []

    def initComms(self, comms):
        self.initted.append(comms)


class FakePluginService:
    def __init__(self, equips):
        self._map = {e.name: e for e in equips}

    def findEquipment(self, model):
        return self._map.get(model)

    def findEquipType(self, model, type):
        return self._map.get(model)


class FakeDB:
    def __init__(self, raise_error=False):
        self.raise_error = raise_error
    # --- Methods used directly by Manager ---

    def listStationEquipment(self):
        if self.raise_error:
            raise RuntimeError("DB failure")
        return [
            {'model': 'EquipA', 'ip_address': '1.2.3.4', 'port': 111, 'timeout_ms': 200},
            {'model': 'EquipB', 'ip_address': '5.6.7.8', 'port': 222, 'timeout_ms': 300},
            {'model': 'MissingEquip', 'ip_address': '9.9.9.9', 'port': 999, 'timeout_ms': 100},
        ]

    def close(self):
        pass
    # --- Stubbed methods to satisfy service initializations ---

    def get_TestPlanForStation(self):
        return None

    def listCalCables(self):
        return []

    def get_ChamberForStation(self):
        return None

    def saveTestPlan(self, plan):
        return 1

    def set_TestPlanForStation(self, plan_id: int):
        return False

    def listTestPlans(self):
        return []

    def deleteTestPlan(self, plan_id: int):
        return False

    def wipeDB(self):
        return False

    def upsertEquipment(self, *a, **k):
        return 1

    def attachEquipmentToStation(self, equipmentId: int):
        return True

    def fetchStationEquipmentByModel(self, model: str):
        return None

    def set_ChamberForStation(self, chamberType: str):
        return True


def test_manager_applies_comms(monkeypatch):
    fe1 = FakeEquip('EquipA')
    fe2 = FakeEquip('EquipB')
    db = FakeDB()
    m = Manager('StationX', db)
    # Inject fake plugin service and re-run apply
    m.pluginService = FakePluginService([fe1, fe2])
    m._applyPersistedEquipmentComms()
    assert fe1.initted and fe2.initted
    assert fe1.initted[0]['IP Address'] == '1.2.3.4'


def test_manager_apply_handles_exception():
    db = FakeDB(raise_error=True)
    m = Manager('StationX', db)
    # No exception should propagate
    # pluginService will have no equipment; just ensure finalize still works
    m.finalize()
