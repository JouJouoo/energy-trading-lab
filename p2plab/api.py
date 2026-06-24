from __future__ import annotations

from typing import Any, Dict

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - optional production dependency
    FastAPI = None
    BaseModel = object

from .agent import P2PLabAgent


if FastAPI is not None:
    app = FastAPI(title="Energy Trading Lab", version="0.1.0")
    agent = P2PLabAgent()

    class LabRequest(BaseModel):
        text: str
        grid_case: str = "ieee33"

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok", "product": "Energy Trading Lab"}

    @app.post("/reproduce")
    def reproduce(request: LabRequest) -> Dict[str, Any]:
        return agent.run_paper_reproduction(request.text, grid_case=request.grid_case)

    @app.post("/theory")
    def theory(request: LabRequest) -> Dict[str, Any]:
        return agent.run_theory_experiment(request.text, grid_case=request.grid_case)
else:
    app = None
