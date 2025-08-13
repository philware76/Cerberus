import importlib.util
import random
import re
import sys
from pathlib import Path

# Ensure module import (package path relative to tests root)
MODULE_PATH = Path(__file__).parents[2] / 'Cerberus' / 'plugins' / 'products' / 'nesieFirmware'

spec = importlib.util.spec_from_file_location('nesie_rx_filter_bands', MODULE_PATH / 'nesie_rx_filter_bands.py')
assert spec is not None
nesie = importlib.util.module_from_spec(spec)  # type: ignore
# Register in sys.modules so dataclasses decorator can resolve module
sys.modules[spec.name] = nesie  # type: ignore
spec.loader.exec_module(nesie)  # type: ignore

# Regex now captures trailing hardware id hex after //  0x.. comment pattern.
# Assumes each entry formatted on a single logical line ending with },  //  0xHH
ENTRY_PATTERN = re.compile(
    r"\{\s*\{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*"  # uplink
    r"\{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*"        # downlink
    r"([A-Z_]+)\s*,\s*(\d+)\s*,\s*"                 # direction mask token, ladon id
    r"(BAND_FILTER_[A-Z0-9_]+)\s*,\s*(-?\d+)\s*,\s*"  # band token, lte band
    r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*"     # filter_no, filters_per_band, extra_data
    r"(COVERT872CALDATALOOKUP_[A-Z0-9_]+)\s*}\s*,\s*//\s*(0x[0-9A-Fa-f]+)"  # cal lookup + hardware id
)


def parse_c_entries(c_text: str):
    entries = []
    for m in ENTRY_PATTERN.finditer(c_text):
        (ul_from, ul_to, dl_from, dl_to, direction_token, ladon_id, band_token, lte_band,
         filter_no, filters_per_band, extra_data, cal_lookup_token, hw_hex) = m.groups()
        entries.append({
            'ul_from': int(ul_from),
            'ul_to': int(ul_to),
            'dl_from': int(dl_from),
            'dl_to': int(dl_to),
            'direction': direction_token,
            'ladon_id': int(ladon_id),
            'band': band_token,
            'lte_band': int(lte_band),
            'filter_no': int(filter_no),
            'filters_per_band': int(filters_per_band),
            'extra_data': int(extra_data),
            'cal_lookup': cal_lookup_token,
            'hardware_id': int(hw_hex, 16),
        })
    return entries


def test_all_hardware_ids_and_structure():
    c_file = MODULE_PATH / 'rxFilterBands.c'
    c_text = c_file.read_text(encoding='utf-8')
    entries = parse_c_entries(c_text)
    assert len(entries) == len(nesie.RX_FILTER_BANDS), f'Entry count mismatch C={len(entries)} PY={len(nesie.RX_FILTER_BANDS)}'

    # Validate hardware ids for all entries first
    for idx, (c_e, py_e) in enumerate(zip(entries, nesie.RX_FILTER_BANDS)):
        assert py_e.hardware_id == c_e['hardware_id'], f'Hardware ID mismatch at {idx}: C {c_e["hardware_id"]} PY {py_e.hardware_id}'

    # Random structural deep sample
    random.seed(12345)
    sample_indices = random.sample(range(len(entries)), min(10, len(entries)))
    dir_mask_map = {
        'UPLINK_DIR_MASK': nesie.UPLINK_DIR_MASK,
        'DOWNLINK_DIR_MASK': nesie.DOWNLINK_DIR_MASK,
        'BOTH_DIR_MASK': nesie.BOTH_DIR_MASK,
    }
    for idx in sample_indices:
        e = entries[idx]
        py_entry = nesie.RX_FILTER_BANDS[idx]
        assert py_entry.uplink.low_dmhz == e['ul_from']
        assert py_entry.uplink.high_dmhz == e['ul_to']
        assert py_entry.downlink.low_dmhz == e['dl_from']
        assert py_entry.downlink.high_dmhz == e['dl_to']
        assert py_entry.direction_mask == dir_mask_map[e['direction']]
        assert py_entry.ladon_id == e['ladon_id']
        assert py_entry.lte_band == e['lte_band']
        assert py_entry.filter_no == e['filter_no']
        assert py_entry.filters_per_band == e['filters_per_band']
        assert py_entry.extra_data == e['extra_data']
        assert py_entry.band.name == e['band']
        assert py_entry.cal_lookup.name == e['cal_lookup']
        assert isinstance(py_entry.hardware_id, int)
