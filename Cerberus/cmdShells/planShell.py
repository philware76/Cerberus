from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.manager import Manager
from Cerberus.plan import Plan


class PlanShell(BaseShell):
    intro = "Cerberus Plan Shell. Type help or ? to list commands."
    prompt = "Plan> "

    def __init__(self, manager: Manager):
        super().__init__(manager)

    def do_new(self, arg):
        "Create a new plan. Usage: new <plan_name>"
        plan_name = arg.strip()
        if not plan_name:
            print("Please provide a plan name.")
            return
        from Cerberus.plan import Plan
        self.manager.plan = Plan(plan_name)
        print(f"New plan '{plan_name}' created.")

    def do_add(self, testName):
        "Add a test name to the current plan. Usage: add <test_name>"
        if self.manager.addTestToPlan(testName):
            print(f"Test '{testName}' added to the current plan.")
        else:
            print(f"Failed to add test '{testName}' to the current plan. Ensure a plan is created first.")
    
    def do_remove(self, testName):
        "Remove a test name from the current plan. Usage: remove <test_name>"
        if self.manager.removeTestFromPlan(testName):
            print(f"Test '{testName}' removed from the current plan.")
        else:
            print(f"Failed to remove test '{testName}' from the current plan. Ensure the test exists in the plan.")

    def do_show(self, arg):
        "Show the current plan details."
        if self.manager.plan is None:
            print("No plan created.")
            return
        plan = self.manager.plan
        print(f"Plan name: {plan.name}")
        print(f"User: {plan.user}")
        print(f"Date: {plan.date}")
        print("Tests:")
        for test in plan:
            print(f"  - {test}")

