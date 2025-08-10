import logging
from typing import List, Tuple

from Cerberus.common import calcCRC
from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.plan import Plan
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.pluginService import PluginService


class PlanService:
    """
    Service to manage test plans.
    This service handles creating, saving, and loading test plans,
    as well as adding and removing tests from plans.
    """

    def __init__(self, pluginService: PluginService, db: StorageInterface):
        self._plan: Plan | None
        self._planCRC = -1
        self._planId = -1

        self._database = db
        self._pluginService = pluginService
        self.loadPlan()

    def newPlan(self, name: str) -> Plan | None:
        """Create a new test plan, save to the database and returns the ID."""
        if name is None or name == "":
            logging.error("Plan name cannot be empty or none.")
            return None

        self._plan = Plan(name)
        self._planCRC = -1
        self._planId = -1

        logging.debug(f"New plan created: {self._plan.name}")

        return self._plan

    def listTestPlans(self) -> List[Tuple[int, Plan]]:
        return self._database.listTestPlans()

    def loadPlan(self):
        """Load the current test plan for this station from the database."""
        self._plan = self._database.get_TestPlanForStation()
        self._planCRC = calcCRC(self._plan)

    def getPlan(self) -> Plan | None:
        """Returns the loaded test plan."""
        if self._plan is None:
            logging.error("No test plan loaded.")
            return None

        return self._plan

    def savePlan(self) -> int | None:
        """Save the current test plan for this station to the database."""
        if self._plan is None:
            logging.error("No test plan loaded.")
            return None

        newPlanCRC = calcCRC(self._plan)
        if self._planCRC == newPlanCRC:
            logging.debug("Plan CRC is the same, not saving")
            return self._planId

        id = self._database.saveTestPlan(self._plan)
        if id == -1:
            logging.error(f"Test plan '{self._plan.name}' was not saved.")
            return id

        self._planCRC = newPlanCRC
        self._planId = id

        logging.debug(f"Test plan '{id}:{self._plan.name}' saved successfully.")

        return id

    def setTestPlan(self, planId: int) -> bool:
        """Set the current test plan for this station.
        Returns True if set successfully, False otherwise.
        """
        # TODO: Check if the planId is a valid ID!

        if self._database.set_TestPlanForStation(planId):
            self.loadPlan()
            logging.debug(f"Test plan {planId} set and loaded successfully.")
            return True
        else:
            logging.error(f"Failed to set test plan to: {planId}")
            return False

    def addTestToPlan(self, testName: str) -> bool:
        """Add a test to the current plan."""
        if self._plan is None:
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
        if self._plan is None:
            logging.error("No test plan loaded.")
            return False

        if testName in self._plan:
            self._plan.remove(testName)
            logging.info(f"Test '{testName}' removed from the current plan.")
            return True
        else:
            logging.error(f"Test '{testName}' not found in the current plan.")
            return False
