"""Plugin loader: discover algorithm templates and scenarios on disk.

This module is the runtime entry point for the plugin system. It scans the
configured roots at startup, parses the manifests, and returns lists of
`AlgorithmTemplate` / `ScenarioSpec` dataclasses.

It does **not** `import` the implementation files. The Agent loads the
template code lazily when it actually generates an experiment. The manifest
is metadata only.

## Root precedence

The merge order is **user-global > user-data > built-in**:

1. `~/.energy_trading_lab/<surface>/`  (user-global, OS-aware)
2. `$ENERGY_LAB_DATA_DIR/<surface>/`  (per-install, where the daemon writes)
3. `p2plab/algorithm_templates/`  (built-in)
3. `scenarios/`                    (built-in)

A user-installed template / scenario with the same `name` overrides the
built-in. The same `name` from two user roots is a config error and is
reported in the loader's debug log; the first-wins order is preserved.

## Frontmatter parser

`TEMPLATE.md` / `SCENARIO.md` use a constrained YAML frontmatter shape:

- Top-level keys: scalar / list / dict.
- Scalars: strings (unquoted, single-quoted, or double-quoted), ints, floats,
  booleans (`true` / `false`), and `null`.
- Lists: `[item, item, ...]` on a single line, or `- item` per line.
- Dicts: indented `key: value` lines, one level deep.

The parser is intentionally small. If a manifest needs richer YAML, add
`PyYAML` to `requirements.txt` and replace `_parse_simple_frontmatter`.

## Surface roots

The two surfaces have their own root conventions:

- Algorithm templates live under `p2plab/algorithm_templates/<family>/<name>/`.
  Family sub-folders are `Base/`, `RL/`, `Optimization/`, `Auction/`,
  `GameTheory/`, `RuleBased/`.

- Scenarios live flat under `scenarios/<name>/`. There is no family
  hierarchy for scenarios; the name is the unique identifier.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .plugin_manifest import (
    ALLOWED_FAMILIES,
    AlgorithmTemplate,
    ScenarioSpec,
    family_directory,
)


_LOG = logging.getLogger(__name__)


BUILTIN_TEMPLATES_ROOT = Path(__file__).resolve().parent / "algorithm_templates"
BUILTIN_SCENARIOS_ROOT = Path(__file__).resolve().parents[1] / "scenarios"


def _user_global_root(surface: str) -> Optional[Path]:
    """`~/.energy_trading_lab/<surface>/` (or platform equivalent)."""
    home = Path.home()
    if not home:
        return None
    return home / ".energy_trading_lab" / surface


def _user_data_root(surface: str) -> Optional[Path]:
    """`$ENERGY_LAB_DATA_DIR/<surface>/` (or None if not set)."""
    base = os.environ.get("ENERGY_LAB_DATA_DIR")
    if not base:
        return None
    return Path(base) / surface


def _candidate_roots(surface: str) -> List[Path]:
    """Return the merged root list, in precedence order (highest first)."""
    if surface == "algorithm_templates":
        roots: List[Path] = []
        global_root = _user_global_root(surface)
        if global_root is not None:
            roots.append(global_root)
        data_root = _user_data_root(surface)
        if data_root is not None:
            roots.append(data_root)
        roots.append(BUILTIN_TEMPLATES_ROOT)
        return roots
    if surface == "scenarios":
        roots = []
        global_root = _user_global_root(surface)
        if global_root is not None:
            roots.append(global_root)
        data_root = _user_data_root(surface)
        if data_root is not None:
            roots.append(data_root)
        roots.append(BUILTIN_SCENARIOS_ROOT)
        return roots
    raise ValueError("Unknown plugin surface: %s" % surface)


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _split_frontmatter(text: str) -> Optional[tuple]:
    """Return (frontmatter_text, body_text) if the text starts with `---`.

    A leading `---` line, content, and a closing `---` line. The body is
    everything after the closing `---`.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    return m.group(1), m.group(2)


