from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import sqlite3

class Database:
    def __init__(self, db_path: str = "data/db.sqlite"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    research_problem TEXT,
                    source_type TEXT,
                    grid_case TEXT,
                    experiment_depth TEXT,
                    strategy_count INTEGER DEFAULT 0,
                    best_strategy TEXT,
                    best_cost REAL,
                    p2p_volume_kwh REAL,
                    carbon_kg REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    run_dir TEXT,
                    artifact_count INTEGER DEFAULT 0,
                    has_code_project INTEGER DEFAULT 0,
                    llm_model TEXT,
                    analysis_source TEXT,
                    status TEXT DEFAULT 'completed',
                    error TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    name TEXT,
                    path TEXT,
                    type TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    strategy TEXT,
                    total_cost REAL,
                    p2p_volume_kwh REAL,
                    carbon_kg REAL,
                    min_voltage_pu REAL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_project_artifacts_project_id ON project_artifacts(project_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_project_metrics_project_id ON project_metrics(project_id)
            ''')
            
            conn.commit()
    
    def add_project(self, project_data: Dict[str, Any]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO projects (
                        id, title, research_problem, source_type, grid_case,
                        experiment_depth, strategy_count, best_strategy, best_cost,
                        p2p_volume_kwh, carbon_kg, created_at, modified_at,
                        run_dir, artifact_count, has_code_project, llm_model,
                        analysis_source, status, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_data.get('run_id'),
                    project_data.get('title'),
                    project_data.get('research_problem'),
                    project_data.get('source_type'),
                    project_data.get('grid_case'),
                    project_data.get('experiment_depth'),
                    project_data.get('strategy_count', 0),
                    project_data.get('best_strategy'),
                    project_data.get('best_cost'),
                    project_data.get('p2p_volume_kwh'),
                    project_data.get('carbon_kg'),
                    datetime.fromtimestamp(project_data.get('created_at', 0)).isoformat() if project_data.get('created_at') else None,
                    datetime.fromtimestamp(project_data.get('modified_at', 0)).isoformat() if project_data.get('modified_at') else None,
                    project_data.get('run_dir'),
                    project_data.get('artifact_count', 0),
                    1 if project_data.get('has_code_project') else 0,
                    project_data.get('llm_model'),
                    project_data.get('analysis_source'),
                    project_data.get('status', 'completed'),
                    project_data.get('error')
                ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding project: {e}")
            return False
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
        except Exception as e:
            print(f"Error getting project: {e}")
            return None
    
    def list_projects(self, limit: int = 30, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM projects 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error listing projects: {e}")
            return []
    
    def delete_project(self, project_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM project_artifacts WHERE project_id = ?', (project_id,))
                cursor.execute('DELETE FROM project_metrics WHERE project_id = ?', (project_id,))
                cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False
    
    def add_project_metrics(self, project_id: str, metrics: List[Dict[str, Any]]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM project_metrics WHERE project_id = ?', (project_id,))
                
                for metric in metrics:
                    cursor.execute('''
                        INSERT INTO project_metrics (
                            project_id, strategy, total_cost, p2p_volume_kwh, carbon_kg, min_voltage_pu
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        project_id,
                        metric.get('strategy'),
                        metric.get('total_cost'),
                        metric.get('p2p_volume_kwh'),
                        metric.get('carbon_kg'),
                        metric.get('grid_validation', {}).get('min_voltage_pu')
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding project metrics: {e}")
            return False
    
    def get_project_metrics(self, project_id: str) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM project_metrics WHERE project_id = ?', (project_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting project metrics: {e}")
            return []
    
    def add_project_artifact(self, project_id: str, name: str, path: str, type: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO project_artifacts (project_id, name, path, type)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, name, path, type))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding artifact: {e}")
            return False
    
    def get_project_artifacts(self, project_id: str) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM project_artifacts WHERE project_id = ?', (project_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting artifacts: {e}")
            return []
    
    def set_setting(self, key: str, value: Any) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value)
                    VALUES (?, ?)
                ''', (key, value_str))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error setting setting: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
                row = cursor.fetchone()
                
                if row:
                    value = row['value']
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return default
        except Exception as e:
            print(f"Error getting setting: {e}")
            return default
    
    def get_project_count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM projects')
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            print(f"Error getting project count: {e}")
            return 0
