import importlib.util
import random
import re
from pathlib import Path

# Parse rxFilterBands.c entries capturing hardware_id from trailing comment //  0xHH..
C_ENTRY_PATTERN = re.compile(
    r"""\{\s*\{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*\{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*([A-Z_]+)\s*,\s*(\d+)\s*,\s*(BAND_FILTER_[A-Z0-9_]+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(COVERT872CALDATALOOKUP_[A-Z0-9_]+)\s*}\s*,?\s*//\s*(0x[0-9A-Fa-f]+)""")

C_FILE = Path('Cerberus/plugins/products/nesieFirmware/rxFilterBands.c')
PY_FILE = Path('Cerberus/plugins/products/nesieFirmware/nesie_rx_filter_bands.py')


def parse_c_entries(text: str):
    entries = []
    for m in C_ENTRY_PATTERN.finditer(text):
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


def load_generated_module():
    spec = importlib.util.spec_from_file_location('nesie_rx_filter_bands', PY_FILE)
    assert spec is not None, 'Failed to load spec for nesie_rx_filter_bands'
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_generated_filters_match_c_source():
    c_text = C_FILE.read_text(encoding='utf-8')
    c_entries = parse_c_entries(c_text)
    mod = load_generated_module()

    py_entries = mod.RX_FILTER_BANDS
    assert len(c_entries) == len(py_entries), f"Entry count mismatch C={len(c_entries)} PY={len(py_entries)}"

    # Full sequential comparison of hardware IDs + spot check of structural fields.
    for idx, (c_e, py_e) in enumerate(zip(c_entries, py_entries)):
        assert py_e.hardware_id == c_e['hardware_id'], f"Hardware ID mismatch at index {idx}: C {c_e['hardware_id']} PY {py_e.hardware_id}"

    # Random 10 sample deep comparisons to ensure other fields aligned (seed for determinism)
    random.seed(1234)
    sample_indices = random.sample(range(len(c_entries)), min(10, len(c_entries)))
    for idx in sample_indices:
        c_e = c_entries[idx]
        py_e = py_entries[idx]
        assert (py_e.uplink.low_dmhz, py_e.uplink.high_dmhz) == (c_e['ul_from'], c_e['ul_to'])
        assert (py_e.downlink.low_dmhz, py_e.downlink.high_dmhz) == (c_e['dl_from'], c_e['dl_to'])
        assert py_e.ladon_id == c_e['ladon_id']
        assert py_e.lte_band == c_e['lte_band']
        assert py_e.filter_no == c_e['filter_no']
        assert py_e.filters_per_band == c_e['filters_per_band']
        assert py_e.extra_data == c_e['extra_data']
        # Band enum numeric equality
        assert py_e.band.name == c_e['band']
        assert py_e.cal_lookup.name == c_e['cal_lookup']


def test_regex_parses_all_entries():
    c_text = C_FILE.read_text(encoding='utf-8')
    c_entries = parse_c_entries(c_text)
    # Expect at least 50 (currently 64)
    assert len(c_entries) >= 50, f"Unexpectedly low number of parsed entries: {len(c_entries)}"
