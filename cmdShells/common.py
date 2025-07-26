from typing import Dict
from plugins.basePlugin import BasePlugin
from testManager import TestManager

def displayPlugins(manager: TestManager):
    displayPluginCategory("Equipment", manager.equipment)
    displayPluginCategory("Product", manager.products)
    displayPluginCategory("Test", manager.tests)


def displayPluginCategory(category_name, plugins: Dict[str, BasePlugin]):
    print(f"Available {category_name} plugins:")
    idx = 0
    for _, plugin in plugins.items():
        print(f" #{idx}: '{plugin.name}'")
        idx += 1

    print("")

def getInt(text:str) -> int:
    try:
        return int(text)
    except ValueError:
        return None