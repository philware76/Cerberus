import json
import logging
from typing import Dict, List, Tuple

from Cerberus.database.database import StorageInterface
from Cerberus.plan import Plan

# NOT SURE IF THIS WORKS YET - UNTESTED!

class FileDatabase(StorageInterface):
    """File-based implementation of the StorageInterface."""
    
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._data = {}
        self._load_data()
    
    def _load_data(self):
        """Load data from the file."""
        try:
            with open(self._file_path, 'r') as file:
                self._data = json.load(file)
        except FileNotFoundError:
            self._data = {}
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {self._file_path}: {e}")
            self._data = {}
    
    def _save_data(self):
        """Save data to the file."""
        with open(self._file_path, 'w') as file:
            json.dump(self._data, file, indent=4)
    
    # Implement other abstract methods here...
    def get_ChamberForStation(self) -> str:
        """Get the chamber class name for this station."""
        return self._data.get('chamber_type', '')

    def set_ChamberForStation(self, chamberType: str) -> bool:
        """Set the chamber class name for this station."""
        self._data['chamber_type'] = chamberType
        self._save_data()
        return True
    
    def listTestPlans(self) -> list[Tuple[int, str]]:
        """List all test plans in the database."""
        return [(planEntry["id"], Plan.from_dict(planEntry["plan"]).name) for planEntry in self._data.get('test_plans', [])]
    
    def get_TestPlanForStation(self) -> Plan:
        """Get the test plan for this station."""
        plan_id = self._data.get('testPlanId', None)
        if plan_id is None:
            return None
        
        test_plans = self._data.get('test_plans', [])
        for planEntry in test_plans:
            if planEntry.get('id') == plan_id:
                return Plan.from_dict(planEntry['plan'])
            
        return None
        
    def set_TestPlanForStation(self, id: int) -> bool:
        self._data['testPlanId'] = id
        self._save_data()
        return True


    def saveTestPlan(self, plan: Plan) -> int | None:
        """Save a new test plan for this station, assigning a new ID."""
        test_plans: List[Dict[str, str]] = self._data.get('test_plans', [])
        new_id = len(test_plans) + 1

        plan_dict = {
            "id": new_id,
            "plan": plan.to_dict()
        }
        
        test_plans.append(plan_dict)
        self._data['test_plans'] = test_plans
        self._save_data()
        
        return new_id
