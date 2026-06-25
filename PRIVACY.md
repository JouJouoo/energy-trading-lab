# Privacy

Energy Trading Lab is **local-first**. It does not phone home. There is no telemetry, no analytics, no usage beacon, no account.

## What stays on your machine

- All experiment artifacts (`runs/<run_id>/`, `data/runs/<run_id>/`).
- The workspace database (`data/db.sqlite`).
- Your LLM API keys (env vars, request bodies, or `data/db.sqlite` settings).
- Caches and intermediate state under `data/cache/`.

## What leaves your machine

The only outbound network calls are the ones you explicitly configure:

1. **LLM calls** to the provider you point at via `ENERGY_LAB_LLM_BASE_URL` (default `https://api.openai.com/v1`). These calls send the system + user prompts you composed; they do not send any local file system state beyond what your prompt references.
2. **Document upload**: the `POST /api/upload` endpoint processes the file locally; nothing is uploaded to a third party. The parsed text lives in your local SQLite + runs.

## What we never see

The core team has no central server. There is no centralized error reporting, no remote log aggregation, no version check, and no auto-update channel. Your fork is your fork.

## LLM prompts and logs

- `agent_trace.json` and `execution_log_attempt_*.txt` are written to your local `runs/<run_id>/`. They contain the prompts, the LLM responses (when LLM is used), and the experiment logs.
- These files are not transmitted anywhere unless you choose to share them.

## Responsible disclosure

If you find a security issue (e.g. a way to make the agent exfiltrate data, or a path traversal in the workspace APIs), open a private issue or email the maintainer directly. We will respond within a week.

## Compliance note

The project is research software, not a product. Do not feed it personal data you wouldn't otherwise put in a research notebook.
