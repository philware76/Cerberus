from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.gui.helpers import displayWidget
from Cerberus.gui.PlanUI import PlanListWidget
from Cerberus.manager import Manager
from Cerberus.plan import Plan


class PlanShell(BaseShell):
    intro = "Cerberus Plan Shell. Type help or ? to list commands."
    prompt = "Plan> "

    def __init__(self, manager: Manager):
        super().__init__(manager)
        self.planService = manager.planService

    def do_new(self, arg):
        "Create a new plan. Usage: new <plan_name>"
        plan_name = arg.strip()
        if not plan_name:
            print("Please provide a plan name.")
            return
        from Cerberus.plan import Plan
        self.planService.newPlan(plan_name)
        print(f"New plan '{plan_name}' created.")

    def do_save(self, arg):
        """Saves the current test plan to the database"""
        id = self.planService.savePlan()
        if id is not None:
            print(f"Test Plan saved as id #{id}")
        else:
            print("Failed to save test plan")

    def do_add(self, testName):
        "Add a test name to the current plan. Usage: add <test_name>"
        if self.planService.addTestToPlan(testName):
            print(f"Test '{testName}' added to the current plan.")
        else:
            print(f"Failed to add test '{testName}' to the current plan. Ensure a plan is created first.")

    def do_remove(self, testName):
        "Remove a test name from the current plan. Usage: remove <test_name>"
        if self.planService.removeTestFromPlan(testName):
            print(f"Test '{testName}' removed from the current plan.")
        else:
            print(f"Failed to remove test '{testName}' from the current plan. Ensure the test exists in the plan.")

    def do_show(self, arg):
        "Show the current plan details."
        plan = self.planService.getPlan()
        if plan is None:
            print("No plan created.")
            return

        print(f"Plan name: {plan.name}")
        print(f"User: {plan.user}")
        print(f"Date: {plan.date}")
        print("Tests:")
        for test in plan:
            print(f"  - {test}")

    def do_listPlans(self, arg):
        plans = self.planService.listTestPlans()
        widget = PlanListWidget(plans)
        displayWidget(widget)
