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
Parent delegation utilities (only for `SingleParentDelegationMixin` equip):
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

Some equipment plugins conceptually sit *behind* (or rely on) another plugin (controller, chassis, comms adapter). To simplify user workflow, the shell can auto‑attach the required parent via `getParent` when the child supports delegation.

### When Delegation Is Available
All of the following must be true for `getParent` to succeed:
1. Child class mixes in `SingleParentDelegationMixin`.
2. Child declares a required parent name (returned by `parent_name_required()` — typically from a `REQUIRED_PARENT` attribute).
3. The parent equipment plugin was discovered (shows up in `equip list`).
4. The parent can be successfully initialised (`initialise()` returns truthy / does not raise).

### What `getParent` Does (Simplified Logic)
```python
if not isinstance(equip, SingleParentDelegationMixin):
  print("This equipment does not support parent delegation.")
elif equip.has_parent():
  try:
    print(f"Parent already attached: {equip._p().name}")
  except Exception:
    print("Parent attached but inaccessible (internal error).")
else:
  required = equip.parent_name_required()
  if not required:
    print("No REQUIRED_PARENT declared.")
  else:
    ps = PluginService.instance(); parent = ps.findEquipment(required)
    if parent is None:
      print(f"Required parent '{required}' not found among discovered equipment.")
    else:
      try:
        parent.initialise()
      except Exception as ex:
        print(f"Failed to initialise parent '{parent.name}': {ex}")
      else:
        try:
          equip.attach_parent(parent)
          print(f"Attached parent '{parent.name}'.")
        except Exception as ex:
          print(f"Failed to attach parent: {ex}")
```
It always returns `False` (stay in shell) and never exits.

### Success Example
```
Cerberus> equip
Equipment> list
 #0: 'VisaController' [Equipment]
 #1: 'SigGenA' [Equipment]

Equipment> load SigGenA
Equipment> open
SigGenA> getParent
Attached parent 'VisaController'.
SigGenA> getParent
Parent already attached: VisaController
```

### Missing Parent
```
SigGenA> getParent
Required parent 'VisaController' not found among discovered equipment.
```
Fix: ensure the parent plugin is discoverable (not disabled, driver present) then retry.

### Not a Delegating Plugin
```
OtherEquip> getParent
This equipment does not support parent delegation.
```
Cause: no `SingleParentDelegationMixin`.

### Required Parent Not Declared
```
ChildEquip> getParent
No REQUIRED_PARENT declared.
```
Cause: `parent_name_required()` returned `None`; add the attribute to the plugin.

### Parent Initialisation Failure
```
ChildEquip> getParent
Failed to initialise parent 'VisaController': Timeout opening resource
```
Resolve hardware / connection issues; re‑run after fixing.

### Stale / Corrupted Attachment
```
ChildEquip> getParent
Parent attached but inaccessible (internal error).
```
The child *thinks* it has a parent but internal state is invalid. Use `detachParent` then `getParent` again, or re‑`finalise` both plugins.

### Manual Reverse Attachment
If you are in the *parent* shell you can attach yourself to a child using:
```
ParentEquip> setParentEquip ChildEquip
Attached 'ParentEquip' as parent of 'ChildEquip'.
```
This validates that the child's required parent matches the current parent name.

### Detaching
```
ChildEquip> detachParent
Parent detached.
```
You can then re‑run `getParent` to re‑attach (useful after parent reconfiguration / firmware reset).

### Designing a New Delegating Equipment Plugin
- Inherit from base equipment + `SingleParentDelegationMixin`.
- Declare `REQUIRED_PARENT = "SomeParentName"` (or equivalent the mixin reads).
- Ensure `initialise()` is idempotent so repeated calls are safe.
- Implement `finalise()` so detach/reattach cycles release resources cleanly.
- Avoid heavy side‑effects in the child constructor; defer to `initialise()`.

### When Not to Use Delegation
- Relationship is optional (parent purely enhances functionality) — consider an explicit `setParent` method instead.
- Multiple parents required (delegation mixin supports only a single parent).
- Attachment order must be manually orchestrated due to calibration / configuration prerequisites.

### Quick Troubleshooting Table
| Symptom | Cause | Action |
|---------|-------|--------|
| "This equipment does not support parent delegation." | Missing mixin | Add `SingleParentDelegationMixin` |
| "No REQUIRED_PARENT declared." | Not set / returned `None` | Define `REQUIRED_PARENT` or override `parent_name_required()` |
| Required parent not found | Parent plugin undiscovered | Check discovery logs / enable plugin |
| Init failure | Hardware / driver / address issue | Fix underlying issue; try manual `init` on parent |
| Inaccessible parent after attach | Internal plugin error / stale pointer | `detachParent` then `getParent`; possibly restart shells |

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
