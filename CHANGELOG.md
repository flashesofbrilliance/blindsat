# Changelog

All notable changes to `sat_private` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- Provider adapters (OpenAI, Anthropic)
- Retry + parse-error recovery
- CLI entry point
- Async pipeline variant

---

## [0.1.0] — 2026-04-27

### Added
- `sat_private/core.py` — encode, CNF, prompts, DIMACS, decode
- `sat_private/pipeline.py` — `run_pipeline` orchestrator
- `sat_private/__init__.py` — public API surface
- `tests/` — 22 unit tests, 9 integration tests, 15 edge case tests
- `docs/` — DoD, user testing plan, use cases, next steps
- `examples/` — access control, feature flags, compliance rules
- `.github/workflows/ci.yml` — pytest + coverage + security checks
- Project scaffolding: `pyproject.toml`, `requirements.txt`, `Makefile`, `.gitignore`
