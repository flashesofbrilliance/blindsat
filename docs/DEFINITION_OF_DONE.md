# Definition of Done — sat_private v0.1.0

## Purpose

Criteria that must pass before any feature branch is merged or a release tag is cut.

---

## Functional Criteria

| # | Criterion | Acceptance condition |
|---|---|---|
| F-01 | Variable encoding | `encode_variables` produces unique 8-char uppercase hex tokens every call |
| F-02 | No semantic leakage | LLM user message contains zero symbolic variable names or real meanings |
| F-03 | CNF correctness | SymPy `to_cnf` output round-trips correctly through clause extraction |
| F-04 | DIMACS compatibility | Exported `.cnf` passes `minisat formula.cnf` without error |
| F-05 | Verifier gating | Pipeline makes exactly 2 LLM calls for SAT; 1 for UNSAT |
| F-06 | Decode accuracy | `decode_assignment` round-trips on random formulas (≤10 vars) |
| F-07 | Decoy injection | Decoy tokens appear only in VARS block, never in CLAUSES |
| F-08 | UNSAT handling | UNSAT result returns `decoded = {}` and skips verifier call |

---

## Quality Criteria

| # | Criterion | Target |
|---|---|---|
| Q-01 | Test coverage | ≥ 90% line coverage (`pytest --cov`) |
| Q-02 | Edge cases pass | All EC-xx tests green |
| Q-03 | No hardcoded tokens | Zero hardcoded hex strings outside test fixtures |
| Q-04 | Type hints | All public functions fully annotated |
| Q-05 | Docstrings | All public functions have docstrings |
| Q-06 | Lint clean | `ruff check .` returns zero errors |

---

## Security Criteria

| # | Criterion | Verification method |
|---|---|---|
| S-01 | Secret state never logged | `grep -r "token_map\|decode_map" logs/` returns nothing |
| S-02 | `.gitignore` covers secret files | `formula.cnf`, `caller_secret_state.json` confirmed ignored |
| S-03 | Tokens fresh per session | Two calls to `encode_variables` with same input yield different tokens |
| S-04 | No token reuse across calls | `run_pipeline` called twice → different `token_map` values |
| S-05 | Real names never in DIMACS | `caller_map` values are symbols only, never real meanings |

---

## Release Checklist

- [ ] All F-xx, Q-xx, S-xx criteria green
- [ ] CI passes on Python 3.10, 3.11, 3.12
- [ ] CHANGELOG.md updated
- [ ] `version` bumped in `pyproject.toml`
- [ ] `git tag v0.x.0` created and pushed
