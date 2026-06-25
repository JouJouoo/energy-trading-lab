---
name: ieee33
display_name: IEEE 33-Bus Test Feeder
bus_count: 33
base_voltage_kv: 12.66
voltage_limits: [0.95, 1.05]
topology_source: Baran-Wu 1989
feeder_file: feeder.json
metrics_schema:
  - total_cost
  - p2p_volume_kwh
  - min_voltage_pu
  - max_voltage_pu
  - network_loss_kwh
  - voltage_violation_count
  - self_consumption_ratio
tags: [radial, distribution, benchmark, low-voltage]
---

# IEEE 33-Bus Test Feeder

> The 33-bus radial distribution benchmark from Baran & Wu (1989). The data shipped here is the common "case33bw" approximation used across the P2P energy-trading research literature.

## 1. Network topology

A single radial feeder with one substation (slack bus 1) and 32 load buses. The mainline runs from bus 1 to bus 18; laterals split off at buses 2, 3, and 6. Total of 32 branches, all overhead line.

## 2. Bus types

- 1 slack (bus 1, substation, voltage regulated at 1.0 pu).
- 32 load buses (constant P/Q by default; the Agent scales them by 0.12 to set the operating point in the validation pass).

## 3. Voltage base & limits

- Base: 12.66 kV line-to-line.
- Per-bus operating range: 0.95 to 1.05 pu.
- No on-feeder voltage regulators; only the substation transformer tap.

## 4. Line parameters

Impedance values are the standard Baran-Wu per-unit figures (on a 100 MVA / 12.66 kV base). `r_ohm` / `x_ohm` in the JSON mirror the same ratios. No thermal limit is enforced by the validator.

## 5. Load / PV profile source

By default the load profile is a 24-hour residential curve with morning and evening peaks; PV is a 6:00–18:00 bell. The Agent can override with the `examples/profiles/` 30-day series when one is shipped (see `docs/roadmap.md` 0.5.x).

## 6. Prosumer injection mapping

12 prosumers placed at the 12 even-indexed load buses by default. Each has 4 kW PV and 8 kWh battery. The Agent's `candidate_prosumer_buses(grid, count)` helper is the deterministic placer.

## 7. Constraints & violations

- Voltage magnitude outside [0.95, 1.05] pu at any bus.
- Network loss as a fraction of total demand above 8%.
- Reverse power flow at the substation bus (not yet enforced).

## 8. Output metrics

`total_cost`, `p2p_volume_kwh`, `min_voltage_pu`, `max_voltage_pu`, `network_loss_kwh`, `voltage_violation_count`, `self_consumption_ratio`.

## 9. Anti-patterns

- Do not place prosumers at bus 1 (slack). The reverse-flow assumption breaks.
- Do not zero out all loads when validating power flow — the validator emits nonsense voltages.
- Do not rely on the in-source data for numeric publication; the canonical `pandapower.case33bw()` is the gold standard.
