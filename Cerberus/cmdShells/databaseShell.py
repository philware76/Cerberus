from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.database import Database
from Cerberus.manager import Manager


class DatabaseShell(BaseShell):
    intro = "Cerberus Database Shell. Type help or ? to list commands."
    prompt = "Database> "

    def __init__(self, manager:Manager):
        super().__init__(manager)

    def do_get_chamber(self, arg):
        "Get the chamber class name for this station from the database"
        if not self.manager or not hasattr(self.manager, 'database') or not self.manager.database:
            print("Database not open. Use 'open' first.")
            return
        chamber = self.manager.database.get_station_chamber_type()
        print(f"Chamber class: {chamber}")

    def do_set_chamber(self, arg):
        "Set the chamber class name for this station in the database. Usage: set_chamber <ClassName>"
        if not self.manager or not hasattr(self.manager, 'database') or not self.manager.database:
            print("Database not open. Use 'open' first.")
            return
        if not arg:
            print("Please provide a chamber class name.")
            return
        self.db.set_station_chamber_type(arg)
        print(f"Chamber class set to: {arg}")

