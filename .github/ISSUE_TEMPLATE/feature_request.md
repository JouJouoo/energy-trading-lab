---
name: Feature request
about: Suggest something the Agent should do
title: "[Feature] "
labels: enhancement
assignees: ''
---

## What you want

One sentence.

## Why you want it

What's the user / researcher pain point? Link a paper, a use case, or a workflow gap.

## How it would work

Sketch the user-visible behavior. If the feature involves a new plugin surface (algorithm, scenario, LLM provider), name the folder / file the new plugin would live in.

## Surface area

Which surfaces would change?

- [ ] Algorithm template (`p2plab/algorithm_templates/<family>/<name>/`)
- [ ] Scenario (`scenarios/<grid>/`)
- [ ] LLM adapter (`p2plab/llm_adapters/<provider>_adapter.py`)
- [ ] FastAPI endpoint (and matching CLI subcommand — required by the dual-track rule)
- [ ] Web UI view / component
- [ ] CLI subcommand
- [ ] Documentation
- [ ] Tests

## Willing to PR?

- [ ] Yes, I'd like to implement this.
- [ ] Yes, but I'd appreciate pairing.
- [ ] No, I'm just suggesting.
