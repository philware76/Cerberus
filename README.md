<div align="center">

# Cerberus

Robust, extensible CLI + (auto‑generated) GUI platform for Equipment control, Product management, Calibration & Test execution.

---

</div>

Cerberus is a highly flexible plugin‑driven framework that lets you define and orchestrate:

* Equipment (any controllable resource: instruments, fixtures, services, simulated devices, files, etc.)
* Products (logical device / DUT abstractions; optionally discovered over Ethernet)
* Tests (calibration, verification, utility or maintenance routines; they may or may not target a Product)

The same infrastructure supports traditional product verification, ad‑hoc engineering utilities (e.g. cable calibration), calibration workflows, and automation scripts. Nothing in the core constrains you to RF / comms equipment, VISA resources, or even having a Product at all.

---

## 1. High‑Level Overview

At runtime the top‑level application (`CerberusCLI.py`) launches an interactive shell hierarchy:

```
MainShell (application root)
 ├─ Equipment Shells (one per Equipment plugin)
 ├─ Product Shells   (one per Product plugin)
 └─ Test Shells      (one per Test plugin)
```

All shells are generic: they can introspect a plugin's parameter groups and auto‑render a UI window with appropriate widgets (form inputs, selectors, etc.) without bespoke code. This keeps new plugin onboarding fast—define parameters in code, get a usable interactive & GUI representation “for free.”

Core architectural pillars:

| Concern              | Component(s)                                    | Summary |
|----------------------|--------------------------------------------------|---------|
| Plugin discovery     | `PluginDiscovery`, `pluggy`                      | Dynamically imports & registers Equipment / Product / Test factories. |
| Plugin lifecycle     | `BasePlugin` (+ specialisations)                 | Initialise → Configure → (Run / Use) → Finalise. |
| Requirements resolve | `PluginService.getRequirements()`               | Determines & selects suitable Equipment for a Test. |
| Execution            | `Executor.runTest()`                            | Injects Product (optional), initialises required Equipment, runs & finalises Test, returns Result object. |
| Networking discovery | `EthDiscovery.search()`                         | Broadcast discovery to find candidate Products (NESIE devices). |
| Persistence          | `GenericDB` (MySQL) / File DB (tests)            | Automatic parameter versioning & retrieval per station / plugin / group. |
| Persistence          | `GenericDB` (MySQL) / File DB (tests)            | Automatic parameter versioning & retrieval per station / plugin / group. ([GenericDB details](Cerberus/database/README_GenericDB.md)) |
| State management     | `Manager`                                        | Coordinates load/save of all plugin parameters and lifecycle finalisation. |
| Planning             | `plan`, `planService`                            | Test plan composition & serialisation. |

---

## 2. Plugin System Fundamentals

