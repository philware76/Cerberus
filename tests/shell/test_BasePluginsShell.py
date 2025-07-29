import json
import shlex
from io import StringIO
from contextlib import redirect_stdout
from typing import Any

from cmdShells.basePluginShell import BasePluginShell  # Update import path as needed
from plugins.baseParameters import BaseParameters, BaseParameter, NumericParameter  # Use your actual module paths
from plugins.basePlugin import BasePlugin  # Your real BasePlugin

groupName = "RF Params"
numParam1 = NumericParameter("power", 10.0, "dBm")
numParam2 = NumericParameter("freq", 2.4e9, "Hz")

class DummyPlugin(BasePlugin):
    def __init__(self):
        super().__init__("Dummy")                                           
        self.addParameterGroup(BaseParameters(groupName) \
                .addParameter(numParam1) \
                .addParameter(numParam2))

    def initialise(self, init: Any = None) -> bool:
        '''Initialises a plugin with some initialisation meta data'''
        pass

    def configure(self, config: Any = None) -> bool:
        '''Provides the configuration for the plugin'''
        pass

    def finalise(self) -> bool:
        '''finalises a plugin'''
        pass
    
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
    assert numParam1.name in output
    assert numParam2.name in output

    # Test listGroups
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_listGroups("")
        output = buf.getvalue()
    assert "RF Params" in output

    # Test getGroupParams
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_getGroupParams("RF Params")
        output = buf.getvalue()
    assert '"power"' in output
    assert '"value": 10.0' in output

    # Test getGroupParams with invalid group
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_getGroupParams("NoSuchGroup")
        output = buf.getvalue()
    assert "does not exist" in output

    # Test setGroupParams
    new_params = {
        "power": {"name": "power", "value": 20.0, "units": "dBm"},
        "freq": {"name": "freq", "value": 915e6, "units": "Hz"}
    }
    line = f'"RF Params" \'{json.dumps(new_params)}\''
    with StringIO() as buf, redirect_stdout(buf):
        shell.do_setGroupParams(line)
        output = buf.getvalue()
    assert "New RF Params parameters" in output
    assert "915000000.0" in output

    # Confirm plugin parameter actually updated
    updated = plugin._groupParams["RF Params"]
    assert isinstance(updated["power"], NumericParameter)
    assert updated["power"].value == 20.0
    assert updated["freq"].value == 915e6
