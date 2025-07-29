from typing import Dict
from plugins.basePlugin import BasePlugin
from testManager import TestManager

def displayPluginCategory(category_name, plugins: Dict[str, BasePlugin]):
    print(f"Available {category_name} plugins:")
    idx = 0
    for plugin in list(plugins.values()):
        print(f" #{idx}: '{plugin.name}'")
        idx += 1

    print("")

def getInt(text:str) -> int:
    try:
        return int(text)
    except ValueError:
        return None