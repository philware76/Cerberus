import pluggy

hookimpl = pluggy.HookimplMarker("cerberus")

@hookimpl
def register_test():
    print("[OCXOCalibration] register_test() called")
    return "ocxoCal"