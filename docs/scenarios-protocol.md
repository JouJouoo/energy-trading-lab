# Scenarios protocol — Simulation scenario manifest spec

> **Version**: 0.2.0
> **Status**: Stable. New scenarios must follow this spec.

A **scenario** is a folder under `scenarios/<grid>/` that ships the static description of one distribution network plus the default load / PV / prosumer profiles that the Agent uses when the user selects that grid case.

This is the analogue of open-design's [`design-systems/<brand>/DESIGN.md` convention](https://github.com/nexu-io/open-design/blob/main/CONTRIBUTING.md#adding-a-new-design-system) — a 9-section Markdown contract next to a JSON data file.

## 1. Folder layout

```
scenarios/<grid>/
├── SCENARIO.md             # required, this spec's 9-section manifest
├── feeder.json             # required, bus / line / load data
├── prosumer_layout.json    # optional, default prosumer placement
└── profiles/
    ├── load_24h.json       # optional, 24-hour default load profile
    └── pv_24h.json         # optional, 24-hour default PV profile
```

`<grid>` ∈ snake_case: `ieee33`, `ieee69`, `ieee123`, `custom_feeder_a`, etc. The name is what the user types into `--grid-case`.

## 2. `SCENARIO.md` shape

`SCENARIO.md` is Markdown with a YAML frontmatter block + a 9-section body. The frontmatter is the machine-consumed part; the body documents the scenario for humans.

### 2.1 Frontmatter (machine-consumed)

```yaml
---
name: ieee33                          # required, snake_case, must match <grid>
display_name: IEEE 33-Bus Test Feeder # required, shown in UI / CLI listings
bus_count: 33                         # required, integer
base_voltage_kv: 12.66                # required, line-to-line kV
voltage_limits: [0.95, 1.05]          # required, [min_pu, max_pu]
topology_source: Baran-Wu 1989        # required, citation
feeder_file: feeder.json              # required, must exist next to this file
prosumer_layout_file: prosumer_layout.json  # optional
load_profile_file: profiles/load_24h.json    # optional
pv_profile_file: profiles/pv_24h.json        # optional
metrics_schema:                       # optional, list of metric keys
  - total_cost
  - p2p_volume_kwh
  - min_voltage_pu
  - network_loss_kwh
  - voltage_violation_count
tags: [radial, distribution, benchmark]   # optional, free-form
---
```

### 2.2 Body (human-consumed, 9 sections)

The body must contain exactly these nine H2 sections, in order:

1. **Network topology** — feeder type, slack bus, radial / meshed, total length.
2. **Bus types** — how many load buses, how many generator buses, how many switch buses.
3. **Voltage base & limits** — the `base_voltage_kv`, the per-bus operating range, any special zones (e.g. voltage regulators).
4. **Line parameters** — typical R / X / B values, conductor type, thermal limits.
5. **Load / PV profile source** — synthetic or measured, peak / off-peak ratios, time resolution.
6. **Prosumer injection mapping** — how prosumers are placed across the feeder, the default count, the default PV / storage sizing.
7. **Constraints & violations** — voltage limit, line loading limit, what the Agent counts as a violation.
8. **Output metrics** — which metrics the Agent reports for this scenario.
9. **Anti-patterns** — what *not* to do with this scenario (e.g. "do not place prosumers at the slack bus").

Empty section bodies are fine for hard-to-find data, but the headings must be there.

## 3. `feeder.json` shape

`feeder.json` is a JSON document with the following top-level keys:

```json
{
  "name": "ieee33",
  "base_voltage_kv": 12.66,
  "base_mva": 10.0,
  "frequency_hz": 60,
  "slack_bus": 0,
  "buses": [
    {"id": 0, "type": "slack", "voltage_pu": 1.0},
    {"id": 1, "type": "load", "load_kw": 100.0, "load_kvar": 60.0},
    ...
  ],
  "lines": [
    {"from": 0, "to": 1, "r_pu": 0.0572, "x_pu": 0.0297, "limit_a": 400},
    ...
  ],
  "transformers": []
}
```

All values are in per-unit unless suffixed with `_kw`, `_kvar`, `_a`, `_hz`. The Agent's `SimplePowerFlowValidator` is the consumer.

## 4. `prosumer_layout.json` shape (optional)

```json
{
  "default_prosumer_count": 12,
  "placement": "deterministic_evenly_spaced",
  "by_bus": {
    "3": {"pv_kw": 4.0, "battery_kwh": 8.0},
    "7": {"pv_kw": 3.0, "battery_kwh": 6.0}
  }
}
```

When `prosumer_layout.json` is present, the Agent uses it; otherwise it falls back to even spacing across the load buses.

## 5. Discovery

`p2plab/plugin_loader.discover_scenarios(roots)` is the function the Agent uses at startup to enumerate scenarios. It scans:

- `scenarios/` (the canonical built-in root).
- `$ENERGY_LAB_DATA_DIR/scenarios/` (user-installed scenarios).
- `~/.energy_trading_lab/scenarios/` (user-global scenarios).

The merge order is **user-global > user-data > built-in**: a user-installed scenario with the same `<name>` overrides the built-in.

The discovery result is exposed via:

- CLI: `python -m p2plab.cli plugins-scenarios`
- HTTP: `GET /api/plugins/scenarios`
- Web UI: `http://127.0.0.1:8765/plugins`

## 6. Validation

`tests/test_plugin_manifest.py` (shared with the algorithm template validation) iterates every discovered scenario and asserts:

1. `SCENARIO.md` frontmatter parses as YAML.
2. Required keys (`name`, `display_name`, `bus_count`, `base_voltage_kv`, `voltage_limits`, `topology_source`, `feeder_file`) are present.
3. `feeder.json` parses and the `buses` / `lines` lists are non-empty.
4. The 9 body sections (Network topology, …, Anti-patterns) are present in the body.

A failing assertion is treated as a build break.

## 7. Backward compatibility

The historical `IEEE33_FEEDER` / `IEEE69_FEEDER` constants inside `p2plab/grid.py` remain as the fallback when no scenarios are installed. They will be removed in 0.3.0 once the built-in `scenarios/ieee33/` and `scenarios/ieee69/` ship as the canonical data.

## 8. Bar for merging a new scenario

1. The folder follows §1's layout.
2. `SCENARIO.md` passes `tests/test_plugin_manifest.py`.
3. `feeder.json` parses; the Agent's `SimplePowerFlowValidator` accepts it.
4. The 9 body sections are present.
5. The merge request is labeled `plugin:scenario`.
6. The author adds a row to the scenarios table in `docs/spec.md` §8.
