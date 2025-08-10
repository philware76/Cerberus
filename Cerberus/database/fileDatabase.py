import json
import logging
from typing import Any, Dict, List, Tuple

from Cerberus.database.database import StorageInterface
from Cerberus.plan import Plan

# NOT SURE IF THIS WORKS YET - UNTESTED!


class FileDatabase(StorageInterface):
    """File-based implementation of the StorageInterface (single-station)."""

    def __init__(self, file_path: str):
        self._file_path = file_path
        self._data: Dict[str, Any] = {}
        self._load_data()
        # Ensure mandatory containers
        self._data.setdefault('test_plans', [])
        self._data.setdefault('equipment', [])
        self._data.setdefault('testPlanId', None)
        self._save_data()

    # --- Internal persistence helpers -----------------------------------------------------------------------------
    def _load_data(self):
        try:
            with open(self._file_path, 'r') as file:
                self._data = json.load(file)
        except FileNotFoundError:
            self._data = {}
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {self._file_path}: {e}")
            self._data = {}

    def _save_data(self):
        with open(self._file_path, 'w') as file:
            json.dump(self._data, file, indent=4)

    # --- Core API --------------------------------------------------------------------------------------------------
    def close(self):
        logging.debug("Closed file database.")

    def deleteTestPlan(self, plan_id: int) -> bool:
        test_plans = self._data.get('test_plans', [])
        for i, plan in enumerate(test_plans):
            if plan.get('id') == plan_id:
                del test_plans[i]
                self._data['test_plans'] = test_plans
                if self._data.get('testPlanId') == plan_id:
                    self._data['testPlanId'] = None
                self._save_data()
                logging.info(f"Test plan with ID {plan_id} deleted.")
                return True
        logging.error(f"Test plan with ID {plan_id} not found.")
        return False

    def get_ChamberForStation(self) -> str | None:
        return self._data.get('chamber_type')

    def set_ChamberForStation(self, chamberType: str) -> bool:
        self._data['chamber_type'] = chamberType
        self._save_data()
        return True

    def listTestPlans(self) -> list[Tuple[int, Plan]]:
        return [(int(planEntry['id']), Plan.from_dict(planEntry['plan'])) for planEntry in self._data.get('test_plans', [])]

    def get_TestPlanForStation(self) -> Plan | None:
        plan_id = self._data.get('testPlanId')
        if plan_id is None:
            return None
        for planEntry in self._data.get('test_plans', []):
            if planEntry.get('id') == plan_id:
                return Plan.from_dict(planEntry['plan'])
        return None

    def set_TestPlanForStation(self, plan_id: int) -> bool:
        self._data['testPlanId'] = plan_id
        self._save_data()
        return True

    def saveTestPlan(self, plan: Plan) -> int | None:
        test_plans: List[Dict[str, Any]] = self._data.get('test_plans', [])
        # Generate incremental ID (avoid re-use if deletions occurred)
        if test_plans:
            new_id = max(p['id'] for p in test_plans if 'id' in p) + 1
        else:
            new_id = 1
        plan_dict = {"id": new_id, "plan": plan.to_dict()}
        test_plans.append(plan_dict)
        self._data['test_plans'] = test_plans
        self._save_data()
        return new_id

    # --- Equipment Management -------------------------------------------------------------------------------------
    def _next_equipment_id(self) -> int:
        equipment: List[Dict[str, Any]] = self._data.get('equipment', [])
        if not equipment:
            return 1
        return max(e.get('id', 0) for e in equipment) + 1

    def upsertEquipment(self, equipRole: str, manufacturer: str, model: str, serial: str, version: str,
                        ip: str, port: int, timeout: int, calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        role = equipRole.upper()
        if role not in ("SIGGEN", "SPECAN"):
            logging.error(f"Invalid equipment role '{equipRole}'")
            return None
        equipment: List[Dict[str, Any]] = self._data.get('equipment', [])
        for eq in equipment:
            if eq.get('serial') == serial:
                eq.update({
                    'role': role,
                    'manufacturer': manufacturer,
                    'model': model,
                    'version': version,
                    'ip': ip,
                    'port': port,
                    'timeout': timeout,
                    'calibration_date': calibration_date,
                    'calibration_due': calibration_due
                })
                self._save_data()
                return int(eq['id'])
        new_id = self._next_equipment_id()
        equipment.append({
            'id': new_id,
            'role': role,
            'manufacturer': manufacturer,
            'model': model,
            'serial': serial,
            'version': version,
            'ip': ip,
            'port': port,
            'timeout': timeout,
            'calibration_date': calibration_date,
            'calibration_due': calibration_due
        })
        self._data['equipment'] = equipment
        self._save_data()
        return new_id

    def assignEquipmentToStation(self, equipRole: str, equipmentId: int) -> bool:
        role = equipRole.upper()
        if role == 'SIGGEN':
            key = 'siggen_id'
        elif role == 'SPECAN':
            key = 'specan_id'
        else:
            logging.error(f"Unknown equipment role {equipRole} for assignment")
            return False
        self._data[key] = equipmentId
        self._save_data()
        return True

    def getStationEquipment(self) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        equipment: List[Dict[str, Any]] = self._data.get('equipment', [])
        id_map = {e['id']: e for e in equipment}
        sg_id = self._data.get('siggen_id')
        sa_id = self._data.get('specan_id')
        if sg_id and sg_id in id_map:
            result['SIGGEN'] = id_map[sg_id].copy()
        if sa_id and sa_id in id_map:
            result['SPECAN'] = id_map[sa_id].copy()
        return result
