import logging

from testManager import TestManager

def displayPlugins(manager: TestManager):
    displayPluginCategory("Equipment", manager.equipPlugins)
    displayPluginCategory("Product", manager.productPlugins)
    displayPluginCategory("Test", manager.testPlugins)


def displayPluginCategory(category_name, plugins):
    logging.info(f"Available {category_name} plugins:")
    for name, plugin in plugins.items():
        logging.info(f" - {name}: '{plugin.name}'")

    logging.info("")