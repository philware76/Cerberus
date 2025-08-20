# Cerberus Command Shells

This document describes the interactive command shell subsystem found under `Cerberus/cmdShells`. These shells provide a structured, extensible, text‑based interface (built on Python's `cmd.Cmd`) for exploring plugins, configuring equipment & products, composing plans, and running tests.

---
## High‑Level Architecture

```
MainShell
  ├── EquipShell ──> EquipmentShell (per loaded equipment plugin)
  ├── ProductsShell ──> ProductShell (per loaded product plugin)
  ├── TestsShell ──> TestShell (per loaded test plugin)
  ├── DatabaseShell
  ├── ManagerShell
  └── PlanShell

(Shared foundations)
BaseShell → BasePluginShell → RunCommandShell
                ▲                ▲
                │                └─ dynamic dispatch of plugin API methods
PluginsShell (lists & loads plugin-specific shells)
```

### Core Concepts
- **Manager**: Central orchestration object injected into every shell; exposes services (pluginService, planService, chamberService, db, etc.). Lifecycle (`with manager:`) ensures resources are opened/closed correctly.
- **Plugins**: Discoverable entities (equipment, products, tests) exposed through plugin dictionaries in `pluginService`.
- **Shell Types**:
  - *MainShell*: Entry point; routes to subsystem shells.
  - *PluginsShell*: Generic browser/loader for a category of plugins (Equipment, Product, Test).
  - *BasePluginShell*: Adds parameter inspection & lifecycle commands (`init`, `finalise`, param editing UI).
  - *RunCommandShell*: Adds dynamic command parsing for plugin methods (auto‑generates parsers from method signatures for `get*/set*/cmd*/reset`).
  - *{Equipment, Product, Test}Shell*: Concrete shells layering domain‑specific commands over the dynamic base.
  - *PlanShell / ManagerShell / DatabaseShell*: Operate on station configuration, plans & DB maintenance.

### Dynamic Command Resolution
`RunCommandShell` inspects the *base class* of a plugin to build an allow‑list of callable methods whose names:
- start with `get`, `set`, `cmd`, or
- are exactly `reset`

For each such method a minimal `argparse.ArgumentParser` is generated. Optional (typing.Optional / Union[..., None]) parameters become `--named` options; required parameters stay positional. Values are parsed with `ast.literal_eval` for safe conversion of numerics, tuples, dicts, etc.

Key points / nuances:
- Only methods defined on the first direct base class of the plugin (`plugin.__class__.__bases__[0]`) are considered. Brand‑new methods added only in the concrete subclass (and not in its base) will NOT appear unless also declared in that base class.
- Overridden methods keep their signature for parsing (since lookup still uses the base method object for signature construction). If you change a signature in the subclass, ensure the base is updated to match for correct parsing.
- Return values from these methods are ignored unless the method itself prints/logs output; design methods to emit user feedback if needed.
- Method name → command name mapping is 1:1 (case sensitive as written).

Examples (method → shell usage):
```python
class BaseSignalGen:
  def setFrequency(self, hz: float): ...          # usage: setFrequency 1e6
  def getFrequency(self) -> float: ...            # usage: getFrequency
  def setRange(self, start: float, stop: float, step: float | None = None): ...
    # usage: setRange 1e6 2e6 --step 1e3
  def cmdCalibrate(self, mode: str = "fast"): ... # usage: cmdCalibrate --mode "slow"
  def reset(self): ...                            # usage: reset
```
Chaining:
```
setFrequency 100e6; getFrequency; setRange 1e6 2e6 --step 5e3
```

Multiple commands can be chained on one line separated by semicolons:
```
> setFreq 100e6; getFreq; reset
```

Tab completion is extended so these dynamically discovered methods appear as first‑token suggestions.

### Parameter Management
`BasePluginShell` exposes a plugin's grouped parameters (`plugin._groupParams`) for inspection and update:
- `txtParams` – human readable dump
- `listGroups` – show group names
- `getGroupParams <group>` – JSON of one group
- `setGroupParams <json>` – atomic replace of a group's parameters (validates keys)
- `uiParams` – pop up a Qt parameter editor (if GUI libs available)

### Parent Delegation (Equipment)
Equipment that mix in `SingleParentDelegationMixin` can automatically discover and attach required parent equipment (`REQUIRED_PARENT`). `EquipmentShell` provides helper commands to manage this linkage (`getParent`, `setParentEquip`, `detachParent`).

---
## Launching the Main Shell
Run (from repository root):
```
python CerberusCLI.py            # or: py .\CerberusCLI.py (Windows PowerShell)
```
Optional arguments:
- `-f <file.db>` – use a file‑based DB (instead of MySQL / Generic DB)
- `-i <cerberus.ini>` – specify alternate config file

A splash screen (Qt) may display plugin discovery status if GUI libs are present.

---
## Global Conventions
- All shells inherit `quit` / `exit` (immediate or graceful leaving of current shell).
- Commands follow `cmd.Cmd` semantics; `help <command>` or `? <command>` shows inline docstrings.
- Returning `True` from a `do_*` method exits that shell level; most commands return `False` (continue).
- Dynamic plugin method usage:
  - Required args: positional order.
  - Optional args: `--paramName value`.
  - Literal types: `--threshold 0.95` or `--window "(1,2,3)"` (auto literal‑eval).

---
## Shell Reference
Below each section lists static (explicitly implemented) commands. Dynamic plugin methods (auto‑exposed via `RunCommandShell`) are not enumerated individually—use `cmds` inside a plugin shell to list them.

### MainShell (`Cerberus>`)
- `equip` – enter Equipment shell
- `products` – enter Product shell
- `tests` – enter Test shell
- `database` – enter Database shell
- `manager` – enter Manager shell
- `plan` – enter Plan shell
- `exit` / `quit` – leave entire program

### PluginsShell (category shells: `Equipment>`, `Product>`, `Test>`)
- `list` – list discovered plugins with index
- `load <name|index>` – prepare a plugin shell instance (does not enter it)
- `open` – enter the previously loaded plugin shell (`load` first)

(For ProductsShell, `load/open` are overridden by discovery workflow; see below.)

### EquipmentShell (`<EquipmentName>`)
Static domain commands:
- `identity` – query & print instrument identity (VISA devices)
- `checkId` – compare live identity vs DB record for model/station
- `write <cmd>` – raw write (if comms interface)
- `query <cmd>` – raw query & print response
- `saveSettings` – persist equipment settings via DB service
Parent delegation utilities (only for `SingleParentDelegationMixin` equip)  
*(See detailed workflow & troubleshooting in the [In‑Depth Parent Delegation section](#in-depth-equipment-parent-delegation--getparent))*:
- `getParent` – attach declared REQUIRED_PARENT automatically (or show existing)
- `setParentEquip <childName>` – attach this equipment as parent of child
- `detachParent` – detach current parent
Plus dynamic plugin API commands (see `cmds`).

### ProductsShell (`Product>`)
Manages product plugins with a *discovery + connect* workflow (instead of manual `load`/`open`).

Core commands:
- `list` – list all discovered product plugins (like other plugin shells)
- `discover [<sortField>] | [<filterField> <value>]` – perform Ethernet discovery of NESIE devices.
  - No args: discover & default sort by `Name`.
  - One arg: treat as sort field (case-insensitive, must match a column).
  - Two args: `<filterField> <value>` filter (substring, case-insensitive) then default sort by `Name`.
  - Columns are those returned from `EthDiscovery.search()` (e.g., `ID`, `IP Address`, `Name`, `Type`, etc.).
- `connect <Idx|IP>` – select a previously discovered device (by table index or IP) then automatically:
  1. Resolve product ID → plugin name via `PROD_ID_MAPPING`.
  2. Load corresponding product plugin shell.
  3. Open (`cmdloop`) the `ProductShell` for interactive control.

Notes:
- `load` / `open` exist (inherited) but are intentionally not the primary workflow; use `discover` + `connect` for correct contextual setup (PIC IP, product type, ID).
- Run `discover` again to refresh device list; previous indices are recalculated.

### ProductShell (`<ProductName>` / `<ProductName> @<IP>` / `<ProductName> DA@<IP>`)
Entered automatically after `connect`.

Product-specific commands:
- `select` – mark this product as the active DUT used by tests.
- `openPIC` – open PIC controller; after success, prompt updates with `@<PIC_IP>` and DA host is learned.
- `openDA` – open / (re)open DA BIST connection (auto-closes previous if open).
- `stopNesie` – stop the NESIE daemon via SSH on the DA host.
- `killNesie` – kill the NESIE daemon process via SSH.
- `getBandsFitted` – read EEPROM → list fitted bands.
- `slotDetails` – show slot index → band mapping (`SLOT_DETAILS_DICT`).
- `saveSettings` – persist product plugin settings to DB.
- Dynamic plugin API methods (see `cmds`) – generated from base class `get*/set*/cmd*/reset` methods.

Discovery workflow summary:
```
Cerberus> products
Product> discover           # build table
Product> discover ID K      # example: filter where ID contains 'K'
Product> connect 0          # connect by index (or use an IP address)
<ProductName> select        # set as DUT
<ProductName> openPIC       # learn DA IP
<ProductName> openDA        # open BIST link
```

Edge cases:
- Empty discovery → "No devices found!" (state cleared)
- Bad filter column or sort field → warning; original list not reused
- Connecting without discovery → guidance to run `discover`
- Non-numeric / invalid index → validation error

### PICShell (`<ProductName> PIC@<PIC_IP>`)
Opened from a ProductShell via `openPIC`. Provides low‑level power & status for the product controller (PIC) and discovers the DA (BIST) host IP.

Commands:
- `getStatus` – (auto‑runs on entry) instantiate a `NesiePIC`, print power state, DA address, temperature. If DA address != `0.0.0.0`, informs you the DA is ready and you can exit back.
- `getDA` – Re‑query & print DA Address; warns if still `0.0.0.0`.
- `powerOn` – Request power on and (because an arg is always passed internally) wait with progress dots until boot complete or timeout (~90s).
- `powerOff` – Request power off and wait for shutdown (dots until completion or timeout).
- `exit` – Return to the ProductShell; collected DA IP is propagated so `openDA` can be used there.

Typical flow:
```
<ProductName> openPIC
<ProductName> PIC@192.168.1.120> powerOn
... (dots) ...
Powered On
<ProductName> PIC@192.168.1.120> getStatus
You can exit back as we have the DA Address
<ProductName> PIC@192.168.1.120> exit
<ProductName> @192.168.1.120> openDA
```

### TestsShell (`Test>`)
Generic plugin list/load/open identical to Equipment shell.

### TestShell (`<TestName>`)
- `run` – execute the test (warns if no product selected)
- `saveSettings` – persist test settings
- Dynamic plugin API (`cmds` to list parameterizable methods)

### ManagerShell (`Manager>`)
- `setChamber <ClassName>` – set chamber class name in DB
- `getChamber` – show stored chamber class name
- `savePlan` – persist current test plan for station
- `setTestPlan <PlanId>` – set active test plan by ID
- `listPlans` – list all available stored plans with metadata

### PlanShell (`Plan>`)
- `new <plan_name>` – create a new in‑memory plan
- `save` – persist current plan; shows returned DB id
- `add <test_name>` – add test to current plan
- `remove <test_name>` – remove test from plan
- `show` – display plan details & test list
- `listPlans` – show plan list in GUI widget (Qt)

### DatabaseShell (`Database>`)
- `wipeDB` – drop core tables (requires explicit `YES` confirmation; destructive!)

### BasePluginShell (applies within Equipment/Product/Test shells)
- `txtParams` – human readable parameter groups
- `listGroups` – list names of parameter groups
- `getGroupParams <group>` – JSON of a group's parameters
- `setGroupParams <json>` – replace a group's parameters (validate & atomic)
- `uiParams` – Qt GUI parameter editor
- `init` – initialise plugin (open hardware / prepare state)
- `finalise` – close / finalise plugin
- `exit` – finalise (if not already) and leave shell

### RunCommandShell Extras
- `cmds` – list dynamic plugin commands & their signatures (or usage for `cmds <name>`)
- (Multiple command chaining with `;`)

---
## Usage Patterns & Examples

List equipment, load by index, open shell:
```
Cerberus> equip
Equipment> list
Equipment> load 0
Equipment> open
<EquipName> cmds          # List dynamic methods
<EquipName> getStatus
<EquipName> setMode MODE_A
<EquipName> query "*IDN?"
```

Connect to a product discovered on the network:
```
Cerberus> products
Product> discover ID K    # filter column 'ID' contains 'K'
Product> connect 0        # or connect 192.168.1.45
<MyProduct> select
<MyProduct> openPIC
<MyProduct> openDA
<MyProduct> stopNesie
```

Build & save a plan:
```
Cerberus> plan
Plan> new Regression
Plan> add TxLevelTest
Plan> add DynamicRangeTest
Plan> show
Plan> save
```

Run a test (after selecting DUT):
```
Cerberus> tests
Test> list
Test> load TxLevelTest
Test> open
TxLevelTest> run
```

Parent delegation:
```
Cerberus> equip
Equipment> load ChildDevice
Equipment> open
ChildDevice> getParent      # auto attaches required parent if present
ChildDevice> detachParent
```

---
## In‑Depth: Equipment Parent Delegation & `getParent`

This section uses the real `SMB100A` (R&S signal generator) as the **parent** and the `NRP-Z24` power sensor (implemented as `NRP_Z24`) as the **child** to illustrate how parent delegation works.

### Why Delegation Here?
Rohde & Schwarz NRP sensors communicate via an existing VISA session owned by the signal generator. Instead of every sensor opening its own physical VISA connection, the design:
- Keeps a **single hardware session** in the parent (`SMB100A`, a `VISADevice`).
- Exposes each sensor as a *distinct* plugin (so dependency selection & tests can refer to them individually).
- Lets the sensor forward SCPI commands through the parent using a standardised interface supplied by the delegation mixin.

### Child Declaration (`BaseNRPPowerMeter`)
```python
class BaseNRPPowerMeter(SingleParentDelegationMixin, BasePowerMeter):
  REQUIRED_PARENT: str | None = "SMB100A"  # Declarative dependency

  def initialise(self, init=None) -> bool:
    if not self._ensure_parent(init):
      return False  # Fails fast if parent not provided / cannot attach
    return BasePowerMeter.initialise(self)
```
`REQUIRED_PARENT` advertises to both the shell and any dependency resolver what parent name must be attached. The mixin supplies `parent_name_required()`, `has_parent()`, `attach_parent()`, and `detach_parent()`.

### Concrete Child (`NRP_Z24`)
```python
class NRP_Z24(BaseNRPPowerMeter):
  def setFrequency(self, freq: float) -> bool:
    return self.command(f"SENSe:FREQuency {freq}")

  def getPowerReading(self) -> float:
    resp = self.query("READ?")
    ...
```
Because `setFrequency` & `getPowerReading` are defined on the child's **base** (`BasePowerMeter` / or its first base in MRO) or follow the naming rules, they become dynamic shell commands (`setFrequency`, `getPowerReading`).

### Parent (`SMB100A`)
Owns the VISA connection (via `VisaInitMixin` + `VISADevice`) and provides low-level SCPI helpers (`command`, `query`, etc.) that the child will reuse once attached.

### Workflow in the Shell
1. Discover plugins (manager startup does this automatically).
2. Open Equipment shell.
3. Load & open the **parent** (optional – `getParent` can initialise it if not already).
4. Load & open the **child**.
5. Run `getParent` inside the child shell to auto‑attach.

Example session:
```
Cerberus> equip
Equipment> list
 #0: 'SMB100A' [SigGen]
 #1: 'NRP-Z24' [NRPPowerMeter]

Equipment> load NRP-Z24
Equipment> open
NRP-Z24> getParent
Attached parent 'SMB100A'.

# Now dynamic commands from the *base* class + child are available
NRP-Z24> setFrequency 1e9
NRP-Z24> getPowerReading
 -34.97
```

Re-running `getParent` after attachment:
```
NRP-Z24> getParent
Parent already attached: SMB100A
```

### What `getParent` Does (Simplified for This Pair)
```python
if isinstance(child, SingleParentDelegationMixin):
  if child.has_parent():
    print(f"Parent already attached: {child._p().name}")
  else:
    required = child.parent_name_required()  # -> "SMB100A"
    parent = PluginService.instance().findEquipment(required)
    if parent:
      parent.initialise()
      child.attach_parent(parent)
      print("Attached parent 'SMB100A'.")
    else:
      print("Required parent 'SMB100A' not found among discovered equipment.")
```

### Failure Scenarios (Concrete)
| Scenario | Example Output | Cause / Fix |
|----------|----------------|-------------|
| Parent not discovered | `Required parent 'SMB100A' not found among discovered equipment.` | Ensure SMB100A plugin is enabled & discovered; restart manager if necessary. |
| Parent VISA init fails | `Failed to initialise parent 'SMB100A': <error>` | Check cabling, VISA resource string, permissions. Try `load SMB100A` + `open` + `init` manually. |
| Child missing REQUIRED_PARENT | `No REQUIRED_PARENT declared.` | Add `REQUIRED_PARENT = "SMB100A"` to base or override `parent_name_required()`. |
| Not delegating | `This equipment does not support parent delegation.` | Child class missing `SingleParentDelegationMixin` in MRO. |
| Stale attachment | `Parent attached but inaccessible (internal error).` | Underlying parent object invalid; `detachParent` then `getParent`, or re‑`finalise` both. |

### Detach & Re‑Attach
```
NRP-Z24> detachParent
Parent detached.
NRP-Z24> getParent
Attached parent 'SMB100A'.
```
Useful after parent firmware reload or configuration change.

### Design Checklist for New Children Like `NRP-Z24`
- [x] Inherit from `SingleParentDelegationMixin` before the functional base (so mixin hooks precedence if needed).
- [x] Set `REQUIRED_PARENT` to the canonical parent plugin name.
- [x] Keep `initialise()` lightweight; rely on parent for heavy I/O setup.
- [x] Use parent provided `command/query` instead of opening new sessions.
- [x] Ensure parent initialisation is idempotent (multiple calls safe).

### When NOT to Use This Pattern
- Child could optionally work stand‑alone (parent only augments features).
- Many children need *different* context objects simultaneously (consider a pool / manager object instead).
- Multiple parents are required (single parent mixin is insufficient; introduce a custom multi‑parent coordination layer).

### Quick Troubleshooting Table
| Symptom | Cause | Action |
|---------|-------|--------|
| "This equipment does not support parent delegation." | Missing mixin | Add `SingleParentDelegationMixin` |
| "No REQUIRED_PARENT declared." | Not set / returned `None` | Define `REQUIRED_PARENT` or override `parent_name_required()` |
| Required parent not found | Parent plugin undiscovered | Enable & discover `SMB100A` |
| Init failure | Hardware / VISA resource issue | Verify VISA address; manually initialise parent |
| Inaccessible parent after attach | Internal plugin error / stale pointer | `detachParent` then `getParent` |

---
## Error Handling & Edge Cases
- Dynamic command parse errors show concise usage (custom `SilentArgParser`) instead of exiting the shell.
- Unknown parameters in `setGroupParams` are rejected (prevents silent typos).
- Parent delegation commands guard against unsupported equipment and missing required parents.
- `discover` handles empty results, unknown columns, filtering producing zero matches, and preserves a clean state.
- Destructive DB actions require explicit confirmation (`wipeDB`).

---
## Extending the Shell Subsystem
1. Create a new plugin base type (e.g., `BaseAnalyzer`) with methods following `get*/set*/cmd*/reset` naming to expose them automatically.
2. Register plugins with `pluginService`.
3. (Optional) Create a specialized shell if you need extra domain commands; inherit from `RunCommandShell` (for dynamic APIs) or `BasePluginShell`.
4. Add navigation command to `MainShell` if this is a top‑level category; otherwise rely on `PluginsShell` loading.

### Shell Naming & Auto‑Loading Convention
`PluginsShell.do_load` constructs the shell class name dynamically: `<PluginType>Shell` (e.g., `EquipmentShell`, `ProductShell`, `TestShell`). It then imports the module by lowercasing the first character (e.g., `EquipmentShell` → `equipmentShell`). To enable automatic loading for a new plugin category:
- Module path: `Cerberus/cmdShells/<lowerFirstName>Shell.py`
- Class name: `<TypeName>Shell` inheriting from `RunCommandShell` or `BasePluginShell`
Maintain this pattern so `import_module` + `getattr` succeed.

### Adding a New Command to a Shell
Define `def do_<command>(self, arg):` inside the shell class. Return `True` to exit that shell level; any other return (or no return) keeps you in the shell. If a dynamic method name and a `do_` method collide, the explicit `do_` wins.

### Dependencies & Optional Components
| Component | Purpose | Optional? |
|-----------|---------|-----------|
| PySide6 | GUI splash, parameter editor, plan list widget | Yes (shells still work headless) |
| tabulate | Pretty table formatting for product discovery | Yes (would fallback to manual prints) |
| iniconfig | Load `cerberus.ini` configuration | Required for config loading |
| Database backend / MySQL | Persistent storage (equipment, products, plans, tests) | Required unless `-f` FileDatabase used |
| SSH / related libs (via product plugins) | Product SSH operations (`stopNesie`, `killNesie`) | Only for those commands |

Graceful Degradation:
- GUI-dependent commands catch `ImportError` and print a message instead of crashing.
- Missing optional libs only affect the subset of commands that rely on them.

### Adding Custom Command Parsing
If a method needs richer argument semantics than `RunCommandShell` provides, implement a dedicated `do_<name>` method in the concrete shell; it will take precedence over dynamic dispatch.

---
## Security & Safety Notes
- Raw equipment commands (`write/query`) are passed through; misuse can put hardware into invalid states. Use cautiously.
- SSH operations (`stopNesie`, `killNesie`) assume key file exists and host is trusted.
- `wipeDB` is irreversible—ensure you're targeting the correct environment.

---
## Troubleshooting
| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| `Error: '<method>' is not a valid command.` | Method name not in plugin base class or naming convention | Use `cmds` to inspect allowed names; adjust plugin implementation |
| `Unknown parameter name(s)` during `setGroupParams` | Misspelled or new param not defined in group | Retrieve with `getGroupParams` first; edit keys to match |
| `Please run discover before selecting a Nesie` | `connect` invoked before `discover` | Run `discover` to populate device list |
| Parent attach fails | Required parent not initialised or missing | Ensure parent plugin discovered and initialises cleanly |
| No response to `query` | Not a `CommsInterface` plugin or device offline | Confirm equipment type & connectivity |

---
## Glossary
- **DUT** – Device Under Test.
- **BIST** – Built‑In Self Test subsystem on product (DA host).
- **NESIE** – Product family / platform discovered over Ethernet.
- **PIC** – Microcontroller interface to DA / product internals.

---
## Versioning
This README documents the command interfaces present as of 2025‑08‑20. Future additions should append new commands and update architecture notes accordingly.

---
## Quick Command Index
(Abbreviated; see sections above for details.)

Main: equip | products | tests | database | manager | plan | exit
EquipmentShell: identity | checkId | write | query | saveSettings | getParent | setParentEquip | detachParent | cmds
ProductsShell: discover | connect
ProductShell: select | openPIC | openDA | stopNesie | killNesie | getBandsFitted | slotDetails | saveSettings | cmds
TestsShell/TestShell: run | saveSettings | cmds
ManagerShell: setChamber | getChamber | savePlan | setTestPlan | listPlans
PlanShell: new | save | add | remove | show | listPlans
DatabaseShell: wipeDB
BasePluginShell: txtParams | listGroups | getGroupParams | setGroupParams | uiParams | init | finalise | exit
RunCommandShell: cmds (and dynamic plugin API methods)
PICShell: getStatus | getDA | powerOn | powerOff | exit

---
Happy testing!
