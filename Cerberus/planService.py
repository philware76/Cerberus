import logging
from typing import List

from Cerberus.database.database import Database
from Cerberus.plan import Plan
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.pluginService import PluginService


class PlanService:
    """
    Service to manage test plans.
    This service handles creating, saving, and loading test plans,
    as well as adding and removing tests from plans.
    """
    def __init__(self, pluginService: PluginService, db: Database):
        self._plan: Plan
        self._database = db
        self._pluginService = pluginService
        self.loadPlan()

    def newPlan(self, name:str) -> int | None:
        """Create a new test plan, save to the database and returns the ID."""
        if name is None or name == "":
            logging.error("Plan name cannot be empty or none.")
            return

        self._plan = Plan(name)
        logging.debug(f"New plan created: {self._plan.name}")
        return self.savePlan()
        
    def listTestPlans(self) -> List[Plan]:
        return self._database.listTestPlans()
 
    def loadPlan(self):
        """Load the current test plan for this station from the database."""
        self._plan = self._database.get_TestPlanForStation()

    def getPlan(self) -> Plan:
        """Get the current test plan."""
        if self._plan is None:
            logging.error("No test plan loaded.")
            return None
        
        return self._plan

    def savePlan(self) -> int | None:
        """Save the current test plan for this station to the database."""
        if self._plan is not None:
            id = self._database.saveTestPlan(self._plan)
            logging.debug(f"Test plan '{id}' saved successfully.")
        else:
            logging.warning("No test plan to save.")
            id = None

        return id

    def setTestPlan(self, planId: int) -> bool:
        """Set the current test plan for this station.
        Returns True if set successfully, False otherwise.
        """
        if not planId:
            logging.error("Test plan ID cannot be empty.")
            return False

        if self._database.set_TestPlanForStation(planId):
            self.loadPlan()
            logging.debug(f"Test plan {planId} set and loaded successfully.")
            return True
        else:
            logging.error(f"Failed to set test plan to: {planId}")
            return False
                
    def addTestToPlan(self, testName: str) -> bool:
        """Add a test to the current plan."""
        if not self._plan:
            logging.error("No test plan loaded.")
            return False

        # Check if testPlugin is a valid BaseTest subclass
        testPlugin = self._pluginService.findTest(testName)
        if not testPlugin or not isinstance(testPlugin, BaseTest):
            logging.error(f"Test '{testName}' is not a valid BaseTest subclass.")
            return False
        
        self._plan.append(testName)
        logging.info(f"Test '{testName}' added to the current plan.")
        return True
    
    def removeTestFromPlan(self, testName: str) -> bool:
        """Remove a test from the current plan."""
        if not self._plan:
            logging.error("No test plan loaded.")
            return False

        if testName in self._plan:
            self._plan.remove(testName)
            logging.info(f"Test '{testName}' removed from the current plan.")
            return True
        else:
            logging.error(f"Test '{testName}' not found in the current plan.")
            return False
