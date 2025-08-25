
import json
import logging
import os
import threading
from typing import Any, Iterable, Optional, cast

from Cerberus.common import DBInfo
from Cerberus.database.cerberusDB import CerberusDB
from Cerberus.logConfig import getLogger
from Cerberus.plugins.baseParameters import BaseParameter
from Cerberus.plugins.basePlugin import BasePlugin

logger = getLogger("FileDB")
logger.setLevel(logging.INFO)


class FileDB(CerberusDB):
    '''File JSON based 'database' which conforms to the CerberusDB API'''

    def __init__(self, station_id: str, filename: str):
        super().__init__(station_id)
        self.filename = filename

        self._lock = threading.RLock()

        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self._get_empty_db_structure(), f)

    def _get_empty_db_structure(self) -> dict:
        """Return the empty database structure."""
        return {
            "group_identities": {},  # key: (station_id, plugin_type, plugin_name, group_name) -> id
            "group_content": {},     # key: id -> {"group_hash": str, "group_json": str}
            "group_settings": {},    # key: id -> {"group_identity_id": int, "content_id": int}
            "next_id": 1
        }

    def _load_data(self) -> dict:
        """Load data from the JSON file."""
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure the structure is complete
                empty_structure = self._get_empty_db_structure()
                for key in empty_structure:
                    if key not in data:
                        data[key] = empty_structure[key]
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_empty_db_structure()

    def _save_data(self, data: dict) -> None:
        """Save data to the JSON file."""
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _get_next_id(self, data: dict) -> int:
        """Get the next available ID and increment the counter."""
        next_id = data["next_id"]
        data["next_id"] = next_id + 1
        return next_id

    def _get_group_identity_key(self, plugin_type: str, plugin_name: str, group_name: str) -> str:
        """Generate a key for group identity lookup."""
        return f"{self.station_id}:{plugin_type}:{plugin_name}:{group_name}"

    def _save_group_imp(self, plugin_type: str, plugin_name: str, group_name: str, values_map: dict) -> None:
        """Save a group's parameter values."""
        with self._lock:
            data = self._load_data()
            
            # Compute hash and canonical JSON
            hash_hex, canonical_json = self.compute_group_hash(values_map)
            
            # Get or create group identity
            identity_key = self._get_group_identity_key(plugin_type, plugin_name, group_name)
            
            # Check if content with this hash already exists
            content_id = None
            for cid, content in data["group_content"].items():
                if content["group_hash"] == hash_hex:
                    content_id = int(cid)
                    break
            
            # Create new content if not found
            if content_id is None:
                content_id = self._get_next_id(data)
                data["group_content"][str(content_id)] = {
                    "group_hash": hash_hex,
                    "group_json": canonical_json
                }
            
            # Get or create group identity ID
            if identity_key in data["group_identities"]:
                identity_id = data["group_identities"][identity_key]
            else:
                identity_id = self._get_next_id(data)
                data["group_identities"][identity_key] = identity_id
            
            # Update or create group settings
            settings_id = self._get_next_id(data)
            data["group_settings"][str(settings_id)] = {
                "group_identity_id": identity_id,
                "content_id": content_id
            }
            
            # Clean up old settings for this identity
            to_remove = []
            for sid, settings in data["group_settings"].items():
                if settings["group_identity_id"] == identity_id and int(sid) != settings_id:
                    to_remove.append(sid)
            
            for sid in to_remove:
                del data["group_settings"][sid]
            
            self._save_data(data)

    def _load_group_json(self, plugin_type: str, plugin_name: str, group_name: str) -> dict:
        """Load a group's parameter values."""
        with self._lock:
            data = self._load_data()
            
            identity_key = self._get_group_identity_key(plugin_type, plugin_name, group_name)
            
            # Find the group identity
            if identity_key not in data["group_identities"]:
                return {}
            
            identity_id = data["group_identities"][identity_key]
            
            # Find the current settings for this identity
            content_id = None
            for settings in data["group_settings"].values():
                if settings["group_identity_id"] == identity_id:
                    content_id = settings["content_id"]
                    break
            
            if content_id is None:
                return {}
            
            # Get the content
            content = data["group_content"].get(str(content_id))
            if not content:
                return {}
            
            try:
                return json.loads(content["group_json"])
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode JSON for group {identity_key}")
                return {}

    def _close_impl(self):
        """Close the database (no-op for file-based implementation)."""
        pass

    def _get_cerberus_tables(self) -> list[str]:
        """Return list of 'tables' (sections) in the file database."""
        return ["group_identities", "group_content", "group_settings"]

    def _delete_plugin_impl(self, plugin_type: str, plugin_name: str):
        """Delete all data for a specific plugin."""
        with self._lock:
            data = self._load_data()
            
            # Find all identity keys for this plugin
            prefix = f"{self.station_id}:{plugin_type}:{plugin_name}:"
            identity_keys_to_remove = [key for key in data["group_identities"].keys() 
                                     if key.startswith(prefix)]
            
            # Get identity IDs to remove
            identity_ids_to_remove = [data["group_identities"][key] for key in identity_keys_to_remove]
            
            # Remove group identities
            for key in identity_keys_to_remove:
                del data["group_identities"][key]
            
            # Remove group settings for these identities
            settings_to_remove = []
            for sid, settings in data["group_settings"].items():
                if settings["group_identity_id"] in identity_ids_to_remove:
                    settings_to_remove.append(sid)
            
            for sid in settings_to_remove:
                del data["group_settings"][sid]
            
            # Note: We don't remove group_content as it might be referenced by other identities
            
            self._save_data(data)

    def _delete_group_impl(self, plugin_type: str, plugin_name: str, group_name: str):
        """Delete data for a specific plugin group."""
        with self._lock:
            data = self._load_data()
            
            identity_key = self._get_group_identity_key(plugin_type, plugin_name, group_name)
            
            if identity_key not in data["group_identities"]:
                return
            
            identity_id = data["group_identities"][identity_key]
            
            # Remove group identity
            del data["group_identities"][identity_key]
            
            # Remove group settings for this identity
            settings_to_remove = []
            for sid, settings in data["group_settings"].items():
                if settings["group_identity_id"] == identity_id:
                    settings_to_remove.append(sid)
            
            for sid in settings_to_remove:
                del data["group_settings"][sid]
            
            self._save_data(data)

    def _drop_tables_safely(self, tables: list[str]) -> None:
        """Drop 'tables' (clear sections) in the file database."""
        with self._lock:
            data = self._load_data()
            
            for table in tables:
                if table in data:
                    if table == "next_id":
                        data[table] = 1
                    else:
                        data[table] = {}
            
            self._save_data(data)

    def _find_duplicate_group_settings_impl(self) -> list[Any]:
        """Find duplicate group settings (file-based implementation)."""
        with self._lock:
            data = self._load_data()
            
            # Group settings by identity_id
            identity_groups = {}
            for sid, settings in data["group_settings"].items():
                identity_id = settings["group_identity_id"]
                if identity_id not in identity_groups:
                    identity_groups[identity_id] = []
                identity_groups[identity_id].append((int(sid), settings))
            
            # Find duplicates (more than one setting per identity)
            duplicates = []
            for identity_id, settings_list in identity_groups.items():
                if len(settings_list) > 1:
                    # Sort by ID and keep the first one
                    settings_list.sort(key=lambda x: x[0])
                    keep_id = settings_list[0][0]
                    content_id = settings_list[0][1]["content_id"]
                    all_ids = [str(sid) for sid, _ in settings_list]
                    
                    # Format: (group_identity_id, content_id, count, keep_id, all_ids_csv)
                    duplicates.append((identity_id, content_id, len(settings_list), keep_id, ",".join(all_ids)))
            
            return duplicates

    def _cleanup_single_duplicate_set_impl(self, group_identity_id: int, keep_id_int: int,
                                         dup_ids: list[int], dry_run: bool) -> int:
        """Clean up a single duplicate set."""
        if dry_run:
            return len(dup_ids)
        
        with self._lock:
            data = self._load_data()
            
            deleted_count = 0
            for dup_id in dup_ids:
                if str(dup_id) in data["group_settings"]:
                    del data["group_settings"][str(dup_id)]
                    deleted_count += 1
            
            if deleted_count > 0:
                self._save_data(data)
            
            return deleted_count

    def _get_group_content_rows(self) -> list[tuple[Any, Any, Any]]:
        """Get all rows from group_content 'table'."""
        with self._lock:
            data = self._load_data()
            
            rows = []
            for cid, content in data["group_content"].items():
                rows.append((int(cid), content["group_hash"], content["group_json"]))
            
            return rows
