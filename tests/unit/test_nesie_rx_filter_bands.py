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

# Parse rxFilterBands.c entries (regex captures all fields including extra_data)
C_ENTRY_PATTERN = re.compile(r"""
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

C_FILE = MODULE_PATH / 'rxFilterBands.c'
PY_FILE = MODULE_PATH / 'nesie_rx_filter_bands.py'


def parse_c_entries(c_text: str):
    """Parse C file entries and normalize extra_data values."""
    entries = []
    for m in C_ENTRY_PATTERN.finditer(c_text):
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


def test_generated_filters_match_c_source():
    """Test that generated Python filters match the C source entries."""
    c_text = C_FILE.read_text(encoding='utf-8')
    c_entries = parse_c_entries(c_text)
    py_entries = nesie.RX_FILTER_BANDS

    assert len(c_entries) == len(py_entries), f"Entry count mismatch C={len(c_entries)} PY={len(py_entries)}"

    # Hardware IDs are now sequential indices
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


def test_all_hardware_ids_and_structure():
    """Test all hardware IDs are sequential and validate structure with direction masks."""
    c_text = C_FILE.read_text(encoding='utf-8')
    entries = parse_c_entries(c_text)

    assert len(entries) == len(nesie.RX_FILTER_BANDS), f'Entry count mismatch C={len(entries)} PY={len(nesie.RX_FILTER_BANDS)}'

    # Hardware ids are now sequential indices; verify all entries
    for idx, py_e in enumerate(nesie.RX_FILTER_BANDS):
        assert py_e.hardware_id == idx, f'Hardware ID mismatch at {idx}: expected {idx} got {py_e.hardware_id}'

    # Comprehensive structural validation with direction masks
    random.seed(12345)
    sample_indices = random.sample(range(len(entries)), min(15, len(entries)))
    dir_mask_map = {
        'UPLINK_DIR_MASK': nesie.UPLINK_DIR_MASK,
        'DOWNLINK_DIR_MASK': nesie.DOWNLINK_DIR_MASK,
        'BOTH_DIR_MASK': nesie.BOTH_DIR_MASK,
    }

    for idx in sample_indices:
        e = entries[idx]
        py_entry = nesie.RX_FILTER_BANDS[idx]

        # Frequency ranges
        assert py_entry.uplink.low_dmhz == e['ul_from']
        assert py_entry.uplink.high_dmhz == e['ul_to']
        assert py_entry.downlink.low_dmhz == e['dl_from']
        assert py_entry.downlink.high_dmhz == e['dl_to']

        # Direction mask validation
        assert py_entry.direction_mask == dir_mask_map[e['direction']]

        # Other fields
        assert py_entry.ladon_id == e['ladon_id']
        assert py_entry.lte_band == e['lte_band']
        assert py_entry.filter_no == e['filter_no']
        assert py_entry.filters_per_band == e['filters_per_band']
        assert py_entry.band.name == e['band']
        assert py_entry.cal_lookup.name == e['cal_lookup']
        assert isinstance(py_entry.hardware_id, int)


def test_regex_parses_all_entries():
    """Test that regex successfully parses all entries from C source."""
    c_text = C_FILE.read_text(encoding='utf-8')
    c_entries = parse_c_entries(c_text)

    # Expect at least 60 entries (currently 68+)
    assert len(c_entries) >= 60, f"Unexpectedly low number of parsed entries: {len(c_entries)}"


def test_entry_data_types_and_ranges():
    """Test that all entries have correct data types and reasonable value ranges."""
    py_entries = nesie.RX_FILTER_BANDS

    for idx, entry in enumerate(py_entries):
        # Type checks
        assert isinstance(entry.hardware_id, int), f"Entry {idx}: hardware_id should be int"
        assert isinstance(entry.ladon_id, int), f"Entry {idx}: ladon_id should be int"
        assert isinstance(entry.lte_band, int), f"Entry {idx}: lte_band should be int"
        assert isinstance(entry.filter_no, int), f"Entry {idx}: filter_no should be int"
        assert isinstance(entry.filters_per_band, int), f"Entry {idx}: filters_per_band should be int"

        # Range checks
        assert 0 <= entry.hardware_id < 1000, f"Entry {idx}: hardware_id out of reasonable range"
        assert 0 <= entry.ladon_id < 1000, f"Entry {idx}: ladon_id out of reasonable range"  # Allow 0 for special cases
        assert -50 <= entry.lte_band <= 300, f"Entry {idx}: lte_band out of reasonable range"  # Allow negative for special bands
        assert 0 <= entry.filter_no < 20, f"Entry {idx}: filter_no out of reasonable range"
        assert 0 <= entry.filters_per_band <= 20, f"Entry {idx}: filters_per_band out of reasonable range"  # Allow 0 for special cases

        # Frequency range sanity checks (in decisive MHz units)
        # Check uplink frequency range (allow 0,0 for uplink-only or dummy entries)
        if entry.uplink.low_dmhz == 0 and entry.uplink.high_dmhz == 0:
            # Empty uplink range is valid for downlink-only entries
            pass
        else:
            assert 0 < entry.uplink.low_dmhz <= entry.uplink.high_dmhz, f"Entry {idx}: invalid uplink frequency range"
            assert entry.uplink.high_dmhz < 100000, f"Entry {idx}: uplink frequency too high (>10GHz)"

        # Check downlink frequency range (allow 0,0 for downlink-only or dummy entries)
        if entry.downlink.low_dmhz == 0 and entry.downlink.high_dmhz == 0:
            # Empty downlink range is valid for uplink-only entries
            pass
        else:
            assert 0 < entry.downlink.low_dmhz <= entry.downlink.high_dmhz, f"Entry {idx}: invalid downlink frequency range"
            assert entry.downlink.high_dmhz < 100000, f"Entry {idx}: downlink frequency too high (>10GHz)"


def test_direction_mask_values():
    """Test that direction mask values are valid."""
    valid_masks = {nesie.UPLINK_DIR_MASK, nesie.DOWNLINK_DIR_MASK, nesie.BOTH_DIR_MASK}

    for idx, entry in enumerate(nesie.RX_FILTER_BANDS):
        assert entry.direction_mask in valid_masks, f"Entry {idx}: invalid direction_mask {entry.direction_mask}"


def test_unique_hardware_ids():
    """Test that all hardware IDs are unique (should be sequential 0,1,2...)."""
    hardware_ids = [entry.hardware_id for entry in nesie.RX_FILTER_BANDS]
    expected_ids = list(range(len(nesie.RX_FILTER_BANDS)))

    assert hardware_ids == expected_ids, f"Hardware IDs are not sequential: got {hardware_ids[:10]}... expected {expected_ids[:10]}..."


def test_band_and_cal_lookup_enums():
    """Test that band and cal_lookup references are valid enum values."""
    for idx, entry in enumerate(nesie.RX_FILTER_BANDS):
        # These should be enum instances, not just strings
        assert hasattr(entry.band, 'name'), f"Entry {idx}: band should be an enum with name attribute"
        assert hasattr(entry.cal_lookup, 'name'), f"Entry {idx}: cal_lookup should be an enum with name attribute"

        # Names should start with expected prefixes
        assert entry.band.name.startswith('BAND_FILTER_'), f"Entry {idx}: band name should start with 'BAND_FILTER_'"
        assert entry.cal_lookup.name.startswith('COVERT872CALDATALOOKUP_'), f"Entry {idx}: cal_lookup name should start with 'COVERT872CALDATALOOKUP_'"
