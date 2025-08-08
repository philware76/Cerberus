from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.manager import Manager


class DatabaseShell(BaseShell):
    intro = "Cerberus Database Shell. Type help or ? to list commands."
    prompt = "Database> "

    def __init__(self, manager: Manager):
        super().__init__(manager)

    def do_get_chamber(self, arg):
        "Get the chamber class name for this station from the database"
        chamber = self.manager.chamberService.loadChamber()
        print(f"Chamber class: {chamber}")

    def do_set_chamber(self, arg):
        "Set the chamber class name for this station in the database. Usage: set_chamber <ClassName>"
        if not arg:
            print("Please provide a chamber class name.")
            return

        if self.manager.chamberService.saveChamber(arg):
            print(f"Chamber class set to: {arg}")
        else:
            print(f"Could not set Chamber type to {arg}")
