# deploy/ — Docker Compose deployment

> Read this before editing `deploy/docker-compose.yml` or `deploy/Dockerfile`.

## Layout

```
deploy/
├── docker-compose.yml     # one service: energy-trading-lab-backend
├── Dockerfile             # python:3.11-slim + requirements.txt
├── .env.example           # ENERGY_LAB_PORT, ENERGY_LAB_LLM_API_KEY
└── README.md              # up / down / logs / upgrade commands
```

## Conventions

- The image is `python:3.11-slim`. Do not switch to `python:3.11` (saves ~800MB).
- The image installs `requirements.txt` only. Do not add system packages beyond what `pypdf` and `pandas` need.
- The container exposes 8765. Override with `ENERGY_LAB_PORT` in `deploy/.env`.
- Two volume mounts: `./data:/app/data` and `./runs:/app/runs`. The `data` volume holds the SQLite and the new `data/runs/` artifacts; the `runs` volume is the legacy mount kept for back-compat.
- The container's working directory is `/app`. The entrypoint is `python -m p2plab.cli serve --host 0.0.0.0 --port 8765`.
- Logs go to stdout. Use `docker compose logs -f` to follow.

## Local development

```bash
cd deploy
cp .env.example .env       # edit if you have an LLM key
docker compose up -d       # start
curl http://127.0.0.1:8765/api/health
docker compose logs -f
docker compose down
```

## What this image does NOT do

- It does not run a Tauri shell. The desktop app is a separate target.
- It does not auto-update. The image is rebuilt and redeployed on every release; see `docs/roadmap.md` 0.4.x.
- It does not include the LLM SDKs. The image only ships the OpenAI-compatible HTTP client; the upstream provider is reached at runtime.