Cerberus uses [pluggy](https://pluggy.readthedocs.io/) to declare hook specifications and register plugin implementations discovered under `Cerberus/plugins/`.

Plugin categories (each subfolder contains leaf folders with concrete plugin modules):

```
Cerberus/plugins/
	equipment/
	products/
	tests/
```

Each concrete plugin file ends with `Equipment.py`, `Product.py`, or `Test.py` (case‑sensitive suffix), enabling `PluginDiscovery` to match it. The module must expose a factory function:

```
createEquipmentPlugin() / createProductPlugin() / createTestPlugin()
```

The factory returns an instance derived from the relevant base class (e.g. `BaseEquipment`, `BaseProduct`, `BaseTest`). The discovery phase:

1. Walks leaf directories.
2. Dynamically imports candidate modules.
3. Registers the module with pluggy `PluginManager` & adds hook specs.
4. Invokes the factory to obtain the runtime instance.

Instances are stored in `PluginService` maps (`equipPlugins`, `productPlugins`, `testPlugins`) keyed by plugin name (case‑insensitive retrieval supported).

### Parameters & Auto‑Generated UI

Each `BasePlugin` holds one or more parameter groups (`BaseParameters`) each containing individual `BaseParameter` objects. The generic shell & GUI layer enumerate groups and expose them to the user automatically. Setting persistence (see Database section) ensures station‑specific values survive restarts.

### Equipment Flexibility

Any controllable resource can be Equipment: physical instruments, sockets, internal services, simulations, or file handlers. There is no assumption of VISA / SCPI. Tests simply declare required Equipment *types*; multiple concrete instances can satisfy a requirement, with current selection policy being “first candidate” (policy can be extended).

### Product Independence

Tests may operate:
* With a Product (e.g. device calibration or verification)
* Without a Product (utility tasks like cable calibration)

Optional association keeps utility & infrastructure tests lightweight.

---

## 3. Requirement Resolution & Execution Flow

When you trigger a Test (via CLI command, plan execution, or programmatically):

1. `Executor.runTest(test, product)` is called (product may be `None`).
2. Test `initialise()` executes (parameter validation, preconditions, etc.).
3. `PluginService.getRequirements(test)` enumerates each declared `requiredEquipment` type:
	 * Builds a candidate list for each type
	 * Marks missing types (fast fail)
	 * Selects one instance (policy: first match) per type
4. Each selected Equipment is initialised if not already online.
5. Equipment instances injected into the Test (`test.provideEquip`).
6. `test.run()` executes; any `TestError` is caught & logged.
7. `test.finalise()` always called.
8. Test `result` (a `BaseTestResult`) is inspected; pass/fail/skip status & log output are reported.

This yields a clear contract:
* If any required Equipment type is missing → abort before test logic.
* Equipment initialisation problems raise immediate failure.
* A test may produce PASS, FAIL, or SKIPPED (others extendable via `ResultStatus`).

---

## 4. Product Discovery (Ethernet)

`EthDiscovery.search(timeout=2)` performs a UDP broadcast to locate NESIE devices. Responses are parsed into dictionaries using known `DEVICE_TYPES` to enrich type info and normalise MAC address formatting. Discovered Products can then be selected (or ignored) before executing tests, enabling quick multi‑device test sessions or selective targeting.

---

## 5. Persistence & Database Model

Cerberus persists plugin parameter groups per Station using a **generic, versioned schema** in MySQL (`GenericDB`). Key attributes:

* Each (station, plugin_type, plugin_name, group_name) is a stable identity.
* Entire parameter groups are stored as deterministic JSON blobs (one row per version) with SHA256 content hashing.
* A pointer table (`current_group_setting`) tracks the active version; identical content skips new row creation (de‑duplication).
* Loading replays persisted values into existing `BaseParameter` objects transparently.
* Historical versions are retained (allowing future diffing / rollback features if desired).

For unit tests and development without MySQL, a file / in‑memory DB conforming to `BaseDB` is used—guaranteeing compatibility with the production persistence layer.

### Automatic Schema Setup

`GenericDB` creates required tables on initialisation; migrations are not currently required due to a normalised, append‑only versioning model.

### Station Scope

Parameter values are namespaced by `station_id`, enabling multiple benches / environments to maintain distinct calibrations or defaults.

---

## 6. Manager Lifecycle

`Manager` coordinates startup and shutdown:

1. Instantiates `PluginService` (discovering all plugins).
2. Loads persisted parameters for every Equipment / Test / Product via DB abstraction.
3. Provides `saveAll()` to persist snapshots (also invoked in `finalize`).
4. Context‑manager semantics allow safe use with `with Manager(...) as m:` ensuring orderly DB closure and final save on exit.

---

## 7. Test Planning

Modules `plan` and `planService` (see code) enable composing sequences of tests (optionally parameterised) and serialising/deserialising plan definitions. This underpins repeatable calibration / verification workflows and future UI plan editors.

---

## 8. Shell & CLI Experience

The CLI (`CerberusCLI.py`) exposes commands to:
* List tests, equipment, products
* Inspect & modify parameter groups
* Run single tests or entire plans
* Discover products over Ethernet

Shell hierarchy allows entering a specific plugin shell to focus operations (e.g. configuring one instrument) while maintaining consistent commands (e.g. `show params`, `set <group>.<param> <value>`). The same metadata powers a GUI layer that auto‑generates input widgets (text fields, numeric sliders, dropdowns, etc.) directly from parameter definitions—no duplicated form code.

---

## 9. Writing a New Plugin (Quick Start)

1. Create a leaf folder under the relevant category, e.g. `Cerberus/plugins/equipment/MyPowerSupply/`.
2. Add a module named `MyPowerSupplyEquipment.py`.
3. Implement `createEquipmentPlugin()` returning a subclass of `BaseEquipment`.
4. Define parameter groups (subclass `BaseParameters` if needed) and add via `addParameterGroup()`.
5. Implement lifecycle methods: `initialise()`, `configure()`, `finalise()`.
6. (Optional) Provide helpful `description` for shell/UI introspection.

The plugin becomes available at next startup—no manual registration.

---

## 10. Unit Tests & Quality

Pytest suites (`tests/unit/`) cover foundational behaviours:
* Plugin discovery & case‑insensitive lookup
* Parameter storage / persistence (`genericDB`, file DB)
* Executor requirement resolution and error paths
* Plan serialisation logic
* Edge cases in parameter group handling & exception stringification

This ensures core extension surfaces (plugins & persistence) remain stable as features evolve.

---

## 11. Extensibility Roadmap (Ideas)

* Pluggable Equipment selection policies (e.g. round‑robin, capability scoring)
* Historical parameter diff / rollback via stored versions
* Test result history persistence & analytics
* GUI plan editor & execution dashboard
* Remote execution (station orchestration) layer
* Rich product discovery adapters (USB, serial, REST, etc.)

---

## 12. Development Environment

Dependencies are listed in `requirements.txt`. Typical workflow (simplified):

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\\Scripts\\activate)
pip install -r requirements.txt
pytest -q
python CerberusCLI.py
```

Configure MySQL connection details in your runtime configuration (see `common.DBInfo` usage) or adapt to a file DB for local experimentation.

---

## 13. Key Design Principles

* **Loose coupling:** Tests depend only on Equipment *types*, not concrete names.
* **Declarative parameters:** Single source of truth drives CLI, GUI, and persistence.
* **Deterministic persistence:** Content hashing prevents redundant DB rows while preserving history.
* **Graceful degradation:** Tests can run without Products; equipment can be absent (explicitly reported early).
* **Discoverability:** Zero manual registration; file structure + suffix naming convention is enough.

---

## 14. Troubleshooting Quick Reference

| Symptom | Possible Cause | Action |
|---------|----------------|--------|
| Plugin missing from shell list | File name/suffix mismatch | Ensure module ends with `Equipment.py` / `Product.py` / `Test.py` and factory exists. |
| Requirements failure before test runs | Equipment type not discovered | Check discovery logs; confirm plugin subclass type matches test `requiredEquipment`. |
| Parameters not loading | Wrong `station_id` or DB connection | Verify station ID passed to `Manager` & DB credentials; inspect logs for load warnings. |
| Duplicate parameter groups | Same `groupName` reused | Adjust group names or accept overwrite (warning emitted). |
| DB rows ballooning | Frequent parameter edits | This is expected; identical content hashes are deduped automatically. |

---

## 15. Contributing

1. Fork & branch (`dev` as integration branch).
2. Add / update tests for new behaviours.
3. Keep plugin file naming consistent; document new parameter groups.
4. Submit PR with concise description & rationale.

---

## 16. License

SmithMyers 2025!

---

Happy testing & calibration – extend Cerberus to fit your lab instead of bending your lab to fit a framework.

