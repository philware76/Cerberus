from cmdShells.pluginsShell import PluginsShell
from testManager import TestManager
from cmdShells.common import displayPluginCategory, getInt
from cmdShells.baseShell import BaseShell
from cmdShells.basePluginShell import BasePluginShell
from plugins.tests.baseTest import BaseTest
from testRunner import TestRunner



class TestsShell(PluginsShell):
    def __init__(self, manager:TestManager):
        super().__init__(manager, manager.testPlugins, "Test")


# class TestsShell(BaseShell):
#     intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
#     prompt = 'Tests> '

#     def __init__(self, manager: TestManager):
#         super().__init__()

#         self.manager = manager

#     def do_list(self, arg):
#         """List all of the Tests"""
#         displayPluginCategory("Test", self.manager.testPlugins)

#     def do_load(self, name):
#         """Loads a test"""
#         try:
#             if idx := getInt(name):
#                 name = list(self.manager.testPlugins.keys())[idx]
            
#             test: BaseTest = self.manager.testPlugins[name]
    
#             TestShell(test, self.manager).cmdloop()
#         except KeyError:
#             print(f"Unknown test: {name}")

class TestShell(BasePluginShell):
    def __init__(self, test: BaseTest, manager: TestManager):
        TestShell.intro = f"Welcome to Cerberus {test.name} Test System. Type help or ? to list commands.\n"
        TestShell.prompt = f"{test.name}> "

        super().__init__(test, manager)
        self.test: BaseTest = test
        self.manager : TestManager = manager

    def do_run(self, arg):
        """Run the loaded test"""
        testRunner = TestRunner(self.manager)
        testRunner.runTest(self.test)