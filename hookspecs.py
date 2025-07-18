# cerberus/hookspecs.py
import pluggy

hookspec = pluggy.HookspecMarker("cerberus")

class TestSpec:
    @hookspec
    def register_test():
        """Register a test plugin."""

    @hookspec
    def other_test():
        """Other a test plugin."""