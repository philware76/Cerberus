import pluggy

hookimpl = pluggy.HookimplMarker("cerberus")

@hookimpl
def register_test():
    print("[TxLevelTest] register_test() called")
    return "txLevel"

@hookimpl
def other_test():
    print("[TxLevelTest] other_test() called")
    return "otherTxLevel"