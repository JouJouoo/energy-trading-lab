# .github/ — CI and contributor templates

> Read this before editing anything under `.github/`. Boundary rules in `AGENTS.md` §"GitHub automation boundary" apply.

## Layout

```
.github/
├── AGENTS.md              # this file
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   └── feature_request.md
├── PULL_REQUEST_TEMPLATE.md
└── workflows/
    └── ci.yml             # the only business workflow
```

## Conventions

- CI is a single business workflow (`ci.yml`). Do not add per-feature workflows without a discussion in an issue.
- The workflow runs `pytest tests/ -v --tb=short` on every push and PR.
- The workflow does not have secrets. The LLM upstream is mocked; see `tests/AGENTS.md`.
- Issue / PR templates are deliberately short. If a contributor can't fill them in, the contribution isn't ready.
- This directory is not a "general CI playground". Anything that doesn't serve the contributor flow goes in `scripts/` (if it must exist) or in `tests/`.

## When you would add a new workflow

You probably shouldn't. Most of what people want to do with a new workflow (nightly eval, scheduled cleanup, release tagging) is on the 0.4.x roadmap. Open an issue first.
