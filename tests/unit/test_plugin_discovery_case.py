import pytest

from Cerberus.pluginService import PluginService


def test_plugin_case_insensitive_access(pluginService: PluginService):
    ps = pluginService
    if len(ps.testPlugins) == 0:
        pytest.skip("No test plugins discovered to validate case-insensitive access.")
    name = next(iter(ps.testPlugins))
    plugin_lower = ps.testPlugins[name.lower()]
    plugin_upper = ps.testPlugins[name.upper()]
    assert plugin_lower is plugin_upper is ps.testPlugins[name]
