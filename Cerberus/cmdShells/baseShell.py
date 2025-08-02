import cmd


class BaseShell(cmd.Cmd):
    def __init__(self, manager=None):
        super().__init__()
        if manager is None:
            raise ValueError("Manager instance must be provided")   
        
        self.manager = manager

    def do_quit(self, arg):
        """Quits the shell immediately"""
        raise KeyboardInterrupt()

    def do_exit(self, arg):
        """Exit the Cerberus Test shell"""
        return True
    
    def emptyline(self):
        pass