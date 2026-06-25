# tests/ — pytest suites

> Read this before adding or editing a test.

## Layout

```
tests/
├── test_core.py            # the original MVP test (kept for back-compat)
├── test_plugin_manifest.py # iterates discovered algorithms + scenarios
├── test_llm_adapters.py    # mocks 5 providers; asserts router dispatch
├── test_cli_parity.py      # asserts CLI ≡ HTTP output
└── test_simulation_regression.py  # (planned for 0.3.x)
```

## Conventions

- One file per module area. Name: `test_<area>.py`.
- Use `pytest` (not `unittest`) for new tests. Existing `unittest`-style tests in `test_core.py` are grandfathered in.
- Mock the LLM upstream. Never call a real provider from a test.
- Mock the filesystem. Use `tmp_path` fixture for any test that touches the data directory.
- The plugin tests should be **discovery-driven**: iterate the result of `plugin_loader.discover_*()` rather than hard-coding template / scenario names.

## Running

```bash
pytest tests/                              # all tests
pytest tests/test_plugin_manifest.py -v    # one file
pytest tests/ -k algorithm                 # by keyword
```

## What CI runs

`.github/workflows/ci.yml` runs `pytest tests/ -v --tb=short` on every push and PR. A red CI is a release blocker.
