from testManager import TestManager

def displayPlugins(manager: TestManager):
    displayPluginCategory("Equipment", manager.equipPlugins)
    displayPluginCategory("Product", manager.productPlugins)
    displayPluginCategory("Test", manager.testPlugins)


def displayPluginCategory(category_name, plugins):
    print(f"Available {category_name} plugins:")
    idx = 0
    for name, plugin in plugins.items():
        print(f" #{idx} - {name}: '{plugin.name}'")
        idx += 1

    print("")

def getInt(text:str) -> int:
    try:
        return int(text)
    except ValueError:
        return None