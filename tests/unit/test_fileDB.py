import pytest

from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.plugins.equipment.signalGenerators.VSG60C.vsg60CEquipment import \
    VSG60C
from Cerberus.plugins.equipment.spectrumAnalysers.BB60C.bb60CEquipment import \
    BB60C

# Mirrors test_genericDB ordering & names to keep suites in sync.


@pytest.fixture
def file_db(tmp_path):
    db_path = tmp_path / "file_settings.json"
    fdb = FileDatabase(str(db_path), station_identity="TEST_STATION_FILE")
    yield fdb
    try:
        fdb.close()
    except Exception:
        pass


@pytest.fixture
def equipment_plugins():
    bb = BB60C()
    vsg = VSG60C()
    # Override some comms params so we can assert persistence changes
    bb.updateParameters('Communication', {'IP Address': '192.168.10.101', 'Port': 6101, 'Timeout': 1600})
    vsg.updateParameters('Communication', {'IP Address': '192.168.10.202', 'Port': 6102, 'Timeout': 2600})
    return [bb, vsg]


def test_save_and_load_equipment_comm_params_roundtrip(file_db, equipment_plugins):
    bb, vsg = equipment_plugins

    # Save initial state
    file_db.save_equipment(equipment_plugins)

    # Mutate in-memory to prove reload overwrites values
    bb.updateParameters('Communication', {'IP Address': '10.1.0.1', 'Port': 1, 'Timeout': 1})
    vsg.updateParameters('Communication', {'IP Address': '10.1.0.2', 'Port': 2, 'Timeout': 2})

    # Reload from file DB
    file_db.load_equipment_into(bb)
    file_db.load_equipment_into(vsg)

    bb_comm = {p.name: p.value for p in bb._groupParams['Communication'].values()}  # noqa: SLF001
    vsg_comm = {p.name: p.value for p in vsg._groupParams['Communication'].values()}  # noqa: SLF001

    assert bb_comm['IP Address'] == '192.168.10.101'
    assert bb_comm['Port'] == 6101
    assert bb_comm['Timeout'] == 1600

    assert vsg_comm['IP Address'] == '192.168.10.202'
    assert vsg_comm['Port'] == 6102
    assert vsg_comm['Timeout'] == 2600

    # Change again and save then verify persistence records exist
    bb.updateParameters('Communication', {'IP Address': '172.16.1.10'})
    file_db.save_equipment([bb])

    # Fetch raw rows for BB60C (optional sanity)
    rows = [r for r in file_db.load_all_for_type('equipment') if r.get('plugin_name') == bb.name and r.get('group_name') == 'Communication']
    names = {r.get('parameter_name') for r in rows}
    assert {'IP Address', 'Port', 'Timeout'} <= names
    names = {r.get('parameter_name') for r in rows}
    assert {'IP Address', 'Port', 'Timeout'} <= names