def _coerce_scalar(value: str) -> Any:
    """Coerce a string scalar into a Python value.

    Supports: None, bool, int, float, and (un)quoted strings.
    """
    s = value.strip()
    if s == "" or s.lower() == "null" or s.lower() == "~":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return s[1:-1]
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        return s[1:-1]
    # Numeric
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_simple_frontmatter(text: str) -> Dict[str, Any]:
    """Parse a constrained YAML frontmatter into a dict.

    Handles:

    - `key: value` top-level pairs.
    - `key:` followed by indented (2+ spaces) lines for dict values.
    - `key: [a, b, c]` for list values.
    - Comments (`#`).

    Does not handle: nested dicts deeper than one level, multi-line strings,
    flow-style dicts, anchors / references. Those are intentionally not
    supported; the manifest format is small enough to do without them.
    """
    result: Dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            # Possible block: collect indented lines until next top-level key
            block: List[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if not nxt.strip() or nxt.lstrip().startswith("#"):
                    block.append(nxt)
                    j += 1
                    continue
                if nxt[:1] in (" ", "\t"):
                    block.append(nxt)
                    j += 1
                else:
                    break
            sub_text = "\n".join(block)
            result[key] = _parse_block(sub_text)
            i = j
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            items = [_coerce_scalar(p) for p in _split_flow_list(inner)]
            result[key] = items
        else:
            result[key] = _coerce_scalar(value)
        i += 1
    return result


def _split_flow_list(s: str) -> List[str]:
    """Split a flow-style list body by commas, respecting quoted strings."""
    out: List[str] = []
    buf: List[str] = []
    quote: Optional[str] = None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        out.append("".join(buf).strip())
    return [p for p in out if p != ""]


def _parse_block(text: str) -> Any:
    """Parse an indented block of key/value pairs (a dict)."""
    if not text.strip():
        return {}
    lines = text.splitlines()
    result: Dict[str, Any] = {}
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        # Strip leading indent (2+ spaces or tab)
        m = re.match(r"^([ \t]+)(.*)$", line)
        if not m:
            i += 1
            continue
        body = m.group(2)
        if ":" not in body:
            i += 1
            continue
        key, _, value = body.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            # Nested block — but we only support one level deep
            block: List[str] = []
            j = i + 1
            base_indent = len(m.group(1))
            while j < len(lines):
                nxt = lines[j]
                stripped = nxt.lstrip()
                if not stripped or stripped.startswith("#"):
                    block.append(nxt)
                    j += 1
                    continue
                # Compare indent
                lead = len(nxt) - len(stripped)
                if lead > base_indent:
                    block.append(nxt[base_indent:])
                    j += 1
                else:
                    break
            result[key] = _parse_block("\n".join(block))
            i = j
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            items = [_coerce_scalar(p) for p in _split_flow_list(inner)]
            result[key] = items
        else:
            result[key] = _coerce_scalar(value)
        i += 1
    return result


# ---------------------------------------------------------------------------
# Algorithm template discovery
# ---------------------------------------------------------------------------


def _read_manifest_text(folder: Path, *extra_names: str) -> Optional[str]:
    """Read the first existing manifest file in the folder.

    Default order: SCENARIO.md, TEMPLATE.md, SCENARIO.yaml, SCENARIO.yml,
    TEMPLATE.yaml, TEMPLATE.yml. Callers may pass additional file names
    to try (e.g. "RUN.md" for a future run surface).
    """
    candidates = [
        "SCENARIO.md",
        "TEMPLATE.md",
        "SCENARIO.yaml",
        "SCENARIO.yml",
        "TEMPLATE.yaml",
        "TEMPLATE.yml",
        *extra_names,
    ]
    for name in candidates:
        candidate = folder / name
        if candidate.exists() and candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8")
            except OSError as exc:
                _LOG.warning("Failed to read %s: %s", candidate, exc)
                return None
    return None


def _parse_algorithm_manifest(folder: Path, family: str) -> Optional[AlgorithmTemplate]:
    text = _read_manifest_text(folder)
    if text is None:
        return None
    parts = _split_frontmatter(text)
    if parts is None:
        _LOG.warning("Template folder %s has no YAML frontmatter.", folder)
        return None
    fm, _body = parts
    try:
        data = _parse_simple_frontmatter(fm)
    except Exception as exc:
        _LOG.warning("Failed to parse %s/TEMPLATE.md: %s", folder, exc)
        return None

    name = str(data.get("name") or folder.name)
    declared_family = str(data.get("family") or family)
    file_name = str(data.get("file_name") or f"{name}.py")
    display_name = str(data.get("display_name") or name)

    if declared_family not in ALLOWED_FAMILIES:
        _LOG.warning(
            "Template %s has unknown family %r; falling back to folder family %r.",
            name,
            declared_family,
            family,
        )
        declared_family = family or "RL"

    description = str(data.get("description") or "")
    affected = list(data.get("affected_modules") or [])
    inputs = dict(data.get("inputs") or {})
    parameters = dict(data.get("parameters") or {})
    validation = dict(data.get("validation") or {})
    tags = list(data.get("tags") or [])

    impl_path = folder / file_name
    if not impl_path.exists():
        _LOG.warning(
            "Template %s declares file_name=%s but the file does not exist in %s.",
            name,
            file_name,
            folder,
        )

    return AlgorithmTemplate(
        name=name,
        family=declared_family,
        display_name=display_name,
        file_name=file_name,
        description=description,
        affected_modules=affected,
        inputs=inputs,
        parameters=parameters,
        validation=validation,
        tags=tags,
        source=str(folder),
    )


def discover_algorithm_templates(
    roots: Optional[Sequence[Path]] = None,
) -> List[AlgorithmTemplate]:
    """Discover algorithm templates from the configured roots.

    `roots` is the candidate root list. If `None`, the loader uses
    `_candidate_roots("algorithm_templates")` which honors the user-global
    / user-data / built-in precedence.
    """
    if roots is None:
        roots = _candidate_roots("algorithm_templates")

    by_name: Dict[str, AlgorithmTemplate] = {}
    for root in roots:
        if not root or not root.exists():
            continue
        # The root is a directory of family sub-folders; iterate them.
        for family_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            family_name = family_dir.name
            for template_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
                # Family mismatch: keep going; the manifest can override.
                # The folder family is used as a fallback in _parse_algorithm_manifest.
                canonical = family_directory(family_name)
                template = _parse_algorithm_manifest(template_dir, canonical)
                if template is None:
                    continue
                # Precedence: keep the first registration; warn on conflicts.
                if template.name in by_name:
                    _LOG.debug(
                        "Template %r already registered from %s; ignoring %s.",
                        template.name,
                        by_name[template.name].source,
                        template.source,
                    )
                    continue
                by_name[template.name] = template
    return list(by_name.values())


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------


def _parse_scenario_manifest(folder: Path) -> Optional[ScenarioSpec]:
    text = _read_manifest_text(folder)
    if text is None:
        return None
    # We try SCENARIO.md first; if it's missing, fall back to the same
    # `_read_manifest_text` order. So a SCENARIO.md takes priority.
    scenario_md = folder / "SCENARIO.md"
    if not scenario_md.exists():
        return None
    parts = _split_frontmatter(text)
    if parts is None:
        _LOG.warning("Scenario folder %s has no YAML frontmatter.", folder)
        return None
    fm, _body = parts
    try:
        data = _parse_simple_frontmatter(fm)
    except Exception as exc:
        _LOG.warning("Failed to parse %s/SCENARIO.md: %s", folder, exc)
        return None

    name = str(data.get("name") or folder.name)
    display_name = str(data.get("display_name") or name)
    bus_count = int(data.get("bus_count") or 0)
    base_voltage_kv = float(data.get("base_voltage_kv") or 0.0)
    vl = data.get("voltage_limits") or [0.95, 1.05]
    if not isinstance(vl, list) or len(vl) != 2:
        vl = [0.95, 1.05]
    voltage_limits = [float(vl[0]), float(vl[1])]
    topology_source = str(data.get("topology_source") or "")
    feeder_file = str(data.get("feeder_file") or "feeder.json")
    prosumer_layout_file = data.get("prosumer_layout_file")
    load_profile_file = data.get("load_profile_file")
    pv_profile_file = data.get("pv_profile_file")
    metrics_schema = list(data.get("metrics_schema") or [])
    tags = list(data.get("tags") or [])

    if bus_count <= 0:
        _LOG.warning("Scenario %s has invalid bus_count; skipping.", name)
        return None
    if not (folder / feeder_file).exists():
        _LOG.warning(
            "Scenario %s declares feeder_file=%s but the file is missing.",
            name,
            feeder_file,
        )
    # 9-section body check — emit a warning, don't fail (legacy support).
    body = parts[1] if parts else ""
    required_sections = [
        "network topology",
        "bus types",
        "voltage base",
        "line parameters",
        "load",
        "prosumer",
        "constraints",
        "output metrics",
        "anti-patterns",
    ]
    body_lower = body.lower()
    missing = [s for s in required_sections if s not in body_lower]
    if missing:
        _LOG.debug(
            "Scenario %s body missing 9-section headings: %s",
            name,
            missing,
        )

    return ScenarioSpec(
        name=name,
        display_name=display_name,
        bus_count=bus_count,
        base_voltage_kv=base_voltage_kv,
        voltage_limits=voltage_limits,
        topology_source=topology_source,
        feeder_file=feeder_file,
        prosumer_layout_file=str(prosumer_layout_file) if prosumer_layout_file else None,
        load_profile_file=str(load_profile_file) if load_profile_file else None,
        pv_profile_file=str(pv_profile_file) if pv_profile_file else None,
        metrics_schema=metrics_schema,
        tags=tags,
        source=str(folder),
    )


def discover_scenarios(roots: Optional[Sequence[Path]] = None) -> List[ScenarioSpec]:
    """Discover scenarios from the configured roots.

    Scenarios live flat: one folder per scenario, no family hierarchy.
    """
    if roots is None:
        roots = _candidate_roots("scenarios")

    by_name: Dict[str, ScenarioSpec] = {}
    for root in roots:
        if not root or not root.exists():
            continue
        for scenario_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            spec = _parse_scenario_manifest(scenario_dir)
            if spec is None:
                continue
            if spec.name in by_name:
                _LOG.debug(
                    "Scenario %r already registered from %s; ignoring %s.",
                    spec.name,
                    by_name[spec.name].source,
                    spec.source,
                )
                continue
            by_name[spec.name] = spec
    return list(by_name.values())


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def get_algorithm_template(name: str) -> Optional[AlgorithmTemplate]:
    """Return the discovered template with the given name, or None."""
    for template in discover_algorithm_templates():
        if template.name == name:
            return template
    return None


def get_scenario(name: str) -> Optional[ScenarioSpec]:
    """Return the discovered scenario with the given name, or None."""
    for spec in discover_scenarios():
        if spec.name == name:
            return spec
    return None


# ---------------------------------------------------------------------------
# Optional runtime template / scenario registration
# ---------------------------------------------------------------------------

# An in-process registry for templates / scenarios added at runtime. The web
# UI can call `register_template(...)` after a user uploads a TEMPLATE.md
# via the workspace; the registered template is then discoverable in the
# same process.
_runtime_templates: Dict[str, AlgorithmTemplate] = {}
_runtime_scenarios: Dict[str, ScenarioSpec] = {}


def register_template(template: AlgorithmTemplate) -> None:
    """Add (or replace) a template in the in-process runtime registry.

    Note: this only affects the current process. To make a template
    persistent, write its folder under one of the discovery roots and
    restart the daemon.
    """
    _runtime_templates[template.name] = template


def register_scenario(scenario: ScenarioSpec) -> None:
    """Add (or replace) a scenario in the in-process runtime registry."""
    _runtime_scenarios[scenario.name] = scenario


def list_algorithm_templates_with_runtime() -> List[AlgorithmTemplate]:
    """All discovered templates, with runtime registrations applied on top."""
    base = {t.name: t for t in discover_algorithm_templates()}
    base.update(_runtime_templates)
    return list(base.values())


def list_scenarios_with_runtime() -> List[ScenarioSpec]:
    """All discovered scenarios, with runtime registrations applied on top."""
    base = {s.name: s for s in discover_scenarios()}
    base.update(_runtime_scenarios)
    return list(base.values())
