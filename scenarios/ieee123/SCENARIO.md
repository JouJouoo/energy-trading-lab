---
name: ieee123
display_name: IEEE 123-Bus Test Feeder (Synthetic Subset)
bus_count: 30
base_voltage_kv: 4.16
voltage_limits: [0.95, 1.05]
topology_source: Synthetic 30-bus radial approximation (see docs/roadmap.md 0.3.x for full IEEE 123)
feeder_file: feeder.json
metrics_schema:
  - total_cost
  - p2p_volume_kwh
  - min_voltage_pu
  - max_voltage_pu
  - network_loss_kwh
tags: [radial, distribution, low-voltage, unbalanced-friendly, plugin-demo]
---

# IEEE 123-Bus Test Feeder (Synthetic Subset)

> This scenario is shipped as a **plugin-extension demo**: it shows that the Agent can pick up an arbitrary `scenarios/<name>/` folder without any code change in `p2plab/grid.py`. The full published IEEE 123-bus unbalanced test feeder is on the 0.3.x roadmap; this folder will be replaced in place by a full-feeder scenario at that point.

## 1. Network topology

A synthetic 30-bus radial feeder. 1 slack (bus 1) and 29 load buses. 4 laterals split off at buses 3, 6, 11, and 18. Total of 29 branches.

## 2. Bus types

- 1 slack (bus 1, substation, voltage regulated at 1.0 pu).
- 29 load buses (constant P/Q by default; the lower 4.16 kV base is appropriate for North American residential feeders).

## 3. Voltage base & limits

- Base: 4.16 kV line-to-line.
- Per-bus operating range: 0.95 to 1.05 pu.

## 4. Line parameters

Impedance values are derived from a deterministic synthetic pattern. Replace with the published IEEE 123 data for numeric publication.

## 5. Load / PV profile source

Same default profiles as the other scenarios. The Agent reads `examples/profiles/` when shipped.

## 6. Prosumer injection mapping

8 prosumers placed at buses 4, 7, 12, 15, 19, 22, 25, 28. Each has 5 kW PV and 10 kWh battery.

## 7. Constraints & violations

Same constraints as the other scenarios. The 4.16 kV base makes the network more voltage-sensitive at the lateral endpoints.

## 8. Output metrics

`total_cost`, `p2p_volume_kwh`, `min_voltage_pu`, `max_voltage_pu`, `network_loss_kwh`.

## 9. Anti-patterns

- Do not use the impedance values in `feeder.json` for publication. Use a published 123-bus dataset.
- Do not place prosumers at the slack bus; the reverse-flow assumption breaks.
- The 4.16 kV base is intentional — a 12.66 kV injection will exceed the per-bus voltage range.
