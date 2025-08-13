# NESIE Firmware Filter Band Generation

This directory contains firmware band definition sources (`rxFilterBands.h` / `rxFilterBands.c`) and a Python generator (`generate_rx_filter_bands.py`) that produces the Python mirror module `nesie_rx_filter_bands.py` for use inside Cerberus tests / runtime.

## Purpose
The C sources define the available receive (and duplexor) filters for NESIE hardware in a compact table (`rxFilterBands` array). Maintaining a hand‑written Python copy is error prone. The generator parses the authoritative C/ header definitions and emits:

* IntEnums: `DuplexorDirection`, `BandFilter`, `CalDataLookup` (values preserved from C)
* Bit mask constants: `UPLINK_DIR_MASK`, `DOWNLINK_DIR_MASK`, `BOTH_DIR_MASK`, `EXTRA_DATA_FORREV_MASK`, `EXTRA_DATA_SWAP_FOR_AND_REV_MASK`
* Dataclasses: `FreqRange`, `RxFilterBand`
* List: `RX_FILTER_BANDS` (index aligned 1:1 with the C array order)
* Lookup dictionaries: `BANDS_BY_FILTER`, `FILTERS_BY_LTE_BAND`, `FILTERS_BY_CAL_LOOKUP`
* Helper: `select_filter()` (approximation of the C PASSBAND_CENTRE_SEARCH selection logic)

## Running the Generator
From repository root (virtualenv active):
```
python Cerberus/plugins/products/nesieFirmware/generate_rx_filter_bands.py
```
This overwrites `nesie_rx_filter_bands.py` with freshly parsed content. A message prints the number of parsed entries (should match `rxFilterBandsLen` in C).

Regenerate whenever you change:
* Enum definitions in `rxFilterBands.h`
* Direction / extra data mask macros
* Any entry inside `rxFilterBands.c`

## Parsing Rules
The script searches the C file for the `rxFilterBands` array and applies a regex per entry. After the struct fields it scans the trailing comment for a hardware ID pattern:
```
..., COVERT872CALDATALOOKUP_XXX},  //  0xHH
```
If found, that hexadecimal literal becomes `hardware_id`; otherwise `-1` is assigned.

## RxFilterBand Dataclass
```
RxFilterBand(
  uplink: FreqRange,          # Uplink passband (dMHz units)
  downlink: FreqRange,        # Downlink passband (dMHz); may be 0,0 for single arm filters
  direction_mask: int,        # Bitwise mask (UPLINK_DIR_MASK / DOWNLINK_DIR_MASK)
  ladon_id: int,              # Firmware Ladon ID (0 if not used)
  band: BandFilter,           # Enumerated band filter type
  lte_band: int,              # 3GPP band number (or -1 for non‑3GPP / empty)
  filter_no: int,             # Sequence number within a multi‑filter band group
  filters_per_band: int,      # Total filters required to cover that band
  extra_data: int,            # Bit flags (EXTRA_DATA_* masks)
  cal_lookup: CalDataLookup,  # Calibration lookup enum value
  hardware_id: int            # Parsed from trailing //  0x.. comment; -1 if absent
)
```

`FreqRange.low_dmhz` / `high_dmhz` are in deci‑MHz (100 kHz units) mirroring firmware; convenience properties expose MHz / Hz. `branch_for(direction)` returns the appropriate range; `covers_freq_khz()` performs a passband containment check using the same edge rounding as firmware ( (kHz + 50) // 100 ).

## Selection Helper
`select_filter(freq_khz, bandwidth_khz, direction, fitted_ids=None)` implements a simplified passband centre offset search:
1. Iterate candidate indices (optionally restricted by `fitted_ids`).
2. Skip entries whose required branch is empty or whose direction bit is missing.
3. Choose the filter (excluding the wideband entry) whose passband centre is closest to the requested frequency when the channel (freq ± bandwidth/2) lies wholly inside the passband.
4. Fallback to wideband if nothing else matches.

Return value: index into `RX_FILTER_BANDS` or `SelectionResult.NOT_FOUND` (-1).

## Testing
`tests/unit/test_nesie_rx_filter_bands.py` validates:
* Total entry count parity
* Hardware ID match for every entry
* Random sample deep field comparisons

If the test fails after editing C, regenerate the module.

## Common Issues
* Hardware IDs missing: ensure each C entry ends with `},  //  0xNN` (two spaces before `//`) so the regex finds it.
* Entry count mismatch: confirm the regex still matches the C struct formatting (multi‑line restructuring can break it).
* Direction mask errors: confirm macros remain in `rxFilterBands.h` and not moved to another header.

## Extending
If new enum types or masks are added, include their names in `HEADER_ENUMS_OF_INTEREST` / `MACROS_OF_INTEREST` inside the generator, then regenerate.

## Disclaimer
This file is auto‑generated; manual edits to `nesie_rx_filter_bands.py` will be lost. Always modify the C / header sources then regenerate.
