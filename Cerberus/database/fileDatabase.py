
import json
import os
import threading
from typing import Any, Iterable, Optional

from Cerberus.database.baseDB import BaseDB
from Cerberus.plugins.baseParameters import BaseParameter
from Cerberus.plugins.basePlugin import BasePlugin


class FileDatabase(BaseDB):
    """Lightweight JSON-file implementation of BaseDB for tests / offline use.

    File format (single JSON object):
    {
       "station_id": {
           "<plugin_type>": {
               "<plugin_name>": {
                   "<group_name>": {
                       "<param_name>": { <parameter_json> }, ...
                   }, ...
               }, ...
           }, ...
       }
    }
    """

    def __init__(self, file_path: str, station_identity: str = "STATION-1"):
        super().__init__(station_identity)
        self._file_path = file_path
        self._lock = threading.RLock()
        # Create file if missing
        if not os.path.exists(self._file_path):
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    # ---------------------------- internal helpers -------------------------------------------------------------
    def _load_all(self) -> dict[str, Any]:
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_all(self, data: dict[str, Any]) -> None:
        tmp_path = self._file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp_path, self._file_path)

    def _station_root(self, data: dict[str, Any]) -> dict[str, Any]:
        return data.setdefault(self.station_id, {})

    # ---------------------------- BaseDB required methods ------------------------------------------------------
    def save_parameter(self, plugin_type: str, plugin_name: str, group_name: str, param: BaseParameter) -> None:
        with self._lock:
            data = self._load_all()
            station = self._station_root(data)
            ptree = station.setdefault(plugin_type, {})
            plug = ptree.setdefault(plugin_name, {})
            grp = plug.setdefault(group_name, {})
            grp[param.name] = param.to_dict()
            self._save_all(data)

    def save_plugin(self, plugin_type: str, plugin: BasePlugin) -> None:
        for group_name, group in plugin._groupParams.items():  # noqa: SLF001
            for param in group.values():
                self.save_parameter(plugin_type, plugin.name, group_name, param)

    def save_many(self, plugin_type: str, plugins: Iterable[BasePlugin]) -> None:
        for p in plugins:
            self.save_plugin(plugin_type, p)

    def load_parameter(self, plugin_type: str, plugin_name: str, group_name: str, parameter_name: str) -> Optional[BaseParameter]:
        from Cerberus.plugins.baseParameters import PARAMETER_TYPE_MAP
        with self._lock:
            data = self._load_all()
            try:
                pj = data[self.station_id][plugin_type][plugin_name][group_name][parameter_name]
            except KeyError:
                return None
        p_type = pj.get("type")
        cls = PARAMETER_TYPE_MAP.get(p_type)
        if not cls:
            return None
        return cls.from_dict(pj)

    def load_plugin_into(self, plugin_type: str, plugin: BasePlugin) -> None:
        for group_name, group in plugin._groupParams.items():  # noqa: SLF001
            for pname, param in group.items():
                restored = self.load_parameter(plugin_type, plugin.name, group_name, pname)
                if restored:
                    param.value = restored.value

    def load_all_for_type(self, plugin_type: str) -> list[Any]:
        with self._lock:
            data = self._load_all()
            station = data.get(self.station_id, {})
            subtree = station.get(plugin_type, {})
            records = []
            for pname, plugin_data in subtree.items():
                for gname, group in plugin_data.items():
                    for param_name, param_json in group.items():
                        records.append({
                            "station_id": self.station_id,
                            "plugin_type": plugin_type,
                            "plugin_name": pname,
                            "group_name": gname,
                            "parameter_name": param_name,
                            "parameter_json": json.dumps(param_json)
                        })
            return records

    def delete_plugin(self, plugin_type: str, plugin_name: str) -> None:
        with self._lock:
            data = self._load_all()
            try:
                del data[self.station_id][plugin_type][plugin_name]
            except KeyError:
                return
            self._save_all(data)

    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str) -> None:
        with self._lock:
            data = self._load_all()
            try:
                del data[self.station_id][plugin_type][plugin_name][group_name]
            except KeyError:
                return
            self._save_all(data)

    def delete_parameter(self, plugin_type: str, plugin_name: str, group_name: str, parameter_name: str) -> None:
        with self._lock:
            data = self._load_all()
            try:
                del data[self.station_id][plugin_type][plugin_name][group_name][parameter_name]
            except KeyError:
                return
            self._save_all(data)

    # Convenience wrappers --------------------------------------------------------------------------------------
    def save_equipment(self, equipment_plugins: Iterable[BasePlugin]) -> None:
        self.save_many('equipment', equipment_plugins)

    def save_tests(self, test_plugins: Iterable[BasePlugin]) -> None:
        self.save_many('test', test_plugins)

    def save_products(self, product_plugins: Iterable[BasePlugin]) -> None:
        self.save_many('product', product_plugins)

    def load_equipment_into(self, plugin: BasePlugin) -> None:
        self.load_plugin_into('equipment', plugin)

    def load_test_into(self, plugin: BasePlugin) -> None:
        self.load_plugin_into('test', plugin)

    def load_product_into(self, plugin: BasePlugin) -> None:
        self.load_plugin_into('product', plugin)

    # Lifecycle --------------------------------------------------------------------------------------------------
    def close(self) -> None:  # Nothing to do for file backend
        return

    def wipeDB(self) -> None:
        """Dangerous: remove all persisted parameter data for this station by clearing the file.

        Implementation choice: replace the file with an empty JSON object. This will remove
        data for all stations stored in the same file — callers must confirm intent.
        """
        with self._lock:
            # Ensure directory exists
            d = os.path.dirname(self._file_path)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            # Overwrite with empty object
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
