import json
import shlex
from contextlib import redirect_stdout
from io import StringIO
from typing import Any

from Cerberus.cmdShells.basePluginShell import BasePluginShell
from Cerberus.plugins.baseParameters import BaseParameters, NumericParameter
from Cerberus.plugins.basePlugin import BasePlugin

groupName = "RF Params"
g1Param1 = NumericParameter("power", 10.0, "dBm")
g1Param2 = NumericParameter("freq", 2.4e9, "Hz")

g2Param1 = NumericParameter("power", 20.0, "dBm")
g2Param2 = NumericParameter("freq", 2.0e9, "Hz")

group1 = BaseParameters(groupName)    \
    .addParameter(g1Param1)  \
    .addParameter(g1Param2)

group2 = BaseParameters(groupName)    \
    .addParameter(g2Param1)  \
    .addParameter(g2Param2)


class DummyPlugin(BasePlugin):
    def __init__(self):
        super().__init__("Dummy")
        self.addParameterGroup(group1)

    def initialise(self, init: Any = None) -> bool:
        '''Initialises a plugin with some initialisation meta data'''
        return True

    def configure(self, config: Any = None) -> bool:
        '''Provides the configuration for the plugin'''
        return True

    def finalise(self) -> bool:
        '''finalises a plugin'''
        return True


class DummyManager:
    pass


def test_BasePluginShell():
    plugin = DummyPlugin()
    manager = DummyManager()
    shell = BasePluginShell(plugin, manager)

    # Test txtParams
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_txtParams("")
        output = buf.getvalue()
    assert groupName in output
    assert g1Param1.name in output
    assert g1Param2.name in output

    # Test listGroups
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_listGroups("")
        output = buf.getvalue()
    assert groupName in output

    # Test getGroupParams
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_getGroupParams(groupName)
        output = buf.getvalue()
    assert '"power"' in output
    assert '"value": 10.0' in output

    # Test getGroupParams with invalid group
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_getGroupParams("NoSuchGroup")
        output = buf.getvalue()
    assert "does not exist" in output

    # Test setGroupParams
    line = json.dumps(group2.to_dict())
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_setGroupParams(line)
        output = buf.getvalue()
    assert "New RF Params parameters" in output
    assert str(g2Param1.value) in output

    # Confirm plugin parameter actually updated
    updated = plugin._groupParams["RF Params"]
    assert isinstance(updated["power"], NumericParameter)
    assert updated["power"].value == g2Param1.value
    assert updated["freq"].value == g2Param2.value
    assert isinstance(updated["power"], NumericParameter)
    assert updated["power"].value == g2Param1.value
    assert updated["freq"].value == g2Param2.value
    assert updated["freq"].value == g2Param2.value
