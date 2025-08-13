"""Generate Python representations of NESIE rxFilterBands.

Parses rxFilterBands.h / rxFilterBands.c to emit nesie_rx_filter_bands.py with:
 - IntEnum DuplexorDirection, BandFilter, CalDataLookup
 - Constants: UPLINK_DIR_MASK, DOWNLINK_DIR_MASK, BOTH_DIR_MASK, EXTRA_DATA_* masks
 - Dataclasses FreqRange, RxFilterBand
 - List RX_FILTER_BANDS (index aligned to C array)
 - Dicts: BANDS_BY_FILTER (BandFilter -> list[RxFilterBand]), FILTERS_BY_LTE_BAND, FILTERS_BY_CAL_LOOKUP
 - Helper selection function select_filter(freq_khz, bandwidth_khz, direction, fitted_ids=None)

Frequency units: C stores deci-MHz (dMHz). We preserve raw dMHz and expose derived MHz / Hz properties.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).parent
HEADER = ROOT / "rxFilterBands.h"
CFILE = ROOT / "rxFilterBands.c"
OUTPUT = ROOT / "nesie_rx_filter_bands.py"

INT_MAX = 2_147_483_647  # Matches limits.h 32-bit

_ENUM_TYPENAME_PATTERN = re.compile(r"typedef\s+enum\s*{(?P<body>.*?)}\s*(?P<name>\w+)\s*;", re.S)
_ENUM_ENTRY_PATTERN = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(=\s*(?P<value>[^,/]+))?\s*(,)?\s*(//.*)?$")
_DEFINE_PATTERN = re.compile(r"#define\s+(?P<name>[A-Z0-9_]+)\s+\(?([^\s)]+)\)?")
_ARRAY_PATTERN = re.compile(r"RxFilterBand_t\s+const\s+rxFilterBands\s*\[\s*]\s*=\s*{(?P<body>.*?)};", re.S)
# Updated pattern: allow EXTRA_DATA_* macros or numeric literals for extra_data field.
_ENTRY_PATTERN = re.compile(
    r"""
    \{\s*
        \{\s*(?P<ul_from>\d+)\s*,\s*(?P<ul_to>\d+)\s*}\s*,\s*
        \{\s*(?P<dl_from>\d+)\s*,\s*(?P<dl_to>\d+)\s*}\s*,\s*
        (?P<direction>[A-Z_]+)\s*,\s*
        (?P<ladon_id>\d+)\s*,\s*
        (?P<band>BAND_FILTER_[A-Z0-9_]+)\s*,\s*
        (?P<lte_band>-?\d+)\s*,\s*
        (?P<filter_no>\d+)\s*,\s*
        (?P<filters_per_band>\d+)\s*,\s*
        (?P<extra>(?:-?\d+|EXTRA_DATA_[A-Z0-9_]+))\s*,\s*
        (?P<cal_lookup>COVERT872CALDATALOOKUP_[A-Z0-9_]+)\s*
    }\s*,?[^\n]*
    """,
    re.VERBOSE | re.M,
)

HEADER_ENUMS_OF_INTEREST = {
    "duplexor_direction_t": "DuplexorDirection",
    "band_filter_t": "BandFilter",
    "Covert872CalDataLookup_t": "CalDataLookup",
}

MACROS_OF_INTEREST = {
    "UPLINK_DIR_MASK",
    "DOWNLINK_DIR_MASK",
    "BOTH_DIR_MASK",
    "EXTRA_DATA_FORREV_MASK",
    "EXTRA_DATA_SWAP_FOR_AND_REV_MASK",
}


@dataclass
class ParsedEnum:
    name: str
    entries: List[Tuple[str, int]]


def parse_enums(header_text: str) -> Dict[str, ParsedEnum]:
    enums: Dict[str, ParsedEnum] = {}
    for m in _ENUM_TYPENAME_PATTERN.finditer(header_text):
        body = m.group("body")
        raw_name = m.group("name")
        if raw_name not in HEADER_ENUMS_OF_INTEREST:
            continue
        entries: List[Tuple[str, int]] = []
        current_val: Optional[int] = None
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            m_entry = _ENUM_ENTRY_PATTERN.match(line)
            if not m_entry:
                continue
            ename = m_entry.group("name")
            val_text = m_entry.group("value")
            if val_text is not None:
                val_text = val_text.strip()
                if val_text == "INT_MAX":
                    value = INT_MAX
                else:
                    try:
                        value = int(val_text, 0)
                    except ValueError:
                        continue
                current_val = value
            else:
                if current_val is None:
                    current_val = 0
                else:
                    current_val += 1
            entries.append((ename, current_val))
        enums[raw_name] = ParsedEnum(raw_name, entries)
    return enums


def parse_macros(header_text: str) -> Dict[str, int]:
    values: Dict[str, int] = {}
    for line in header_text.splitlines():
        m = _DEFINE_PATTERN.match(line)
        if not m:
            continue
        name = m.group("name")
        if name not in MACROS_OF_INTEREST:
            continue
        token = line.split()[2]
        token = token.strip("()")
        if name == "BOTH_DIR_MASK":
            # derived below
            continue
        try:
            values[name] = int(token, 0)
        except ValueError:
            continue
    if "UPLINK_DIR_MASK" in values and "DOWNLINK_DIR_MASK" in values:
        values["BOTH_DIR_MASK"] = values["UPLINK_DIR_MASK"] | values["DOWNLINK_DIR_MASK"]
    return values


def extract_array_body(c_text: str) -> str:
    m = _ARRAY_PATTERN.search(c_text)
    if not m:
        raise RuntimeError("Could not locate rxFilterBands array in C file")
    return m.group("body")


def parse_array_entries(array_body: str):
    entries = []
    for m in _ENTRY_PATTERN.finditer(array_body):
        gd = m.groupdict()
        entries.append({
            "ul_from": int(gd["ul_from"]),
            "ul_to": int(gd["ul_to"]),
            "dl_from": int(gd["dl_from"]),
            "dl_to": int(gd["dl_to"]),
            "direction": gd["direction"],
            "ladon_id": int(gd["ladon_id"]),
            "band": gd["band"],
            "lte_band": int(gd["lte_band"]),
            "filter_no": int(gd["filter_no"]),
            "filters_per_band": int(gd["filters_per_band"]),
            # keep raw token; could be number or EXTRA_DATA_* macro
            "extra_data": gd["extra"],
            "cal_lookup": gd["cal_lookup"],
        })
    return entries


def generate_module(enums: Dict[str, ParsedEnum], macros: Dict[str, int], entries) -> str:
    # Build enum class code
    def enum_code(py_name: str, parsed: ParsedEnum) -> str:
        lines = [f"class {py_name}(IntEnum):"]
        for name, value in parsed.entries:
            lines.append(f"    {name} = {value}")
        lines.append("")
        return "\n".join(lines)

    # Map C enum names to Python names
    enum_py_map = {
        "duplexor_direction_t": "DuplexorDirection",
        "band_filter_t": "BandFilter",
        "Covert872CalDataLookup_t": "CalDataLookup",
    }

    enum_sections = []
    for c_name, py_name in enum_py_map.items():
        if c_name in enums:
            enum_sections.append(enum_code(py_name, enums[c_name]))

    macro_lines = [f"{k} = {v}" for k, v in sorted(macros.items())]

    @dataclass
    class _Tmp:  # local only
        pass

    dataclasses_code = """@dataclass
