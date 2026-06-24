from __future__ import annotations

import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .agent import P2PLabAgent
from .document_loader import extract_document_from_base64
from .llm import llm_status


class P2PLabRequestHandler(BaseHTTPRequestHandler):
    agent: P2PLabAgent = P2PLabAgent()
    run_root: str = "runs"
    web_root: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
    jobs: Dict[str, Dict[str, Any]] = {}
    jobs_lock = threading.Lock()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._serve_file(os.path.join(self.web_root, "index.html"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/health":
            self._json({"status": "ok", "product": "Energy Trading Lab"})
            return
        if parsed.path == "/api/llm-status":
            self._json(llm_status())
            return
        if parsed.path == "/api/runs":
            self._json({"memory": self.agent.memory.recent(limit=30)})
            return
        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = self._get_job(job_id)
            if job is None:
                self._json({"error": "Job not found"}, status=404)
                return
            self._json(job)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            text = payload.get("text") or payload.get("paper_text") or payload.get("theory_text") or ""
            grid_case = payload.get("grid_case", "ieee33")
            llm_config = payload.get("llm_config") or {}
            experiment_depth = payload.get("experiment_depth", "quick")
            if parsed.path == "/api/extract-document":
                self._json(
                    extract_document_from_base64(
                        filename=payload.get("filename", "document"),
                        data_base64=payload.get("data_base64", ""),
                    )
                )
                return
            if parsed.path == "/api/jobs":
                job = self._start_job(
                    mode=payload.get("mode", "reproduce"),
                    text=text,
                    grid_case=grid_case,
                    llm_config=llm_config,
                    experiment_depth=experiment_depth,
                )
                self._json(job)
                return
            if parsed.path == "/api/reproduce":
                result = self.agent.run_paper_reproduction(text, grid_case=grid_case, llm_config=llm_config, experiment_depth=experiment_depth)
                self._json(self._summarize(result))
                return
            if parsed.path == "/api/theory":
                result = self.agent.run_theory_experiment(text, grid_case=grid_case, llm_config=llm_config, experiment_depth=experiment_depth)
                self._json(self._summarize(result))
                return
            self.send_error(404, "Not found")
        except Exception as exc:
            self._json({"error": str(exc)}, status=500)

    def _start_job(self, mode: str, text: str, grid_case: str, llm_config: Dict[str, Any], experiment_depth: str) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        job = {
            "job_id": job_id,
            "mode": mode,
            "grid_case": grid_case,
            "experiment_depth": experiment_depth,
            "status": "queued",
            "current_step": "queued",
            "current_summary": "Waiting for the Agent worker.",
            "events": [],
            "result": None,
            "error": "",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        with self.jobs_lock:
            self.jobs[job_id] = job
        thread = threading.Thread(target=self._run_job, args=(job_id, mode, text, grid_case, llm_config, experiment_depth), daemon=True)
        thread.start()
        return self._get_job(job_id) or job

    @classmethod
    def _run_job(cls, job_id: str, mode: str, text: str, grid_case: str, llm_config: Dict[str, Any], experiment_depth: str) -> None:
        agent = P2PLabAgent(run_root=cls.run_root)
        cls._append_job_event(
            job_id,
            {
                "step": "start_job",
                "status": "ok",
                "summary": "Started %s workflow on %s." % (mode, grid_case),
                "details": {},
            },
            status="running",
        )

        def on_event(event: Dict[str, Any]) -> None:
            cls._append_job_event(job_id, event, status="running")
            if event.get("step") == "training_progress":
                time.sleep(0.02)
            elif event.get("step") in ("strategy_start", "strategy_done"):
                time.sleep(0.05)
            else:
                time.sleep(0.16)

        try:
            if mode == "theory":
                result = agent.run_theory_experiment(text, grid_case=grid_case, on_event=on_event, llm_config=llm_config, experiment_depth=experiment_depth)
            else:
                result = agent.run_paper_reproduction(text, grid_case=grid_case, on_event=on_event, llm_config=llm_config, experiment_depth=experiment_depth)
            cls._finish_job(job_id, result)
        except Exception as exc:  # pragma: no cover - surfaced via API
            cls._fail_job(job_id, exc)

    @classmethod
    def _append_job_event(cls, job_id: str, event: Dict[str, Any], status: str = "running") -> None:
        event = dict(event)
        event["time"] = time.time()
        with cls.jobs_lock:
            job = cls.jobs.get(job_id)
            if not job:
                return
            job["status"] = status
            job["current_step"] = event.get("step", "")
            job["current_summary"] = event.get("summary", "")
            job["events"].append(event)
            job["updated_at"] = time.time()

    @classmethod
    def _finish_job(cls, job_id: str, result: Dict[str, Any]) -> None:
        with cls.jobs_lock:
            job = cls.jobs.get(job_id)
            if not job:
                return
            job["status"] = "completed"
            job["current_step"] = "completed"
            job["current_summary"] = "Agent finished and wrote the experiment package."
            job["result"] = cls._summarize_static(result)
            job["updated_at"] = time.time()

    @classmethod
    def _fail_job(cls, job_id: str, exc: Exception) -> None:
        with cls.jobs_lock:
            job = cls.jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["current_step"] = "failed"
            job["current_summary"] = str(exc)
            job["error"] = str(exc)
            job["updated_at"] = time.time()

    def _get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            return json.loads(json.dumps(job, ensure_ascii=False)) if job else None

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def _serve_file(self, path: str, content_type: str) -> None:
        with open(path, "rb") as handle:
            data = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _summarize(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return self._summarize_static(result)

    @staticmethod
    def _summarize_static(result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "run_id": result["run_id"],
            "run_dir": os.path.abspath(result["run_dir"]),
            "artifacts": {key: os.path.abspath(path) for key, path in result["artifacts"].items()},
            "report_preview": result.get("report_preview", ""),
            "model_spec": result["model_spec"],
            "strategy_spec": result["strategy_spec"],
            "innovation_spec": result.get("innovation_spec", {}),
            "analysis_meta": result.get("analysis_meta", {}),
            "reproduction_gaps": result["reproduction_gaps"],
            "experiment_config": result["experiment_config"],
            "metrics": result["metrics"],
            "trace": result["trace"],
            "executions": result.get("executions", []),
        }


def run_server(host: str = "127.0.0.1", port: int = 8765, run_root: str = "runs") -> None:
    P2PLabRequestHandler.agent = P2PLabAgent(run_root=run_root)
    P2PLabRequestHandler.run_root = run_root
    server = ThreadingHTTPServer((host, port), P2PLabRequestHandler)
    print("Energy Trading Lab workspace: http://%s:%s" % (host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
