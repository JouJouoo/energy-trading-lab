# Translations

Energy Trading Lab uses two languages: **English** as the source-of-truth language for code, CLI flags, LLM prompts, and protocol specs; **Simplified Chinese** (zh-CN) for the user-facing web UI strings, the workspace copy, and the Chinese theory draft workflow.

This file documents which surfaces are translated, which are not, and the maintenance workflow.

## What gets translated

| Surface | English | zh-CN | Source of truth |
|---|---|---|---|
| Web UI strings (button labels, headings, hints) | optional | yes (default) | `web/src/views/*.vue`, `web/src/components/*.vue` |
| Workspace copy (empty state, hero copy) | optional | yes (default) | `web/src/views/WorkspaceView.vue` |
| CLI subcommand help text | yes | no | `p2plab/cli.py` (`argparse` descriptions) |
| CLI flags (`--grid-case`, `--experiment-depth`) | yes | no | `p2plab/cli.py` |
| LLM system prompts | yes | no | `p2plab/llm_analysis.py`, `p2plab/llm_adapters/*.py` |
| `TEMPLATE.md` / `SCENARIO.md` manifests | yes | no | per-template |
| `README.md` | yes | yes | `docs/i18n/README.en.md` (English) and `docs/i18n/README.zh-CN.md` (Chinese) |
| `docs/spec.md`, `docs/architecture.md`, `docs/skills-protocol.md`, etc. | yes | no | `docs/*.md` |
| Code comments | yes | no | inline |
| Commit messages | yes | optional | git log |
| GitHub issue / PR templates | yes | no | `.github/ISSUE_TEMPLATE/*.md`, `.github/PULL_REQUEST_TEMPLATE.md` |
| Sample papers / theory drafts in `examples/` | yes + zh-CN | mixed | `examples/sample_paper.md` (English) and `examples/theory_draft.md` (Chinese) |

## Why some things are English-only

- **CLI flags and LLM prompts** are passed to a parser / LLM in a single language; mixing causes substring-match failures and inconsistent behavior. Keeping them English-only makes them greppable for the model and for humans.
- **Protocol specs** (`TEMPLATE.md`, `SCENARIO.md`, `SKILL.md` analogues) are machine-consumed; they need a single canonical schema.
- **Code comments** are reference material for the next contributor; one language means one set of greppable strings.

## Why some things are Chinese-first

- The product's primary user base writes and reads theory drafts in Chinese. Keeping the workspace copy and UI hints in zh-CN matches that flow.

## Adding a new locale

1. Create `docs/i18n/README.<lang>.md` translated from `docs/i18n/README.en.md`.
2. For the web UI, add a locale-aware `t()` helper in `web/src/utils/i18n.js` (currently out of scope; see `docs/roadmap.md` 0.3.x).
3. Update the table above.
4. Mention the locale in `README.md`'s language footer.

## Maintenance workflow

- When a web UI string changes, update both English and Chinese in the same Vue SFC for now (we will split to a dictionary once we add a 3rd locale).
- When a CLI flag is renamed, update `docs/spec.md` and `docs/architecture.md` in the same PR.
- When a `TEMPLATE.md` adds a new frontmatter key, document the English name in `docs/skills-protocol.md`. No translation needed.

## What we don't accept

- A PR that translates the LLM system prompts to another language. The Agent's behavior would silently shift.
- A PR that translates the `TEMPLATE.md` schema. Plugin authors must write manifests in English to be consistent with `docs/skills-protocol.md`.
- A PR that splits English and Chinese strings inside a single Vue SFC's `<template>` block (use two `v-if` branches on a `lang` ref, or move to a dictionary in a follow-up).
