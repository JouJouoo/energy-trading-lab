from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pathlib import Path

from ..agent import P2PLabAgent
from ..document_loader import extract_document_from_base64, DocumentExtractionError
from ..llm import llm_status, sanitize_llm_config
from .workspace import WorkspaceManager
from .logging import setup_logging, log_api_request, log_error, log_job_event

logger = setup_logging()

app = FastAPI(
    title="Energy Trading Lab API",
    description="面向能源交易的科研仿真实验智能体 API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    log_api_request(str(request.url), request.method, response.status_code, duration_ms)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error(exc, {"endpoint": str(request.url), "method": request.method})
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

AGENT = None
RUN_ROOT = "runs"
JOBS: Dict[str, Dict[str, Any]] = {}
WORKSPACE = None

def get_workspace() -> WorkspaceManager:
    global WORKSPACE
    if WORKSPACE is None:
        WORKSPACE = WorkspaceManager(run_root=RUN_ROOT)
    return WORKSPACE

class LLMConfig(BaseModel):
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    timeout_sec: int = 30
    temperature: float = 0.1
    max_tokens: int = 2500
    disabled: bool = False

class JobRequest(BaseModel):
    mode: str = Field(..., description="工作流模式: reproduce 或 theory")
    text: str = Field(..., description="论文文本或理论草稿")
    grid_case: str = Field(default="ieee33", description="电网案例: ieee33 或 ieee69")
    experiment_depth: str = Field(default="quick", description="实验深度: quick/research/deep")
    llm_config: Optional[LLMConfig] = None

class ExtractDocumentRequest(BaseModel):
    filename: str
    mime_type: str = ""
    data_base64: str

class JobStatus(BaseModel):
    job_id: str
    mode: str
    grid_case: str
    experiment_depth: str
    status: str
    current_step: str
    current_summary: str
    events: List[Dict[str, Any]]
    result: Optional[Dict[str, Any]] = None
    error: str = ""
    created_at: float
    updated_at: float

def get_agent() -> P2PLabAgent:
    global AGENT
    if AGENT is None:
        AGENT = P2PLabAgent(run_root=RUN_ROOT)
    return AGENT

@app.get("/api/health", tags=["系统"])
async def health_check():
    return {"status": "ok", "product": "Energy Trading Lab", "version": "0.1.0"}

@app.get("/api/llm-status", tags=["LLM"])
async def get_llm_status():
    return llm_status()

@app.get("/api/runs", tags=["运行记录"])
async def list_runs(limit: int = 30):
    agent = get_agent()
    return {"memory": agent.memory.recent(limit=limit)}

@app.get("/api/workspace/projects", tags=["工作空间"])
async def list_projects():
    workspace = get_workspace()
    projects = workspace.list_projects()
    return {"projects": projects, "count": len(projects)}

@app.get("/api/workspace/projects/{run_id}", tags=["工作空间"])
async def get_project(run_id: str):
    workspace = get_workspace()
    project = workspace.get_project(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.delete("/api/workspace/projects/{run_id}", tags=["工作空间"])
async def delete_project(run_id: str):
    workspace = get_workspace()
    success = workspace.delete_project(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "run_id": run_id}

@app.get("/api/workspace/projects/{run_id}/metrics", tags=["工作空间"])
async def get_project_metrics(run_id: str):
    workspace = get_workspace()
    metrics = workspace.get_project_metrics(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return {"metrics": metrics}

@app.get("/api/workspace/projects/{run_id}/trace", tags=["工作空间"])
async def get_project_trace(run_id: str):
    workspace = get_workspace()
    trace = workspace.get_project_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"trace": trace}

@app.get("/api/workspace/projects/{run_id}/report", tags=["工作空间"])
async def get_project_report(run_id: str):
    workspace = get_workspace()
    report = workspace.get_project_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}

@app.get("/api/workspace/projects/{run_id}/artifact/{artifact_name}", tags=["工作空间"])
async def get_project_artifact(run_id: str, artifact_name: str):
    workspace = get_workspace()
    content = workspace.get_project_artifact(run_id, artifact_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"artifact_name": artifact_name, "content": content}

@app.post("/api/extract-document", tags=["文档处理"])
async def extract_document(request: ExtractDocumentRequest):
    try:
        result = extract_document_from_base64(
            filename=request.filename,
            data_base64=request.data_base64,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".rst", ".tex", ".csv"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB

@app.post("/api/upload", tags=["文档管理"])
async def upload_document(file: UploadFile = File(...)):
    """
    上传论文文件（PDF/TXT/Markdown），提取文本内容供 Agent 使用
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。支持的类型: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
        )
    
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {MAX_UPLOAD_BYTES // 1024 // 1024}MB"
        )
    
    import base64
    data_base64 = base64.b64encode(content).decode("ascii")
    
    try:
        result = extract_document_from_base64(file.filename, data_base64)
        return {
            "success": True,
            "filename": result["filename"],
            "chars": result["chars"],
            "method": result["method"],
            "text": result["text"],
        }
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"文件上传失败: {exc}")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(exc)}")

@app.post("/api/jobs", tags=["任务管理"], response_model=JobStatus)
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex[:12]
    llm_config = request.llm_config.dict() if request.llm_config else {}
    
    job = {
        "job_id": job_id,
        "mode": request.mode,
        "grid_case": request.grid_case,
        "experiment_depth": request.experiment_depth,
        "status": "queued",
        "current_step": "queued",
        "current_summary": "Waiting for the Agent worker.",
        "events": [],
        "result": None,
        "error": "",
        "created_at": time.time(),
        "updated_at": time.time(),
        "_text": request.text,
        "_llm_config": llm_config,
    }
    JOBS[job_id] = job
    
    background_tasks.add_task(run_job_background, job_id)
    
    return job

@app.get("/api/jobs/{job_id}", tags=["任务管理"], response_model=JobStatus)
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    safe_job = {k: v for k, v in job.items() if not k.startswith("_")}
    return safe_job

@app.post("/api/reproduce", tags=["工作流"])
async def run_reproduce(request: JobRequest):
    llm_config = request.llm_config.dict() if request.llm_config else {}
    agent = get_agent()
    
    try:
        result = agent.run_paper_reproduction(
            request.text,
            grid_case=request.grid_case,
            llm_config=llm_config,
            experiment_depth=request.experiment_depth,
        )
        return summarize_result(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/theory", tags=["工作流"])
async def run_theory(request: JobRequest):
    llm_config = request.llm_config.dict() if request.llm_config else {}
    agent = get_agent()
    
    try:
        result = agent.run_theory_experiment(
            request.text,
            grid_case=request.grid_case,
            llm_config=llm_config,
            experiment_depth=request.experiment_depth,
        )
        return summarize_result(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/paper2code", tags=["工作流"])
async def run_paper2code(request: JobRequest, output_dir: Optional[str] = None):
    llm_config = request.llm_config.dict() if request.llm_config else {}
    agent = get_agent()
    
    try:
        result = agent.run_paper_to_code(
            request.text,
            grid_case=request.grid_case,
            llm_config=llm_config,
            output_dir=output_dir,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

async def run_job_background(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return
    
    agent = P2PLabAgent(run_root=RUN_ROOT)
    append_job_event(job_id, {
        "step": "start_job",
        "status": "ok",
        "summary": f"Started {job['mode']} workflow on {job['grid_case']}.",
        "details": {},
    }, status="running")

    def on_event(event: Dict[str, Any]) -> None:
        append_job_event(job_id, event, status="running")
        if event.get("step") == "training_progress":
            asyncio.sleep(0.02)
        elif event.get("step") in ("strategy_start", "strategy_done"):
            asyncio.sleep(0.05)
        else:
            asyncio.sleep(0.16)

    try:
        text = job["_text"]
        llm_config = job["_llm_config"]
        if job["mode"] == "theory":
            result = agent.run_theory_experiment(
                text,
                grid_case=job["grid_case"],
                on_event=on_event,
                llm_config=llm_config,
                experiment_depth=job["experiment_depth"],
            )
        else:
            result = agent.run_paper_reproduction(
                text,
                grid_case=job["grid_case"],
                on_event=on_event,
                llm_config=llm_config,
                experiment_depth=job["experiment_depth"],
            )
        finish_job(job_id, result)
    except Exception as exc:
        fail_job(job_id, exc)

def append_job_event(job_id: str, event: Dict[str, Any], status: str = "running") -> None:
    job = JOBS.get(job_id)
    if not job:
        return
    
    event = dict(event)
    event["time"] = time.time()
    job["status"] = status
    job["current_step"] = event.get("step", "")
    job["current_summary"] = event.get("summary", "")
    job["events"].append(event)
    job["updated_at"] = time.time()

def finish_job(job_id: str, result: Dict[str, Any]) -> None:
    job = JOBS.get(job_id)
    if not job:
        return
    
    job["status"] = "completed"
    job["current_step"] = "completed"
    job["current_summary"] = "Agent finished and wrote the experiment package."
    job["result"] = summarize_result_static(result)
    job["updated_at"] = time.time()
    
    try:
        workspace = get_workspace()
        project_info = workspace.get_project(result["run_id"])
        if project_info:
            project_info["grid_case"] = job.get("grid_case")
            project_info["experiment_depth"] = job.get("experiment_depth")
            workspace.db.add_project(project_info)
            
            metrics = result.get("metrics", [])
            if metrics:
                workspace.db.add_project_metrics(result["run_id"], metrics)
    except Exception as e:
        logger.error(f"Failed to save project to database: {e}")

def fail_job(job_id: str, exc: Exception) -> None:
    job = JOBS.get(job_id)
    if not job:
        return
    
    job["status"] = "failed"
    job["current_step"] = "failed"
    job["current_summary"] = str(exc)
    job["error"] = str(exc)
    job["updated_at"] = time.time()

def summarize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return summarize_result_static(result)

def summarize_result_static(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": result["run_id"],
        "run_dir": os.path.abspath(result["run_dir"]),
        "artifacts": {key: os.path.abspath(path) for key, path in result["artifacts"].items()},
        "report_preview": result.get("report_preview", ""),
        "model_spec": result.get("model_spec", {}),
        "strategy_spec": result.get("strategy_spec", []),
        "innovation_spec": result.get("innovation_spec", {}),
        "analysis_meta": result.get("analysis_meta", {}),
        "reproduction_gaps": result.get("reproduction_gaps", []),
        "experiment_config": result.get("experiment_config", {}),
        "metrics": result.get("metrics", []),
        "trace": result.get("trace", []),
        "executions": result.get("executions", []),
    }


def run_server(host: str = "127.0.0.1", port: int = 8765, run_root: str = "runs") -> None:
    global RUN_ROOT
    # If the caller did not pass an explicit run_root, derive one from
    # the data root so the contract in `AGENTS.md` is honored.
    if run_root == "runs" and os.environ.get("ENERGY_LAB_DATA_DIR"):
        RUN_ROOT = os.path.join(get_data_root(), "runs")
    else:
        RUN_ROOT = run_root

    import uvicorn
    uvicorn.run(
        "p2plab.api.fastapi_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


# ---------------------------------------------------------------------------
# Plugin surfaces (added in 0.2.0)
# ---------------------------------------------------------------------------

@app.get("/api/plugins/algorithms", tags=["插件"])
def list_algorithms_endpoint():
    """List discovered algorithm templates (built-in + user-installed)."""
    from ..plugin_loader import list_algorithm_templates_with_runtime
    templates = list_algorithm_templates_with_runtime()
    return {
        "count": len(templates),
        "templates": [t.to_dict() for t in templates],
    }


@app.get("/api/plugins/scenarios", tags=["插件"])
def list_scenarios_endpoint():
    """List discovered simulation scenarios (built-in + user-installed)."""
    from ..plugin_loader import list_scenarios_with_runtime
    scenarios = list_scenarios_with_runtime()
    return {
        "count": len(scenarios),
        "scenarios": [s.to_dict() for s in scenarios],
    }


if __name__ == "__main__":
    run_server()
