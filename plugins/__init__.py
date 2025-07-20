import pluggy

hookimpl = pluggy.HookimplMarker("cerberus")
hookspec = pluggy.HookspecMarker("cerberus")

def singleton(cls):
    _instances = {}

    def get_instance(*args, **kwargs):
        if cls not in _instances:
            _instances[cls] = cls(*args, **kwargs)

        return _instances[cls]

    return get_instance