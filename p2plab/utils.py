from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def slugify(value: str, fallback: str = "task") -> str:
    value = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", value).strip("-").lower()
    return value[:64] or fallback


def task_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return "%s-%s-%s" % (prefix, stamp, uuid.uuid4().hex[:6])


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def simple_yaml(data: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(data, dict):
        lines: List[str] = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append("%s%s:" % (pad, key))
                lines.append(simple_yaml(value, indent + 2))
            else:
                lines.append("%s%s: %s" % (pad, key, scalar_to_yaml(value)))
        return "\n".join(lines)
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append("%s-" % pad)
                lines.append(simple_yaml(item, indent + 2))
            else:
                lines.append("%s- %s" % (pad, scalar_to_yaml(item)))
        return "\n".join(lines)
    return "%s%s" % (pad, scalar_to_yaml(data))


def scalar_to_yaml(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return '"%s"' % value
        return str(value)
    text = str(value).replace('"', '\\"')
    if re.search(r"[:#\n]|^\s|\s$", text):
        return '"%s"' % text
    return text


def jain_fairness(values: Iterable[float]) -> float:
    vals = [max(0.0, float(v)) for v in values]
    if not vals:
        return 1.0
    numerator = sum(vals) ** 2
    denominator = len(vals) * sum(v * v for v in vals)
    if denominator <= 0:
        return 1.0
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
