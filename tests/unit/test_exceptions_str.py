from Cerberus.exceptions import (CerberusException, EquipmentError,
                                 ExecutionError, PluginError, TestError)


def test_exception_str_formats():
    ex = CerberusException("base")
    assert "CerberusException" in str(ex)
    ex2 = PluginError("plugin")
    assert "PluginError" in str(ex2)
    ex3 = TestError("test")
    assert "TestError" in str(ex3)
    ex4 = EquipmentError("equip")
    assert "EquipmentError" in str(ex4)
    ex5 = ExecutionError("exec")
    assert "ExecutionError" in str(ex5)
