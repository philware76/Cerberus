import json
import logging

from Cerberus.database.database import StorageInterface
from Cerberus.plan import Plan

# NOT SURE IF THIS WORKS YET - UNTESTED!

class FileDatabase(StorageInterface):
    """File-based implementation of the StorageInterface."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = {}
        self.load_data()
    
    def load_data(self):
        """Load data from the file."""
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            self.data = {}
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {self.file_path}: {e}")
            self.data = {}
    
    def save_data(self):
        """Save data to the file."""
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file, indent=4)
    
    # Implement other abstract methods here...
    def get_ChamberForStation(self) -> str:
        """Get the chamber class name for this station."""
        return self.data.get('chamber_type', '')

    def set_ChamberForStation(self, chamberType: str) -> bool:
        """Set the chamber class name for this station."""
        self.data['chamber_type'] = chamberType
        self.save_data()
        return True
    
    def listTestPlans(self) -> list[Plan]:
        """List all test plans in the database."""
        return [Plan.from_dict(plan) for plan in self.data.get('test_plans', [])]
    
    def get_TestPlanForStation(self) -> Plan:
        """Get the test plan for this station."""
        plan_data = self.data.get('test_plan', {})
        return Plan.from_dict(plan_data) if plan_data else Plan.EmptyPlan() 
    
    def set_TestPlanForStation(self, plan: Plan) -> bool:
        """Set the test plan for this station."""
        self.data['test_plan'] = plan.to_dict()
        self.save_data()
        return True
    
    def saveTestPlan(self):
        """Save the current test plan for this station."""
        self.save_data()