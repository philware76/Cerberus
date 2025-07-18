import importlib.util
import os
from pathlib import Path

TESTS_PLUGIN_FOLDER = Path("plugins") / "tests"

class TestDiscovery:
    def __init__(self, plugin_manager):
        self.pm = plugin_manager

    def getTestFolders(self):
        print("[Cerberus] Looking for Test Plugins in:", TESTS_PLUGIN_FOLDER)
        testFolders = [
            entry.name
            for entry in os.scandir(TESTS_PLUGIN_FOLDER)
                if entry.is_dir() and not entry.name.startswith("__")
        ]
        for testFolder in testFolders:
            yield os.path.join(TESTS_PLUGIN_FOLDER, testFolder)

    def loadTestPlugins(self, testFolders):
        for testFolder in testFolders:
            print(f"[Cerberus] Loading test plugin from: {testFolder}")
            for entry in os.scandir(testFolder):
                if entry.is_file() and entry.name.endswith(".py") and not entry.name.startswith("__"):
                    self.registerTestPlugin(entry.name[:-3], entry.path)

    def registerTestPlugin(self, test_file, test_file_path):
        spec = importlib.util.spec_from_file_location(test_file, test_file_path)
        module = importlib.util.module_from_spec(spec)
    
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"[Cerberus] Failed to load plugin {test_file}: {e}")
            return
        
        if hasattr(module, "register_test"):
            self.pm.register(module, name=test_file)
            print(f"[Cerberus] Plugin loaded: {test_file}")
        else:
            print(f"[Cerberus] Skipped {test_file}: no 'register_test' method found")