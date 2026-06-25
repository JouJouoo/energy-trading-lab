# References

A curated reading list for the domains Energy Trading Lab touches. The list is not exhaustive; it is what a new contributor should skim in their first week to get the vocabulary right.

## P2P energy trading — foundations

- Sousa, T. et al. (2019). *Peer-to-peer and community-based markets: A comprehensive review*. Renewable and Sustainable Energy Reviews, 104, 367-378. — The canonical review.
- Mengelkamp, E. et al. (2018). *Designing microgrid energy markets — A case study: The Brooklyn Microgrid*. Applied Energy, 210, 870-880. — Real deployment, useful as a reference architecture.
- Morstyn, T. et al. (2018). *Using peer-to-peer energy-trading platforms to incentivise prosumers to form federated power plants*. Nature Energy, 3, 94-101. — The federated-PV framing.

## Market mechanisms

- Vickrey, W. (1961). *Counterspeculation, Auctions, and Competitive Sealed Tenders*. The Journal of Finance, 16(1), 8-37. — The second-price auction reference.
- Vickrey, W. (1961). *Reply to "Counterspeculation, Auctions, and Competitive Sealed Tenders"*. The Journal of Finance, 16(1), 47-50. — The clarifying follow-up.
- Baran, M. E., Wu, F. F. (1989). *Network reconfiguration in distribution systems for loss reduction and load balancing*. IEEE Transactions on Power Delivery, 4(2), 1401-1407. — The IEEE 33 / 69 test feeder reference.

## Multi-agent reinforcement learning for trading

- Lütge, C. et al. (2021). *A perspective on multi-agent reinforcement learning for emerging power systems*. Electric Power Systems Research, 199, 107430.
- Wei, H. et al. (2021). *Multi-agent reinforcement learning for distributed energy trading in distribution networks*. Applied Energy, 295, 116985. — The "MARL for P2P" paper most relevant to the default `RL/MARL` template.

## Stackelberg / game-theoretic pricing

- Maharjan, S. et al. (2013). *Dependable Demand Response Management in the Smart Grid: A Stackelberg Game Approach*. IEEE Transactions on Smart Grid, 4(1), 120-132.
- Yu, M., Hong, S. H. (2016). *A real-time demand-response trading system for the smart grid*. Applied Energy, 178, 843-855.

## Distribution network power flow

- Baran, M. E., Wu, F. F. (1989). *Optimal sizing of capacitors placed on a radial distribution system*. IEEE Transactions on Power Delivery, 4(1), 735-743.
- Kersting, W. H. (2012). *Distribution System Modeling and Analysis* (3rd ed.). CRC Press. — The textbook for radial-feeder modeling.

## Tooling

- FastAPI: <https://fastapi.tiangolo.com/>
- Uvicorn: <https://www.uvicorn.org/>
- Vue 3: <https://vuejs.org/>
- Vite: <https://vitejs.dev/>
- Tauri: <https://tauri.app/>
- Chart.js: <https://www.chartjs.org/>
- marked: <https://marked.js.org/>
- Pandapower (optional future dependency): <https://www.pandapower.org/>

## Inspiration

- [nexu-io/open-design](https://github.com/nexu-io/open-design) — the engineering conventions for the documentation matrix, plugin surfaces, and dual-track capability exposure were modeled on this project. See `AGENTS.md` for the link mapping.
- [openai/openai-python](https://github.com/openai/openai-python) — the SDK whose adapter pattern `p2plab/llm_adapters/` echoes (without depending on the SDK itself).

## How to add a reference

Open a PR with the new entry. Format: citation first, then a one-line "why it's relevant to Energy Trading Lab" note. Self-citations from the maintainer are allowed; they go under a separate sub-heading.
