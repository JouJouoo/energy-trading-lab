# QUICKSTART — Energy Trading Lab in 5 minutes

This is the one-page setup. It assumes a Unix-like shell (macOS / Linux) and Python 3.9+.

## 1. Clone and enter

```bash
git clone https://github.com/JouJouoo/energy-trading-lab.git
cd energy-trading-lab
```

## 2. Backend — Python virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Start the workspace

```bash
python -m p2plab.cli serve --port 8765
```

Open <http://127.0.0.1:8765>. You should see the Energy Trading Lab workspace. The web UI is served by FastAPI itself; no separate `npm run dev` is required for the bundled frontend.

## 4. Try a paper reproduction

In a second terminal, with the same venv active:

```bash
python -m p2plab.cli reproduce \
  --input examples/sample_paper.md \
  --grid-case ieee33 \
  --experiment-depth quick
```

This runs the same `reproduce` flow that the web UI's "Run Agent" button triggers, but from the CLI. It will print a JSON summary at the end.

## 5. (Optional) Wire an LLM

Without an API key the Agent runs in deterministic fallback mode. To enable real LLM-based paper understanding, export your OpenAI-compatible credentials:

```bash
export ENERGY_LAB_LLM_API_KEY="sk-..."
export ENERGY_LAB_LLM_BASE_URL="https://api.openai.com/v1"   # or DeepSeek / Qwen / Moonshot
export ENERGY_LAB_LLM_MODEL="gpt-4o-mini"
python -m p2plab.cli serve --port 8765
```

See `docs/llm-adapters.md` for the full list of providers and the BYOK priority order.

## 6. (Optional) Desktop shell

If you want a Tauri-packaged desktop app instead of the browser:

```bash
cd web
npm install
npm run tauri:dev
```

This boots the same backend on `127.0.0.1:8765` and opens a desktop window.

## 7. (Optional) Docker

```bash
cd deploy
cp .env.example .env   # fill in API key if you want LLM
mkdir -p data runs     # first time only
docker compose up -d
curl http://127.0.0.1:8765/api/health
```

The Docker image exposes the same FastAPI workspace on `8765` and bind-mounts
`./deploy/data` and `./deploy/runs` so the SQLite metadata and per-run
artifacts survive container restarts. See `deploy/README.md` for the full
operator guide (logs, rebuild, backup, custom plugins).

## What's next

- `docs/architecture.md` — runtime topology, data flow.
- `docs/skills-protocol.md` — add a new algorithm template.
- `docs/scenarios-protocol.md` — add a new grid case.
- `CONTRIBUTING.md` — code style, PR conventions.
- `docs/roadmap.md` — what's coming.
