### Hooks Specification File for the Product Plugins
###
### This file defines the hookspecs for the product plugins.
### It is used by the PluginDiscovery class to dynamically load and register "Product" plugins.
###
### The hookspecs define the methods that plugins must implement to be recognized as valid product plugins.
###
### This file should be placed in the `plugins/products` directory and named `hookspecs.py`.
### The name of the Product plugins need to end with `Product.py` to be recognized by the PluginDiscovery for Product class.
###

from plugins.basePlugin import hookspec

class ProductSpec:
    @hookspec
    def createProductPlugin():
        """create an product plugin"""
        pass
