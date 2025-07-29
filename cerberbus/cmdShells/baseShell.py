import cmd


class BaseShell(cmd.Cmd):
    def do_quit(self, arg):
        """Quits the shell immediately"""
        raise KeyboardInterrupt()

    def do_exit(self, arg):
        """Exit the Cerberus Test shell"""
        return True