import os

import pytest

from Cerberus.common import DBInfo
from Cerberus.database.mySqlDB import MySqlDB
from Cerberus.plugins.equipment.signalGenerators.VSG60C.vsg60CEquipment import \
    VSG60C
from Cerberus.plugins.equipment.spectrumAnalysers.BB60C.bb60CEquipment import \
    BB60C

# NOTE: This test expects a reachable MySQL instance matching cerberus.ini (or override via env vars)
# If unavailable, mark test xfail.


def _dbinfo_from_env():
    host = os.getenv('CERB_DB_HOST', '127.0.0.1')
    port = int(os.getenv('CERB_DB_PORT', '3305'))
    user = os.getenv('CERB_DB_USER', 'root')
    password = os.getenv('CERB_DB_PASS', '5m1thMy3r5')
    database = os.getenv('CERB_DB_NAME', 'cerberus')
    return DBInfo(host, port, user, password, database)


@pytest.fixture
def generic_db():
    dbi = _dbinfo_from_env()
    try:
        gdb = MySqlDB('TEST_STATION_GENERIC', dbi)
    except Exception as exc:  # e.g. connection error
        pytest.skip(f"MySQL not available for GenericDB tests: {exc}")
    yield gdb
    try:
        gdb.close()
    except Exception:
        pass


@pytest.fixture
def equipment_plugins():
    bb = BB60C()
    vsg = VSG60C()
    # Override some comms params so we can assert persistence changes
    bb.updateParameters('Communication', {'IP Address': '192.168.0.101', 'Port': 6001, 'Timeout': 1500})
    vsg.updateParameters('Communication', {'IP Address': '192.168.0.202', 'Port': 6002, 'Timeout': 2500})
    return [bb, vsg]


def test_save_and_load_equipment_comm_params_roundtrip(generic_db, equipment_plugins):
    bb, vsg = equipment_plugins

    # Save initial state
    generic_db.save_equipment(equipment_plugins)

    # Mutate in-memory to prove reload overwrites values
    bb.updateParameters('Communication', {'IP Address': '10.0.0.1', 'Port': 1, 'Timeout': 1})
    vsg.updateParameters('Communication', {'IP Address': '10.0.0.2', 'Port': 2, 'Timeout': 2})

    # Reload from DB
    generic_db.load_equipment_into(bb)
    generic_db.load_equipment_into(vsg)

    bb_comm = {p.name: p.value for p in bb._groupParams['Communication'].values()}  # noqa: SLF001
    vsg_comm = {p.name: p.value for p in vsg._groupParams['Communication'].values()}  # noqa: SLF001

    assert bb_comm['IP Address'] == '192.168.0.101'
    assert bb_comm['Port'] == 6001
    assert bb_comm['Timeout'] == 1500

    assert vsg_comm['IP Address'] == '192.168.0.202'
    assert vsg_comm['Port'] == 6002
    assert vsg_comm['Timeout'] == 2500

    # Change again and save then verify persistence records exist
    bb.updateParameters('Communication', {'IP Address': '172.16.0.10'})
    generic_db.save_equipment([bb])

    # Fetch raw rows for BB60C (optional sanity)
    rows = [r for r in generic_db.load_all_for_type('equipment') if r.plugin_name == bb.name and r.group_name == 'Communication']
    names = {r.parameter_name for r in rows}
    assert {'IP Address', 'Port', 'Timeout'} <= names
    rows = [r for r in generic_db.load_all_for_type('equipment') if r.plugin_name == bb.name and r.group_name == 'Communication']
    names = {r.parameter_name for r in rows}
    assert {'IP Address', 'Port', 'Timeout'} <= names
