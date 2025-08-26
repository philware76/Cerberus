from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.manager import Manager


class DatabaseShell(BaseShell):
    intro = "Cerberus Database Shell. Type help or ? to list commands."
    prompt = "Database> "

    def __init__(self, manager: Manager):
        super().__init__(manager)

    def do_wipeDB(self, arg):
        """Drop equipment, station and testplans tables (DANGEROUS)."""
        confirm = input("Type 'YES' to confirm wiping the database: ")
        if confirm != 'YES':
            print("Aborted.")
            return

        self.manager.db.wipe_DB()
