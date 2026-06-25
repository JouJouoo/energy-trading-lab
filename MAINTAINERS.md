# Maintainers

Energy Trading Lab is currently maintained by a single core contributor. This file documents the path to becoming a maintainer once the project grows beyond 1.0.0.

## Current Core Team

- **joujou** — original author and core maintainer.

## Path to becoming a Maintainer

The bar is intentionally low, because the project is small:

1. **Three merged PRs**, with at least one of them being a non-trivial feature (an algorithm template, a scenario, an LLM adapter, or a FastAPI endpoint + matching CLI subcommand).
2. **At least one review** of another contributor's PR that resulted in actionable changes.
3. **A demonstration of the dual-track discipline** — every new user-facing capability exposed through both the web UI and the `p2plab` CLI (see `AGENTS.md` §Capability exposure).

There is no application form. Existing maintainers raise candidates internally and reach out.

## Maintainer responsibilities

- Review PRs in a timely manner. For an MVP-stage project, "timely" is "within a week".
- Triage new issues. Tag with `bug`, `enhancement`, `docs`, `plugin:algorithm`, `plugin:scenario`, `plugin:llm`.
- Keep `AGENTS.md` honest — when the architecture shifts, update the directory guide.

## Stepping down

Stepping down is easy. Tell a fellow maintainer; we'll move you to emeritus in `CHANGELOG.md` and add you back when life calms down.

## Recognition

Every merged PR is recorded in `CHANGELOG.md` under the contributor's name (when we move to multi-maintainer operation). Plugin authors are credited in the relevant `TEMPLATE.md` / `SCENARIO.md` frontmatter.
