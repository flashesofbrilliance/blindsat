# User Testing Plan — sat_private POC

## Objectives

1. Validate the privacy guarantee is legible to a new reader in under 5 minutes.
2. Confirm Quick Start works end-to-end on a clean machine.
3. Stress-test SAT accuracy across LLM providers and formula sizes.
4. Surface failure modes not covered by unit tests.
5. Red-team the secret state boundary.

---

## Tester Profiles

| Profile | Count | Purpose |
|---|---|---|
| Python dev (no SAT background) | 2 | Usability / onboarding |
| Security / compliance engineer | 2 | Privacy guarantees, threat model |
| ML / LLM engineer | 2 | LLM accuracy, provider swapping |
| Red-team / adversarial tester | 1 | Secret state leakage attempts |

---

## Sessions

### Session 1 — Quick Start
- Tester clones repo on clean machine, runs `pip install -e .`, then `python examples/access_control.py`.
- Pass criterion: no errors, `verified=True` or graceful `UNSAT` within 60 seconds.

### Session 2 — Live LLM Integration
- Tester supplies their own OpenAI or Anthropic key via `.env`.
- Runs `python -m sat_private.demo` against the live API.
- Pass criterion: SAT result returned, verifier confirms, decoded assignment maps to real variable names correctly.

### Session 3 — DIMACS Cross-Validation
- Tester runs 10 diverse formulas through `run_pipeline`, exports `.cnf`, pipes to `minisat`.
- Pass criterion: LLM assignment agrees with MiniSAT on ≥ 9/10 formulas.

### Session 4 — Privacy Red-Team
- Tester inspects every LLM prompt and response at runtime (debug mode).
- Attempts to infer real variable meanings from token patterns alone.
- Pass criterion: zero real meanings reconstructable from prompts, logs, or DIMACS output.

### Session 5 — Edge Case Suite
- Tester runs `pytest tests/test_edge_cases.py -v` from a clean install.
- Pass criterion: all EC-xx tests green, no skipped.

---

## Metrics

| Metric | Target |
|---|---|---|
| Time-to-first-result (Quick Start) | < 2 min |
| SAT/DIMACS agreement rate | ≥ 90% |
| Verifier catch rate (injected bad assignments) | 100% |
| Semantic leakage incidents | 0 |
| Tester-reported confusion points | Documented, P1 fixed before v0.2 |
| CI green on all Python versions | 100% |
| `pytest --cov` coverage | ≥ 90% |
