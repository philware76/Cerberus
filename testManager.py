# cerberus/testmanager.py
import pluggy
import hookspecs
from testDiscovery import TestDiscovery

class TestManager:
    def __init__(self):
        self.pm = pluggy.PluginManager("cerberus")
        self.pm.add_hookspecs(hookspecs.TestSpec)
        self.testDiscovery = TestDiscovery(self.pm)
        self.load_all_plugins()

    def load_all_plugins(self):
        testFolders = self.testDiscovery.getTestFolders()
        self.testDiscovery.loadTestPlugins(testFolders)


if __name__ == "__main__":
    manager = TestManager()
    stuff = manager.pm.hook.register_test()
    other = manager.pm.hook.other_test()
    print(stuff)
    print(other)
    print("[Cerberus] All test plugins loaded.")

