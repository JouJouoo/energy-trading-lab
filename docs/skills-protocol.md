# Skills protocol — Algorithm template manifest spec

> **Version**: 0.2.0
> **Status**: Stable. New templates must follow this spec; existing templates will be migrated on a rolling basis.

An **algorithm template** is a folder under `p2plab/algorithm_templates/<family>/<name>/` that ships the implementation of one algorithm (RL, Optimization, Auction, Game Theory, Rule-based) plus a `TEMPLATE.md` manifest that the Agent consults to plan and validate experiments.

This is the analogue of open-design's [`SKILL.md` convention](https://github.com/nexu-io/open-design/blob/main/docs/skills-protocol.md) — the same pattern, applied to a different domain.

## 1. Folder layout

```
p2plab/algorithm_templates/<family>/<name>/
├── TEMPLATE.md          # required, this spec's manifest
├── <name>.py            # required, the implementation
└── tests/
    └── <name>_smoke.py  # optional, pytest-discoverable smoke test
```

`<family>` ∈ {`Base`, `RL`, `RL/MARL`, `Optimization`, `Auction`, `GameTheory`, `RuleBased`}. The family is what the `algorithm_family` field in `DetailedInnovationSpec` keys off.

## 2. `TEMPLATE.md` shape

`TEMPLATE.md` is Markdown with a YAML frontmatter block. The frontmatter is the machine-consumed part; the body is for humans.

### 2.1 Frontmatter (machine-consumed)

```yaml
---
name: q_learning                  # required, snake_case, must match <name>
family: RL                        # required, one of the families above
display_name: Q-Learning Bidding  # required, shown in UI / CLI listings
file_name: q_learning.py          # required, must exist next to this file
description: |
  Lightweight tabular Q-learning agent for P2P energy bidding.
  State: net demand, time-of-use price, battery SOC.
  Action: buy/sell/hold × quantity bin × price bin.
affected_modules: [reward.py, agent.py]  # optional, hint for the Agent
inputs:                                       # optional, typed input schema
  net_demand: float
  tou_price: float
  battery_soc: float
parameters:                                   # optional, default hyperparameters
  epsilon: 0.18
  learning_rate: 0.1
  discount: 0.95
validation:                                   # optional, validation hints
  smoke_test: tests/q_learning_smoke.py
  min_episodes: 50
tags: [rl, tabular, baseline]                 # optional, free-form
---
```

### 2.2 Body (human-consumed)

A short Markdown document covering, at minimum:

1. **When to use this template** — one paragraph.
2. **Inputs** — the observation the agent expects.
3. **Outputs** — the action the agent emits.
4. **Reward / objective** — the optimization signal.
5. **Hyperparameters** — defaults and tuning notes.
6. **References** — paper, textbook, blog post.

The body is what a new contributor reads to decide whether to use this template.

## 3. Implementation contract

`<name>.py` must expose **one** of the following entry points, depending on the family:

### 3.1 `Base` family (always loaded)

```python
def build_<name>(recipe: ExperimentRecipe) -> Callable[[MarketState], Action]:
    """Return a step function the simulator will call each hour."""
    ...
```

### 3.2 `RL` / `RL/MARL` family

```python
def train_<name>(recipe: ExperimentRecipe, *, progress_callback=None) -> RLPolicy:
    """Train a policy; stream ETL_PROGRESS events via progress_callback."""
    ...

def act_<name>(policy: RLPolicy, state: MarketState) -> Action:
    """Apply a trained policy at inference time."""
    ...
```

### 3.3 `Optimization` family

```python
def solve_<name>(recipe: ExperimentRecipe, market: MarketState) -> ClearingResult:
    """Solve the clearing problem for one step; deterministic, fast."""
    ...
```

### 3.4 `Auction` family

```python
def match_<name>(recipe: ExperimentRecipe, bids: List[Bid], asks: List[Ask]) -> Trades:
    """Match bids and asks into a list of trades."""
    ...
```

### 3.5 `Game Theory` family

```python
def equilibrium_<name>(recipe: ExperimentRecipe, players: List[Player]) -> Equilibrium:
    """Compute an equilibrium or run a price-formation loop."""
    ...
```

### 3.6 `RuleBased` family

```python
def decide_<name>(recipe: ExperimentRecipe, state: MarketState) -> Action:
    """Decide one action from the current state, no training."""
    ...
```

The `progress_callback` parameter, when present, must accept a `dict` payload and must emit `ETL_PROGRESS` events (the Agent's progress protocol — see `p2plab/executor.py`). The protocol is line-prefixed JSON written to stdout; the Agent's `CodeGenerator` handles the wrapping when the template is used in a generated experiment script.

## 4. Discovery

`p2plab/plugin_loader.discover_algorithm_templates(roots)` is the function the Agent uses at startup to enumerate templates. It scans:

- `p2plab/algorithm_templates/` (the canonical built-in root).
- `$ENERGY_LAB_DATA_DIR/algorithm_templates/` (user-installed templates).
- `~/.energy_trading_lab/algorithm_templates/` (user-global templates).

The merge order is **user-global > user-data > built-in**: a user-installed template with the same `<name>` overrides the built-in.

The discovery result is exposed via:

- CLI: `python -m p2plab.cli plugins-algorithms`
- HTTP: `GET /api/plugins/algorithms`
- Web UI: `http://127.0.0.1:8765/plugins`

## 5. Validation

`tests/test_plugin_manifest.py` ships with the project. It:

1. Iterates every discovered template.
2. Asserts the `TEMPLATE.md` frontmatter parses as YAML.
3. Asserts the required keys (`name`, `family`, `display_name`, `file_name`, `description`) are present.
4. Asserts `<name>.py` exists next to the manifest.
5. Asserts the family is one of the allowed set.
6. Asserts the entry-point symbol (`build_*` / `train_*` / `act_*` / `solve_*` / `match_*` / `equilibrium_*` / `decide_*`) exists in the module.

A failing assertion is treated as a build break; CI fails the PR.

## 6. Bar for merging a new template

1. The folder follows §1's layout.
2. `TEMPLATE.md` passes `tests/test_plugin_manifest.py`.
3. The implementation passes its own `tests/<name>_smoke.py` (or the project-level smoke test in `tests/test_core.py`).
4. The body documents at minimum sections 1, 2, 3, 4 from §2.2.
5. The merge request is labeled `plugin:algorithm`.
6. The author adds a row to the templates table in `docs/spec.md` §8.

## 7. Why Markdown, not JSON / YAML

`TEMPLATE.md` is Markdown because the body is documentation, not config. The frontmatter is YAML because it composes naturally with the Markdown body and is well-supported. A pure JSON file would lose the prose; a pure Markdown file would lose the machine-readable structure.
