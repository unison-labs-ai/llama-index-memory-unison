# Contributing to llama-index-memory-unison

Thanks for helping improve the LlamaIndex memory integration for Unison.

## Repo layout

A single-package Python project:

- `src/llama_index/memory/unison/base.py` — `UnisonMemory` class: `put`, `get`, `get_all`, `set`, `reset`
- `src/llama_index/memory/unison/_client.py` — thin async HTTP client wrapping the Unison brain API
- `src/llama_index/memory/unison/__init__.py` — public exports
- `tests/test_smoke.py` — unit and smoke tests (httpx mocking, no live API required)
- `pyproject.toml` — build config, metadata, and dependency pins

## Development

```bash
pip install -e . pytest httpx llama-index-core
pytest -q
```

## Before opening a PR

1. `pytest -q` must pass.
2. Keep changes scoped — one logical change per PR.
3. Add or update a test for every new behavior.
4. Do not commit `.env` or any real credentials.

## Conventions

- Runtime deps: `llama-index-core>=0.11` and `httpx>=0.27` only — keep the footprint minimal.
- `UnisonMemory` must degrade gracefully when the brain is unreachable or `UNISON_TOKEN` is absent — log a warning, never raise in `get()` or `put()`.
- The client enforces nothing — the Unison backend is the only security boundary. Do not add client-side scope or path checks.
- No comments unless the logic is genuinely non-obvious. Good names explain themselves.

## Reporting bugs / proposing features

Use the issue templates. For security issues, see [`SECURITY.md`](./SECURITY.md) — do **not** open a public issue.
