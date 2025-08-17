import cmd

from Cerberus.manager import Manager


class BaseShell(cmd.Cmd):
    def __init__(self, manager: Manager):
        super().__init__()
        if manager is None:
            raise ValueError("Manager instance must be provided")

        self.manager = manager

    def do_quit(self, arg):
        """Quits the shell immediately"""
        print("Exiting Cerberus shell...")
        raise KeyboardInterrupt()

    def do_exit(self, arg) -> bool:
        """Exit the Cerberus Test shell"""
        return True

    def emptyline(self) -> bool:
        return False
