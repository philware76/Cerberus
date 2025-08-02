from multiprocessing import Manager

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.plan import Plan


class PlanShell(BaseShell):
    intro = "Cerberus Plan Shell. Type help or ? to list commands."
    prompt = "Plan> "

    def __init__(self, manager: Manager):
        super().__init__(manager)
        self.plan = None

    def do_new(self, arg):
        "Create a new plan. Usage: new <plan_name>"
        plan_name = arg.strip()
        if not plan_name:
            print("Please provide a plan name.")
            return
        
        self.plan = Plan(plan_name)
        print(f"New plan '{plan_name}' created.")

    def do_add(self, arg):
        "Add a test name to the current plan. Usage: add <test_name>"
        if self.plan is None:
            print("No plan created. Use 'new' first.")
            return
        
        if not arg:
            print("Please provide a test name.")
            return
        
        self.plan.append(arg)
        print(f"Test '{arg}' added to plan.")

    def do_show(self, arg):
        "Show the current plan details."
        if self.plan is None:
            print("No plan created.")
            return
        
        print(f"Plan name: {self.plan.name}")
        print(f"User: {self.plan.user}")
        print(f"Date: {self.plan.date}")
        print("Tests:")
        for test in self.plan:
            print(f"  - {test}")

