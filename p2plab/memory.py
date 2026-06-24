from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from .utils import ensure_dir


class JsonlMemoryStore:
    """Tiny file-backed memory for experiments, failures, and preferences."""

    def __init__(self, root_dir: str = "runs"):
        ensure_dir(root_dir)
        self.path = os.path.join(root_dir, "memory.jsonl")

    def append(self, event_type: str, payload: Dict[str, Any]) -> None:
        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        return rows[-limit:]