class FreqRange:
    low_dmhz: int
    high_dmhz: int

    @property
    def low_mhz(self) -> float: return self.low_dmhz / 10.0
    @property
    def high_mhz(self) -> float: return self.high_dmhz / 10.0
    @property
    def low_hz(self) -> int: return self.low_dmhz * 100_000
    @property
    def high_hz(self) -> int: return self.high_dmhz * 100_000

    def contains_dmhz(self, v: int) -> bool:
        if self.low_dmhz == 0 and self.high_dmhz == 0:
            return False
        return self.low_dmhz <= v <= self.high_dmhz

@dataclass
class RxFilterBand:
    uplink: FreqRange
    downlink: FreqRange
    direction_mask: int
    ladon_id: int
    band: BandFilter
    lte_band: int
    filter_no: int
    filters_per_band: int
    extra_data: int
    cal_lookup: CalDataLookup
    hardware_id: int

    def branch_for(self, direction: 'DuplexorDirection') -> FreqRange:
        if direction == DuplexorDirection.DD_UPLINK:
            return self.uplink
        elif direction == DuplexorDirection.DD_DOWNLINK:
            return self.downlink
        else:
            # Unknown: choose non-empty
            return self.uplink if self.uplink.high_dmhz else self.downlink

    def covers_freq_khz(self, freq_khz: int, bandwidth_khz: int, direction: 'DuplexorDirection') -> bool:
        # Convert kHz to dMHz (freq_khz / 100)
        low_edge_dmhz = (freq_khz - (bandwidth_khz + 1)//2 + 50) // 100
        high_edge_dmhz = (freq_khz + (bandwidth_khz + 1)//2 + 50) // 100
        rng = self.branch_for(direction)
        if rng.low_dmhz == 0 and rng.high_dmhz == 0:
            return False
        return rng.low_dmhz <= low_edge_dmhz and high_edge_dmhz <= rng.high_dmhz

"""

    list_lines = ["RX_FILTER_BANDS: list[RxFilterBand] = ["]
    for idx, e in enumerate(entries):
        extra_raw = e['extra_data']
        extra_code = extra_raw if not extra_raw.lstrip('-').isdigit() else str(int(extra_raw))
        list_lines.append(
            f"    RxFilterBand(FreqRange({e['ul_from']}, {e['ul_to']}), FreqRange({e['dl_from']}, {e['dl_to']}), "
            f"{e['direction']}, {e['ladon_id']}, BandFilter.{e['band']}, {e['lte_band']}, {e['filter_no']}, {e['filters_per_band']}, {extra_code}, CalDataLookup.{e['cal_lookup']}, {idx}),")
    list_lines.append("]\n")

    helper_code = """# Derived lookup dictionaries
BANDS_BY_FILTER: dict[BandFilter, list[RxFilterBand]] = {}
FILTERS_BY_LTE_BAND: dict[int, list[RxFilterBand]] = {}
FILTERS_BY_CAL_LOOKUP: dict[CalDataLookup, list[RxFilterBand]] = {}
for idx, f in enumerate(RX_FILTER_BANDS):
    BANDS_BY_FILTER.setdefault(f.band, []).append(f)
    FILTERS_BY_LTE_BAND.setdefault(f.lte_band, []).append(f)
    FILTERS_BY_CAL_LOOKUP.setdefault(f.cal_lookup, []).append(f)

WIDEBAND_INDEX = 1  # As per C constant

class SelectionResult(IntEnum):
    NOT_FOUND = -1


def _centre_offset(filter_band: RxFilterBand, freq_dmhz: int, direction: DuplexorDirection) -> int:
    rng = filter_band.branch_for(direction)
    centre = (rng.low_dmhz + rng.high_dmhz) // 2
    return abs(freq_dmhz - centre)


def select_filter(freq_khz: int, bandwidth_khz: int, direction: DuplexorDirection, fitted_ids: list[int] | None = None) -> int:
    # Select best filter index akin to PASSBAND_CENTRE_SEARCH logic.
    # If fitted_ids provided restrict search to those indices, else all.
    # Returns filter index or -1.
    if freq_khz >= 6_000_000:
        return SelectionResult.NOT_FOUND
    freq_dmhz = (freq_khz + 50) // 100
    low_edge_dmhz = (freq_khz - (bandwidth_khz + 1)//2 + 50) // 100
    high_edge_dmhz = (freq_khz + (bandwidth_khz + 1)//2 + 50) // 100

    indices = fitted_ids if fitted_ids is not None else list(range(len(RX_FILTER_BANDS)))
    wideband_present = False
    wideband_site = -1
    best_index = -1
    best_offset = 10**9

    for idx in indices:
        if idx < 0 or idx >= len(RX_FILTER_BANDS):
            continue
        f = RX_FILTER_BANDS[idx]
        if idx == WIDEBAND_INDEX:
            wideband_present = True
            wideband_site = idx
        # Check direction mask
        mask = UPLINK_DIR_MASK if direction == DuplexorDirection.DD_UPLINK else DOWNLINK_DIR_MASK
        if (f.direction_mask & mask) == 0:
            continue
        rng = f.branch_for(direction)
        if rng.low_dmhz == 0 or rng.high_dmhz == 0:
            continue
        if rng.low_dmhz <= low_edge_dmhz and high_edge_dmhz <= rng.high_dmhz:
            offset = _centre_offset(f, freq_dmhz, direction)
            if offset < best_offset and idx != WIDEBAND_INDEX:
                best_offset = offset
                best_index = idx
    if best_index == -1 and wideband_present:
        best_index = wideband_site
    return best_index
"""

    content = [
        "# Auto-generated by generate_rx_filter_bands.py. Do not edit manually.",
        "from __future__ import annotations",
        "from dataclasses import dataclass",
        "from enum import IntEnum",
        "", *enum_sections,
        *macro_lines,
        "", dataclasses_code,
        *list_lines,
        helper_code,
        "__all__ = ['DuplexorDirection','BandFilter','CalDataLookup','FreqRange','RxFilterBand',\n"
        "           'RX_FILTER_BANDS','BANDS_BY_FILTER','FILTERS_BY_LTE_BAND','FILTERS_BY_CAL_LOOKUP',\n"
        "           'select_filter','UPLINK_DIR_MASK','DOWNLINK_DIR_MASK','BOTH_DIR_MASK',\n"
        "           'EXTRA_DATA_FORREV_MASK','EXTRA_DATA_SWAP_FOR_AND_REV_MASK']",
    ]
    return "\n".join(content) + "\n"


def main():
    header_text = HEADER.read_text(encoding="utf-8")
    c_text = CFILE.read_text(encoding="utf-8")
    enums = parse_enums(header_text)
    macros = parse_macros(header_text)
    array_body = extract_array_body(c_text)
    entries = parse_array_entries(array_body)
    if not entries:
        raise SystemExit("No entries parsed for rxFilterBands")
    module_text = generate_module(enums, macros, entries)
    OUTPUT.write_text(module_text, encoding="utf-8")
    print(f"Generated {OUTPUT} with {len(entries)} filter entries")


if __name__ == "__main__":
    main()
