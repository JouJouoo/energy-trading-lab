# Code review guidelines

This is the bar a PR has to clear before we merge it. It complements the contribution flow in `CONTRIBUTING.md`; the focus here is *what to look for during review*.

## 1. One concern per PR

A PR that adds an algorithm template + refactors the parser + bumps a dep is three PRs. Push back early.

If the refactor is necessary to make the feature land cleanly, do the refactor as a separate PR first, then land the feature.

## 2. Why before what

The PR description must answer:

- **Why** does this need to exist?
- **What** does the user see that they didn't see before?
- **Surface area**: which files / endpoints / CLI flags / UI views change?
- **Tests**: which tests cover the new behavior? Did the author run them?
- **Bug fix verification** (bug-fix PRs only): what's the reproduction before / after?

If the description is empty or hand-wavy, request changes before reviewing the code.

## 3. Plugin discipline

For `plugin:algorithm`, `plugin:scenario`, `plugin:llm` PRs:

- The folder layout matches `docs/skills-protocol.md` or `docs/scenarios-protocol.md`.
- The manifest's frontmatter parses (CI enforces this via `tests/test_plugin_manifest.py`).
- The implementation has a smoke test, even a trivial one.
- The body sections are present, even if some are short.
- The merge label is correct.

If the manifest is incomplete, request changes — a half-filled `TEMPLATE.md` breaks the discovery contract for every other plugin.

## 4. CLI parity

If the PR adds a new FastAPI endpoint, the matching `p2plab/cli.py` subcommand must land in the same PR. `tests/test_cli_parity.py` enforces the equivalence.

If the PR adds a new CLI subcommand without an HTTP endpoint, the PR description must justify why (e.g. "this is a developer-only command, not a user-facing capability").

## 5. Backward compatibility

- We delete cleanly. No re-exports of removed symbols; no `*_legacy.py` shims.
- If the PR renames a public symbol, the PR must update every caller. We do not preserve the old name as an alias.
- If the PR changes a CLI flag, the old flag is removed in the same PR. We do not deprecate-with-warning unless the cost of the immediate break is high.

## 6. Tests as part of the change

- New behavior → new test.
- Bug fix → regression test that fails before the fix and passes after.
- Refactor → the existing tests must still pass; add a test if the refactor uncovered behavior that was previously untested.

If a PR has no tests and no clear reason for skipping them, request changes.

## 7. Style

- **Python**: `from __future__ import annotations`, dataclass + type hints, snake_case. The legacy modules that lack type hints are grandfathered in but new modules should be fully typed.
- **Vue**: `<script setup>` + Composition API. New components should not use Options API.
- **Comments**: English only. The body of `TEMPLATE.md` / `SCENARIO.md` is English only. The body of UI strings is zh-CN (see `TRANSLATIONS.md`).

## 8. What we don't block on

- Cosmetic preferences that don't affect readability.
- Naming bikesheds where the proposed name is reasonable. Pick one, document it in the relevant `docs/*.md` file, move on.
- Pre-existing lint warnings that aren't introduced by this PR. File a separate issue.
- Documentation improvements that aren't strictly required by the change. Encouraged, but not blocking.

## 9. Reviewer etiquette

- Review within a week of being assigned. For MVP-stage, "within a week" is the SLA.
- If you can't review in time, say so in the PR thread and reassign.
- If you don't have the domain expertise (e.g. Power systems for a power-flow PR), say so. A non-expert review is still useful for style, tests, and CLI parity.

## 10. Approval

A PR is mergeable when:

- It has at least one approval from a maintainer.
- All CI checks pass.
- The branch is up to date with `main`.
- The PR description answers the questions in §2.

The merge button is the maintainer's. Squash-on-merge is the default.
