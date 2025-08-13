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

# Updated regex: now captures extra_data as its own group (macro or numeric) so parsing unpack matches.
ENTRY_PATTERN = re.compile(r"""
    \{\s*
        \{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*
        \{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*
        ([A-Z_]+)\s*,\s*
        (\d+)\s*,\s*
        (BAND_FILTER_[A-Z0-9_]+)\s*,\s*(-?\d+)\s*,\s*
        (\d+)\s*,\s*(\d+)\s*,\s*(EXTRA_DATA_[A-Z0-9_]+|-?\d+)\s*,\s*
        (COVERT872CALDATALOOKUP_[A-Z0-9_]+)\s*
    }\s*,?
""", re.VERBOSE)


def parse_c_entries(c_text: str):
    entries = []
    for m in ENTRY_PATTERN.finditer(c_text):
        (ul_from, ul_to, dl_from, dl_to, direction_token, ladon_id, band_token, lte_band,
         filter_no, filters_per_band, extra_data_token, cal_lookup_token) = m.groups()
        # Normalize extra_data (macro -> value lookup if in module, else int)
        if extra_data_token.startswith('EXTRA_DATA_'):
            extra_val = getattr(nesie, extra_data_token, None)
            if extra_val is None:
                # Fallback: unknown macro treat as 0
                extra_val = 0
        else:
            extra_val = int(extra_data_token)
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
            'extra_data': int(extra_val),
            'cal_lookup': cal_lookup_token,
        })
    return entries


def test_all_hardware_ids_and_structure():
    c_file = MODULE_PATH / 'rxFilterBands.c'
    c_text = c_file.read_text(encoding='utf-8')
    entries = parse_c_entries(c_text)
    assert len(entries) == len(nesie.RX_FILTER_BANDS), f'Entry count mismatch C={len(entries)} PY={len(nesie.RX_FILTER_BANDS)}'

    # Hardware ids are now sequential indices; verify.
    for idx, py_e in enumerate(nesie.RX_FILTER_BANDS):
        assert py_e.hardware_id == idx, f'Hardware ID mismatch at {idx}: expected {idx} got {py_e.hardware_id}'

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
        assert py_entry.band.name == e['band']
        assert py_entry.cal_lookup.name == e['cal_lookup']
        assert isinstance(py_entry.hardware_id, int)
