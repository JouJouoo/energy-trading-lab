## Why

One paragraph. What user / researcher pain point does this PR resolve? Why does it need to exist?

## What users will see

One paragraph. The user-visible change (UI, CLI, or both). Link screenshots or sample output.

## Surface area

Which files / endpoints / CLI flags / UI views change? Tick all that apply.

- [ ] `p2plab/` — backend
- [ ] `p2plab/algorithm_templates/<family>/<name>/` — new algorithm template
- [ ] `scenarios/<grid>/` — new scenario
- [ ] `p2plab/llm_adapters/<provider>_adapter.py` — new LLM adapter
- [ ] `web/src/` — frontend
- [ ] `tests/` — tests
- [ ] `docs/` — documentation
- [ ] `deploy/` — Docker
- [ ] `.github/` — CI / templates

## Tests

- [ ] `pytest tests/` passes locally
- [ ] New tests added (which file, which test names)
- [ ] Existing tests updated (which file, what changed)

## Plugin-specific (if applicable)

For `plugin:algorithm`, `plugin:scenario`, `plugin:llm`:

- [ ] `TEMPLATE.md` / `SCENARIO.md` frontmatter is complete
- [ ] All 9 body sections are present (scenarios)
- [ ] Entry-point symbol is implemented
- [ ] Smoke test passes

## Bug fix verification (bug-fix PRs only)

Reproduction steps before the fix, and what changes after:

```text
Before:
$ python -m p2plab.cli ...
... <error output> ...

After:
$ python -m p2plab.cli ...
... <expected output> ...
```

## Checklist

- [ ] I read `CONTRIBUTING.md` and `docs/code-review-guidelines.md`
- [ ] I added a row to `CHANGELOG.md` under `[Unreleased]`
- [ ] I did not introduce new top-level dependencies without justification in this PR description
- [ ] I did not edit `AGENTS.md` to add a project-specific exception (those go in a follow-up discussion)
