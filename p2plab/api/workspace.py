from __future__ import annotations

import os
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from ..database import Database


def get_data_root() -> str:
    """Resolve the data root per the contract in `AGENTS.md`.

    Precedence: `ENERGY_LAB_DATA_DIR` env var if set, else `./data`.
    Lives in this module (not `fastapi_server`) so the CLI can compute
    paths without importing FastAPI.
    """
    env = os.environ.get("ENERGY_LAB_DATA_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.abspath("./data")


class WorkspaceManager:
    def __init__(self, run_root: str = "runs", db_path: str = "data/db.sqlite"):
        self.run_root = run_root
        self.db_path = db_path
        Path(run_root).mkdir(parents=True, exist_ok=True)
        self.db = Database(db_path=db_path)
    
    def list_projects(self) -> List[Dict[str, any]]:
        db_projects = self.db.list_projects()
        if db_projects:
            return [self._format_project(p) for p in db_projects]
        
        projects = []
        run_dir = Path(self.run_root)
        
        if not run_dir.exists():
            return projects
        
        for item in run_dir.iterdir():
            if item.is_dir():
                project_info = self._get_project_info(item)
                if project_info:
                    projects.append(project_info)
                    self.db.add_project(project_info)
        
        projects.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return projects
    
    def _format_project(self, project: Dict[str, any]) -> Dict[str, any]:
        formatted = {
            "run_id": project.get("id") or project.get("run_id"),
            "run_dir": project.get("run_dir"),
            "title": project.get("title", "Untitled"),
            "research_problem": project.get("research_problem", ""),
            "source_type": project.get("source_type", "unknown"),
            "grid_case": project.get("grid_case"),
            "experiment_depth": project.get("experiment_depth"),
            "strategy_count": project.get("strategy_count", 0),
            "best_strategy": project.get("best_strategy"),
            "best_cost": project.get("best_cost"),
            "artifact_count": project.get("artifact_count", 0),
            "has_code_project": bool(project.get("has_code_project")),
            "llm_model": project.get("llm_model"),
            "analysis_source": project.get("analysis_source"),
        }
        
        created_at = project.get("created_at")
        if isinstance(created_at, str):
            try:
                formatted["created_at"] = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
            except:
                formatted["created_at"] = 0
        else:
            formatted["created_at"] = created_at or 0
        
        modified_at = project.get("modified_at")
        if isinstance(modified_at, str):
            try:
                formatted["modified_at"] = datetime.fromisoformat(modified_at.replace("Z", "+00:00")).timestamp()
            except:
                formatted["modified_at"] = 0
        else:
            formatted["modified_at"] = modified_at or 0
        
        return formatted
    
    def _get_project_info(self, dir_path: Path) -> Optional[Dict[str, any]]:
        try:
            info = {
                "run_id": dir_path.name,
                "run_dir": str(dir_path.absolute()),
                "created_at": dir_path.stat().st_ctime,
                "modified_at": dir_path.stat().st_mtime,
            }
            
            model_spec_path = dir_path / "model_spec.json"
            if model_spec_path.exists():
                with open(model_spec_path, "r", encoding="utf-8") as f:
                    model_spec = json.load(f)
                    info["title"] = model_spec.get("title", "Untitled")
                    info["research_problem"] = model_spec.get("research_problem", "")
                    info["source_type"] = model_spec.get("source_type", "unknown")
            
            metrics_path = dir_path / "metrics.json"
            if metrics_path.exists():
                with open(metrics_path, "r", encoding="utf-8") as f:
                    metrics = json.load(f)
                    if isinstance(metrics, list) and metrics:
                        info["strategy_count"] = len(metrics)
                        best = min(metrics, key=lambda x: float(x.get("total_cost", float("inf"))))
                        info["best_strategy"] = best.get("strategy", "")
                        info["best_cost"] = best.get("total_cost")
            
            analysis_meta_path = dir_path / "analysis_meta.json"
            if analysis_meta_path.exists():
                with open(analysis_meta_path, "r", encoding="utf-8") as f:
                    analysis_meta = json.load(f)
                    info["analysis_source"] = analysis_meta.get("analysis_source", "")
                    info["llm_model"] = analysis_meta.get("llm_status", {}).get("model", "")
            
            artifacts = []
            for ext in ["json", "md", "csv"]:
                for file in dir_path.glob(f"*.{ext}"):
                    artifacts.append(file.name)
            info["artifact_count"] = len(artifacts)
            info["artifacts"] = artifacts[:10]
            
            code_project = dir_path / "code_project"
            if code_project.exists():
                info["has_code_project"] = True
            
            return info
            
        except Exception:
            return None
    
    def get_project(self, run_id: str) -> Optional[Dict[str, any]]:
        db_project = self.db.get_project(run_id)
        if db_project:
            return self._format_project(db_project)
        
        dir_path = Path(self.run_root) / run_id
        if not dir_path.exists() or not dir_path.is_dir():
            return None
        
        project_info = self._get_project_info(dir_path)
        if project_info:
            self.db.add_project(project_info)
        return project_info
    
    def delete_project(self, run_id: str) -> bool:
        dir_path = Path(self.run_root) / run_id
        if dir_path.exists():
            import shutil
            shutil.rmtree(dir_path)
        
        self.db.delete_project(run_id)
        return True
    
    def get_project_artifact(self, run_id: str, artifact_name: str) -> Optional[str]:
        dir_path = Path(self.run_root) / run_id
        artifact_path = dir_path / artifact_name
        
        if not artifact_path.exists():
            return None
        
        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    
    def get_project_metrics(self, run_id: str) -> Optional[List[Dict[str, any]]]:
        return self._load_json_artifact(run_id, "metrics.json")
    
    def get_project_trace(self, run_id: str) -> Optional[List[Dict[str, any]]]:
        return self._load_json_artifact(run_id, "agent_trace.json")
    
    def get_project_report(self, run_id: str) -> Optional[str]:
        return self.get_project_artifact(run_id, "run_report.md")
    
    def _load_json_artifact(self, run_id: str, filename: str) -> Optional[any]:
        content = self.get_project_artifact(run_id, filename)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None
