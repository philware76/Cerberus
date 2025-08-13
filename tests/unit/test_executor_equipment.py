import pytest

from Cerberus.executor import Executor
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.equipment.simpleEquip.simple1Equipment import \
    SimpleEquip1
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.pluginService import PluginService


# --- Helpers -----------------------------------------------------------------------------------------------------
class _FakeEquip(BaseEquipment):
    def __init__(self):
        super().__init__("Fake Equipment (Not Registered)")


class _DummyTestMissingEquip(BaseTest):
    def __init__(self):
        super().__init__("Dummy Missing Equip Test")
        # Require an equipment type that is NOT registered as a plugin
        self._addRequirements([_FakeEquip])

    def run(self):
        # Should not be called when equipment is missing
        assert False, "run() should not be invoked when equipment is missing"


# --- Tests -------------------------------------------------------------------------------------------------------

def test_executor_returns_false_when_missing_equipment():
    ps = PluginService()
    ex = Executor(ps)
    test = _DummyTestMissingEquip()

    ok = ex.runTest(test)
    assert ok is False


def test_executor_returns_false_when_equipment_initialise_fails(monkeypatch):
    ps = PluginService()
    ex = Executor(ps)

    # Use an existing test that requires SimpleEquip1 (e.g., "Simple Test #1")
    test = ps.findTest("Simple Test #1")
    assert test is not None, "Expected built-in 'Simple Test #1' to be available"

    # Force SimpleEquip1.initialise to fail to simulate device offline
    def _fail_initialise(self, init=None):
        return False

    monkeypatch.setattr(SimpleEquip1, "initialise", _fail_initialise)

    ok = ex.runTest(test)
    assert ok is False
    assert ok is False
