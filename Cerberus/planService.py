import logging

from Cerberus.database.database import Database
from Cerberus.plan import Plan
from Cerberus.plugins.tests.baseTest import BaseTest


class PlanService:
    def __init__(self, db: Database):
        self.plan: Plan
        self.database = db
        self.loadPlan()

    def loadPlan(self):
        """Load the current test plan for this station from the database."""
        self.plan = self.database.get_TestPlanForStation()

    def savePlan(self):
        """Save the current test plan for this station to the database."""
        if self.plan:
            id = self.database.saveTestPlan(self.plan)
            logging.debug(f"Test plan '{id}' saved successfully.")
        else:
            logging.warning("No test plan to save.")

    def setTestPlan(self, planId: int) -> bool:
        """Set the test plan for this station in the database.
        Returns True if set successfully, False otherwise.
        """
        if not planId:
            logging.error("Test plan ID cannot be empty.")
            return False

        if self.database.set_TestPlanForStation(planId):
            self.loadPlan()
            logging.debug(f"Test plan {planId} set and loaded successfully.")
            return True
        else:
            logging.error(f"Failed to set test plan to: {planId}")
            return False
                
    def addTestToPlan(self, testName: str) -> bool:
        """Add a test to the current plan."""
        if not self.plan:
            logging.error("No test plan loaded.")
            return False

        # Check if testPlugin is a valid BaseTest subclass
        testPlugin = self.findTest(testName)
        if not testPlugin or not isinstance(testPlugin, BaseTest):
            logging.error(f"Test '{testName}' is not a valid BaseTest subclass.")
            return False
        
        self.plan.append(testName)
        logging.info(f"Test '{testName}' added to the current plan.")
        return True
    
    def removeTestFromPlan(self, testName: str) -> bool:
        """Remove a test from the current plan."""
        if not self.plan:
            logging.error("No test plan loaded.")
            return False

        if testName in self.plan:
            self.plan.remove(testName)
            logging.info(f"Test '{testName}' removed from the current plan.")
            return True
        else:
            logging.error(f"Test '{testName}' not found in the current plan.")
            return False
