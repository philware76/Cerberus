from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.manager import Manager


class DatabaseShell(BaseShell):
    intro = "Cerberus Database Shell. Type help or ? to list commands."
    prompt = "Database> "

    def __init__(self, manager:Manager):
        super().__init__(manager)
        self.db = manager.db

    def do_get_chamber(self, arg):
        "Get the chamber class name for this station from the database"
        chamber = self.db.get_ChamberForStation()
        print(f"Chamber class: {chamber}")

    def do_set_chamber(self, arg):
        "Set the chamber class name for this station in the database. Usage: set_chamber <ClassName>"
        if not arg:
            print("Please provide a chamber class name.")
            return
        self.db.set_ChamberForStation(arg)
        print(f"Chamber class set to: {arg}")

