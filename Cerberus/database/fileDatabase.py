import json
import logging
import os
import sys
from sys import path
from typing import Any, Dict, List, Tuple

from Cerberus.database.database import StorageInterface
from Cerberus.plan import Plan

# NOT SURE IF THIS WORKS YET - UNTESTED!


class FileDatabase(StorageInterface):
    """File-based implementation of the StorageInterface (single-station)."""

    def __init__(self, file_path: str, station_identity: str = "STATION-1"):
        self._file_path = file_path
        self.station_identity = station_identity
        self._data: Dict[str, Any] = {}
        self._load_data()
        # Ensure mandatory containers (role-less)
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

    def wipeDB(self) -> bool:
        try:
            os.remove(self._file_path)
            self._data = {}
        except Exception as e:
            logging.error("Failed to delete file database. {e}")
            return False

        return True

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

    # --- Equipment Management (role-less) ------------------------------------------------------------------------
    def _next_equipment_id(self) -> int:
        equipment: List[Dict[str, Any]] = self._data.get('equipment', [])
        if not equipment:
            return 1
        return max(e.get('id', 0) for e in equipment) + 1

    def upsertEquipment(self, manufacturer: str, model: str, serial: str, version: str,
                        ip: str, port: int, timeout: int, calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:  # type: ignore[override]
        equipment: List[Dict[str, Any]] = self._data.get('equipment', [])
        for eq in equipment:
            if eq.get('serial') == serial:
                eq.update({
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
            'station_identity': None,
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

    def attachEquipmentToStation(self, equipmentId: int) -> bool:
        equipment: List[Dict[str, Any]] = self._data.get('equipment', [])
        for eq in equipment:
            if eq.get('id') == equipmentId:
                if eq.get('station_identity') == self.station_identity:
                    return True
                eq['station_identity'] = self.station_identity
                self._save_data()
                return True
        logging.error(f"Equipment id {equipmentId} not found for attachment")
        return False

    def listStationEquipment(self) -> List[Dict[str, Any]]:
        equipment: List[Dict[str, Any]] = self._data.get('equipment', [])
        return [e.copy() for e in equipment if e.get('station_identity') == self.station_identity]
