FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, scenarios, and entry points.
COPY p2plab ./p2plab
COPY scenarios ./scenarios
COPY pyproject.toml ./
COPY start_backend.py ./

# Container-internal data root. The compose file bind-mounts ./data and
# ./runs onto these two paths so the SQLite + run artifacts survive
# container restarts.
ENV ENERGY_LAB_DATA_DIR=/app/data \
    ENERGY_LAB_RUN_ROOT=/app/runs

EXPOSE 8765

# Default entrypoint: serve the FastAPI workspace on all interfaces.
CMD ["python", "-m", "p2plab.cli", "serve", "--host", "0.0.0.0", "--port", "8765"]
