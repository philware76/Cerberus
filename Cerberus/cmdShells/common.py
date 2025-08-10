import ipaddress
from collections.abc import Mapping
from typing import Dict  # backward compatibility if used elsewhere

from Cerberus.plugins.basePlugin import BasePlugin


def displayPluginCategory(category_name: str, plugins: Mapping[str, BasePlugin]):
    print(f"Available {category_name} plugins:")
    idx = 0
    for plugin in plugins.values():
        base_cls = plugin.__class__.__base__
        base_name = base_cls.__name__.replace('Base', '') if base_cls and hasattr(base_cls, '__name__') else plugin.__class__.__name__
        print(f" #{idx}: '{plugin.name}' [{base_name}]")
        idx += 1

    print("")


def getInt(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False
