# Next Steps — sat_private

Backlog items organised by horizon. Items marked `[N-xx]` are referenced in the codebase.

---

## Horizon 0 — Before v0.1.0 Release (this sprint)

| ID | Item | Owner |
|---|---|---|
| N-01 | Push all scaffolding files to `main` | ARCS |
| N-02 | Confirm CI passes on Python 3.10 / 3.11 / 3.12 | ARCS |
| N-03 | Run Session 1 Quick Start test with real user | Team |
| N-04 | Add `ruff` to dev dependencies in `pyproject.toml` | ARCS |

---

## Horizon 1 — v0.2.0 (next 2 weeks)

| ID | Item | Notes |
|---|---|---|
| N-05 | Provider adapters: OpenAI + Anthropic | Inject via `llm_call_fn` parameter |
| N-06 | Retry + parse-error recovery | Handle garbled LLM responses gracefully |
| N-07 | Auto-calibrated decoy count | Scale decoys with `n_vars` |
| N-08 | CLI entry point (`python -m sat_private`) | Thin wrapper around `run_pipeline` |
| N-09 | DIMACS/LLM consistency check step | Post-hoc cross-validate solver output |
| N-10 | Async `run_pipeline` variant | `async def run_pipeline_async(...)` |

---

## Horizon 2 — v0.3.0 (next month)

| ID | Item | Notes |
|---|---|---|
| N-11 | Session rotation: expire token maps after N uses | Reduces token-map exfiltration surface |
| N-12 | Multi-formula batch mode | Queue of formulas, single session |
| N-13 | Streaming verifier response parsing | Reduce latency on large formulas |
| N-14 | Token noise injection (semantic camouflage) | Add plausible-looking fake tokens to VARS block |
| N-15 | OpenTelemetry tracing | Instrument `encode`, `prompt`, `verify`, `decode` spans |

---

## Horizon 3 — Research / Experimental

| ID | Item | Notes |
|---|---|---|
| N-16 | First-order logic extension | Move beyond propositional SAT |
| N-17 | Homomorphic encoding | Replace hex tokens with algebraically structured encodings |
| N-18 | Multi-LLM ensemble voting | Majority vote across 3+ providers for higher accuracy |
| N-19 | Zero-knowledge proof of correct decode | Cryptographic guarantee that caller decoded honestly |
| N-20 | Benchmark suite vs. MiniSAT / Z3 | Accuracy + latency comparison |
| N-21 | Published benchmark dataset | Anonymised test formulas for reproducibility |
