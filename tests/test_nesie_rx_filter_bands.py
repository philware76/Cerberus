import importlib.util
import random
import re
from pathlib import Path

# Parse rxFilterBands.c entries (without relying on trailing hardware id hex comment now removed from semantics)
C_ENTRY_PATTERN = re.compile(r"""
    \{\s*
        \{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*
        \{\s*(\d+)\s*,\s*(\d+)\s*}\s*,\s*
        ([A-Z_]+)\s*,\s*
        (\d+)\s*,\s*
        (BAND_FILTER_[A-Z0-9_]+)\s*,\s*(-?\d+)\s*,\s*
        (\d+)\s*,\s*(\d+)\s*,\s*(?:EXTRA_DATA_[A-Z0-9_]+|-?\d+)\s*,\s*
        (COVERT872CALDATALOOKUP_[A-Z0-9_]+)\s*
    }\s*,?
""", re.VERBOSE)

C_FILE = Path('Cerberus/plugins/products/nesieFirmware/rxFilterBands.c')
PY_FILE = Path('Cerberus/plugins/products/nesieFirmware/nesie_rx_filter_bands.py')


def parse_c_entries(text: str):
    entries = []
    for m in C_ENTRY_PATTERN.finditer(text):
        (ul_from, ul_to, dl_from, dl_to, direction_token, ladon_id, band_token, lte_band,
         filter_no, filters_per_band, cal_lookup_token) = m.groups()
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
            'cal_lookup': cal_lookup_token,
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

    # Hardware IDs now sequential indices
    for idx, py_e in enumerate(py_entries):
        assert py_e.hardware_id == idx, f"Hardware ID mismatch at index {idx}: expected {idx} got {py_e.hardware_id}"

    # Random 10 sample structural comparisons (seed for determinism)
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
        assert py_e.band.name == c_e['band']
        assert py_e.cal_lookup.name == c_e['cal_lookup']


def test_regex_parses_all_entries():
    c_text = C_FILE.read_text(encoding='utf-8')
    c_entries = parse_c_entries(c_text)
    # Expect at least 60 (currently 68)
    assert len(c_entries) >= 60, f"Unexpectedly low number of parsed entries: {len(c_entries)}"
