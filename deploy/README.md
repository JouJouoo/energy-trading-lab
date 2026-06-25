# deploy/ — Docker Compose deployment

Energy Trading Lab can be deployed as a single Docker container running the
FastAPI workspace. This is one of three supported deployment topologies
(see `docs/architecture.md`); the other two are local venv and Tauri desktop.

## Layout

```
deploy/
├── AGENTS.md            # conventions for editing this folder
├── docker-compose.yml   # one service: energy-trading-lab-backend
├── Dockerfile           # python:3.11-slim + requirements.txt
├── .env.example         # ENERGY_LAB_PORT, ENERGY_LAB_LLM_*
├── README.md            # this file
├── data/                # bind mount: SQLite + workspace metadata
└── runs/                # bind mount: per-experiment artifacts
```

The image exposes port `8765` and writes nothing to its own filesystem
that isn't also mirrored to the host via the two bind mounts. The
container does not run the Tauri desktop shell — that target is separate.

## Quick start

```bash
cd deploy
cp .env.example .env       # edit ENERGY_LAB_LLM_API_KEY if you have one
mkdir -p data runs         # first time only; created on `up` if missing
docker compose up -d       # start the backend
docker compose ps          # confirm `healthy`
docker compose logs -f     # follow logs (Ctrl-C to detach)
curl http://127.0.0.1:8765/api/health   # → {"status":"ok"}
docker compose down        # stop
```

Open `http://127.0.0.1:8765` in a browser to use the web workspace, or use
the CLI on the host:

```bash
python3 -m p2plab.cli workspace-list --json
python3 -m p2plab.cli plugins-algorithms --json
```

## Data persistence

The two bind mounts are what makes the deployment survive restarts:

| Container path | Host path (relative to `deploy/`) | What it holds |
|---|---|---|
| `/app/data`     | `./data`     | SQLite metadata (`db.sqlite`), per-run summaries |
| `/app/runs`     | `./runs`     | Per-experiment artifacts: model_spec, metrics, code_project, etc. |

If you point both paths at an existing local checkout, the container will
pick up your previous runs (the workspace UI will list them on the home
page). If you start with empty directories, the container initializes a
fresh SQLite on first boot.

To back up: `tar czf etl-data.tgz deploy/data deploy/runs`. To restore:
extract the same archive back into `deploy/`.

## Operating

```bash
# Tail logs
docker compose logs -f

# List running services
docker compose ps

# Execute a CLI subcommand inside the container
docker compose exec energy-trading-lab-backend \
  python -m p2plab.cli plugins-algorithms --json

# Rebuild the image (after pulling new source)
docker compose build --no-cache

# Pull a new release and restart
docker compose pull
docker compose up -d
```

## Configuration

All knobs live in `deploy/.env`. The compose file forwards them into the
container's environment.

- `ENERGY_LAB_PORT` — host port mapped to the container's `8765`
- `ENERGY_LAB_LLM_PROVIDER` — `openai` | `deepseek` | `qwen` | `moonshot` | `custom`
- `ENERGY_LAB_LLM_API_KEY` — BYOK; leave blank for the deterministic fallback
- `ENERGY_LAB_LLM_BASE_URL` — override the provider's default base URL
- `ENERGY_LAB_LLM_MODEL` — model name (provider-specific)

If `ENERGY_LAB_LLM_API_KEY` is empty, the LLM stage of the pipeline falls
back to the built-in heuristic extractor. The pipeline still runs end-to-end
in that mode — see `docs/spec.md` §"Local-first" for the design rationale.

## What this deployment does NOT do

- It does not run the Tauri desktop shell.
- It does not auto-update. The image is rebuilt and redeployed on every release.
- It does not include LLM provider SDKs. The image only ships the OpenAI-compatible
  HTTP client; the upstream provider is reached at runtime.
- It does not collect telemetry. Everything stays in the bind-mounted
  `./data` and `./runs` directories on the host.

## Troubleshooting

- **Container exits immediately with "address already in use"**: another
  process is bound to host port 8765. Change `ENERGY_LAB_PORT` in
  `deploy/.env` and re-run `docker compose up -d`.
- **`curl /api/health` returns connection refused**: the container is still
  booting. The healthcheck uses a 20 s `start_period`. Run
  `docker compose logs -f energy-trading-lab-backend` to see startup.
- **Plugin discovery is empty inside the container**: the image only ships
  the built-in algorithm templates and scenarios. To add your own, mount
  them at `/root/.energy_trading_lab/<surface>/` (user-global root) — see
  `docs/skills-protocol.md`.
