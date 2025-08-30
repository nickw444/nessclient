# Agent Contribution Guidelines

This repository is developed with assistance from AI coding agents. To keep the
codebase consistent and easy to maintain, agents must follow these rules when
creating or modifying code and tests.

## Imports
- All imports must be static at module scope. Do not import inside functions,
  coroutines, or test cases. This ensures import errors surface early and keeps
  tests readable and type-checker friendly.

## Tests
- Prefer interacting with objects via their public API only. Avoid calling
  private or underscored methods in tests.
- Keep tests deterministic and side-effect free; avoid relying on timing where
  possible. If concurrency is required, use explicit synchronization (e.g.
  awaiting a queued item) rather than sleeps.

## Style
- Match the repository’s existing style and patterns. Run format/lint/type
  checks using the documented `uv` tasks before pushing.

## Documentation
- Update examples and docs when adding or changing public APIs so they remain
  consistent and copy-paste runnable.

If a situation requires deviating from these rules, clearly justify the change
in the PR description.

