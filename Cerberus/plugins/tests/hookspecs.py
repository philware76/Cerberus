### Hooks Specification File for the Test Plugins
###
### This file defines the hookspecs for the test plugins.
### It is used by the PluginDiscovery class to dynamically load and register "Test" plugins.
###
### The hookspecs define the methods that plugins must implement to be recognized as valid test plugins.
### 
### This file should be placed in the `plugins/tests` directory and named `hookspecs.py`.
### The name of the Test plugins need to end with `Test.py` to be recognized by the PluginDiscovery for Tests class.
###

from plugins.basePlugin import hookspec

class TestSpec:
    @hookspec
    def createTestPlugin():
        """create a test plugin"""
        pass
