from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.plugins.equipment.cables.calibratedCableEquipment import \
    CalibratedCable
from Cerberus.pluginService import PluginService


class CalCableService(dict[str, CalibratedCable]):
    def __init__(self, pluginService: PluginService, db: StorageInterface):
        self.database = db
        self.pluginService = pluginService

        self.loadCalibratedCables()

    def loadCalibratedCables(self):
        rows = self.database.listCalCables()
        for row in rows:
            role = row['role'].upper()          # 'TX' / 'RX' / future

            cable = CalibratedCable()
            cable.loadCalibrationFromJSON(row.get('coeffs_json'))
            self[role] = cable

    def saveCalibratedCables(self) -> int:
        """Persist all calibrated cable objects via database.upsertCalCable.

        Returns number of successfully saved cables.
        """
        import logging
        saved = 0
        for role, cable in self.items():
            try:
                ch = getattr(cable, '_cheb', None)
                if ch is None:
                    continue  # nothing to save
                meta = getattr(cable, '_cal_meta', {}) or {}
                method = meta.get('method', 'chebyshev')
                coeffs = list(getattr(ch, 'coef'))
                domain = tuple(getattr(ch, 'domain'))
                degree = meta.get('degree', len(coeffs) - 1)

                # Serial stored in parameters if present
                serial = ''
                try:
                    serial = cable.getParameterValue('Cable', 'Serial', '')  # type: ignore[attr-defined]

                except Exception:
                    serial = meta.get('serial', '')

                if not serial:
                    serial = f"{role}_AUTO"

                rc = self.database.upsertCalCable(role, serial, method=method, degree=degree,
                                                  domain=domain, coeffs=coeffs)
                if rc is not None:
                    saved += 1

            except Exception as ex:
                logging.error(f"Failed to save calibrated cable {role}: {ex}")

        return saved
