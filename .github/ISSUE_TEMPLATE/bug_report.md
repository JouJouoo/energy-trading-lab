---
name: Bug report
about: Tell us something is broken
title: "[Bug] "
labels: bug
assignees: ''
---

## What you ran

The exact `python -m p2plab.cli ...` invocation, or the web UI route you used.

## What you expected

One sentence.

## What happened

One sentence + the relevant stderr tail (most "the artifact never showed up" reports get diagnosed in 30 seconds when we can see the actual error).

## Environment

- OS: (macOS / Linux / Windows)
- Python version: `python --version`
- ETL version: `git rev-parse HEAD`
- LLM provider: (OpenAI / DeepSeek / Qwen / Moonshot / Custom / none)
- Plugin roots: `python -c "from p2plab.plugin_loader import discover_algorithm_templates, discover_scenarios; print(discover_algorithm_templates()); print(discover_scenarios())"`

## Screenshot

If it's a UI bug, attach one. Drag the image into the editor.

## Workaround (optional)

If you found a way to make it work, share it. We can use it as a regression test.
