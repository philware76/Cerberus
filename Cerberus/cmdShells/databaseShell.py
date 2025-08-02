from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.database import Database
from Cerberus.manager import Manager


class DatabaseShell(BaseShell):
    intro = "Cerberus Database Shell. Type help or ? to list commands."
    prompt = "Database> "

    def __init__(self, manager:Manager):
        super().__init__(manager)
        self.db = None

    def do_open(self, arg):
        "Open the Cerberus database using cerberus.ini"
        try:
            self.db = Database()
            print("Database connection opened.")
        except Exception as e:
            print(f"Failed to open database: {e}")

    def do_exit(self, arg):
        "Exit the database shell and close the database connection"
        if self.db:
            self.db.close()
            print("Database connection closed.")
        return True

    def do_get_chamber(self, arg):
        "Get the chamber class name for this station from the database"
        if not self.db:
            print("Database not open. Use 'open' first.")
            return
        chamber = self.db.get_station_chamber_type()
        print(f"Chamber class: {chamber}")

    def do_set_chamber(self, arg):
        "Set the chamber class name for this station in the database. Usage: set_chamber <ClassName>"
        if not self.db:
            print("Database not open. Use 'open' first.")
            return
        if not arg:
            print("Please provide a chamber class name.")
            return
        self.db.set_station_chamber_type(arg)
        print(f"Chamber class set to: {arg}")

