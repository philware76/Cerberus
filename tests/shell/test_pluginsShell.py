import logging
from contextlib import redirect_stdout
from io import StringIO

import pytest

from Cerberus.cmdShells.equipmentShell import EquipShell
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.productShell import ProductsShell
from Cerberus.cmdShells.testShell import TestsShell
from Cerberus.manager import Manager
from Cerberus.plugins.basePlugin import BasePlugin


def test_cerberus_manager_created(manager):
    assert manager is not None


def test_no_missing_plugins(manager: Manager):
    pluginService = manager.pluginService
    assert len(pluginService.missingPlugins) == 0


@pytest.mark.parametrize("shell_class, plugin_type", [
    (TestsShell, "Test"),
    (EquipShell, "Equip"),
    (ProductsShell, "Product"),
])
def test_getPluginShell(shell_class, plugin_type, manager: Manager):
    shell: PluginsShell = shell_class(manager)

    with StringIO() as buf, redirect_stdout(buf):
        shell.do_list(None)
        output = buf.getvalue()

    # Dynamically access the correct plugin dictionary from the manager
    pluginService = manager.pluginService
    plugin_dict = getattr(pluginService, f"{plugin_type.lower()}Plugins")
    for p in plugin_dict.values():
        plugin: BasePlugin = p
        assert plugin.name in output
        logging.debug(f"{plugin.name} is found in Shell list")

        # This won't run open the plugin shell, only load it and
        # therefore check it can be loaded!
        shell.do_load(plugin.name)

        assert shell.getShell() is not None
        logging.debug(f"{plugin.name} can be loaded")
