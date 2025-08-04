from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.manager import Manager


class ManagerShell(BaseShell):
    intro = "Cerberus Manager Shell. Type help or ? to list commands."
    prompt = "Manager> "

    def __init__(self, manager:Manager):
        super().__init__(manager)
        self.chamberService = manager.chamberService
        self.planService = manager.planService

    def do_setChamber(self, arg):
        """Sets the chamber class name for this station in the database. Usage: set_chamber <ClassName>"""
        if not arg:
            print("Please provide a chamber class name.")
            return

        if self.chamberService.saveChamber(arg):
            print(f"Chamber class set to: {arg}")
        else:
            print(f"Failed to set chamber class to: {arg}")

    def do_getChamber(self, arg):
        """Get the chamber class name for this station from the database"""
        chamber = self.chamberService.loadChamber()
        if chamber:
            print(f"Chamber class: {chamber}")
        else:
            print("No chamber class set for this station.")

    def do_savePlan(self, arg):
        """Save the current test plan for this station to the database."""
        self.planService.savePlan()
        print("Test plan saved successfully.")

    def do_setTestPlan(self, arg):
        """Sets the test plan for this station in the database. Usage: set_test_plan <PlanName>"""
        if not arg:
            print("Please provide a test plan ID.")
            return

        if self.planService.setTestPlan(arg):
            print(f"Test plan set to: {arg}")
        else:
            print(f"Failed to set test plan to: {arg}")

    def do_listPlans(self, arg):
        """List all available test plans."""
        plans = self.manager.db.listTestPlans()
        if not plans:
            print("No test plans available.")
            return
        
        print("Available test plans:")
        for plan in plans:
            print(f" - {plan.name}: {plan.user} on {plan.date}")