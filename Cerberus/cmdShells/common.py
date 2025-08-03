from typing import Dict

from Cerberus.plugins.basePlugin import BasePlugin


def displayPluginCategory(category_name, plugins: Dict[str, BasePlugin]):
    print(f"Available {category_name} plugins:")
    idx = 0
    for plugin in list(plugins.values()):
        print(f" #{idx}: '{plugin.name}' [{plugin.__class__.__base__.__name__.replace('Base', '')}]")
        idx += 1

    print("")

def getInt(text:str) -> int:
    try:
        return int(text)
    except ValueError:
        return None
    except ValueError:
        return None