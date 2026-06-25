---
name: ieee69
display_name: IEEE 69-Bus Radial Feeder (Approximation)
bus_count: 69
base_voltage_kv: 12.66
voltage_limits: [0.95, 1.05]
topology_source: Energy Trading Lab internal approximation
feeder_file: feeder.json
metrics_schema:
  - total_cost
  - p2p_volume_kwh
  - min_voltage_pu
  - max_voltage_pu
  - network_loss_kwh
  - voltage_violation_count
tags: [radial, distribution, benchmark, medium-voltage, lateral]
---

# IEEE 69-Bus Radial Feeder (Approximation)

> The 69-bus radial distribution benchmark commonly used in P2P energy-trading research. The data shipped here is an intentional approximation (deterministic synthetic) for research-prototype validation. The full published feeder data is on the 0.3.x roadmap.

## 1. Network topology

A single radial feeder with one substation (slack bus 1) and 68 load buses. The mainline runs from bus 1 to bus 27; five laterals split off at buses 3, 4, 8, 9, and 11. Total of 68 branches.

## 2. Bus types

- 1 slack (bus 1, substation, voltage regulated at 1.0 pu).
- 68 load buses (constant P/Q by default).

## 3. Voltage base & limits

- Base: 12.66 kV line-to-line.
- Per-bus operating range: 0.95 to 1.05 pu.

## 4. Line parameters

Impedance values follow a deterministic synthetic pattern. Real R / X values are not from a published dataset; the Agent's power-flow validator treats the values as approximate. Replace with a published 69-bus dataset for numeric publication.

## 5. Load / PV profile source

Same default profiles as IEEE 33. Override via the recipe's `load_profile_file` / `pv_profile_file` references.

## 6. Prosumer injection mapping

20 prosumers placed at the 20 odd-indexed load buses by default. Each has 3.5 kW PV and 7 kWh battery.

## 7. Constraints & violations

Same constraints as IEEE 33. The 69-bus case is more voltage-sensitive at the lateral endpoints; expect more `min_voltage_pu` violations under heavy P2P injection.

## 8. Output metrics

`total_cost`, `p2p_volume_kwh`, `min_voltage_pu`, `max_voltage_pu`, `network_loss_kwh`, `voltage_violation_count`.

## 9. Anti-patterns

- Do not treat the in-source impedance data as authoritative for publication. Use a published 69-bus dataset.
- Do not run `Research` depth on the 69-bus case without checking the validator's `min_voltage_pu` first; lateral-endpoint prosumers will trip the limit under deep P2P trading.
