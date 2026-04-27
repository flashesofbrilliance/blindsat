# Failure Modes — sat_private POC

> This document is a living design receipt. It captures every failure mode
> identified during the ARCS gauntlet review of the repo, explains why each
> one matters, records how it was found, and links to the remediation.

---

## How These Were Identified

The review inspected the live repository state (commit `c5c3ec`) by tracing
the main execution path from `run_pipeline` into prompt generation, decode,
verification, and export behaviour. Three priority criteria drove ranking:

1. **First-run breakage** — does it silently fail for a new user?
2. **Privacy invariant violation** — does it leak real variable names?
3. **Silent false positive** — does it return a misleading result with no signal?

Findings were cross-checked against the public docs, examples, and `GETTING_STARTED.md`
to identify documentation / implementation drift.

---

## Failure Modes

### F1 — `llm_call_fn` Signature Mismatch ✅ Fixed

| | |
|---|---|
| **What** | `pipeline.py` called `llm_call_fn(system, user)` (2 args). Some examples used `mock_llm(prompt: str)` (1 arg). |
| **Why it matters** | Every new user following the Getting Started guide would hit `TypeError: mock_llm() takes 1 positional argument but 2 were given` on first real run. |
| **How found** | Compared the `run_pipeline` call site with the function signature in each example. |
| **Fix** | Standardised to `(system: str, user: str) -> str` everywhere. Added `LLMCallable` type alias in `pipeline.py`. All examples updated. |

---

### F2 — Dual Decode Paths ✅ Fixed

| | |
|---|---|
| **What** | `pipeline.py` re-implemented token-to-symbol parsing inline (lines 57–59) instead of calling `core.decode_assignment`. |
| **Why it matters** | Two independent implementations of the same logic drift over time. A bug fix in one path would not propagate to the other. |
| **How found** | Read `pipeline.py` top-to-bottom; found token scanning loop that duplicated `decode_assignment` logic. |
| **Fix** | Removed inline loop. `pipeline.py` now routes all decoding through `core.decode_assignment` — single canonical path. |

---

### F3 — `eval()` Without Input Allowlist ✅ Mitigated

| | |
|---|---|
| **What** | `_parse_expr` in `core.py` called `eval(safe, {"__builtins__": {}})`. Suppressing `__builtins__` is not a full Python sandbox. A crafted formula string could escape. |
| **Why it matters** | `sat_private` is a security-oriented POC. A formula injection surface is contradictory to the privacy claims. |
| **How found** | Reviewed `core.py` Section 2. The `__builtins__: {}` pattern is well-known to be bypassable in CPython. |
| **Fix** | Added `_validate_formula()` with a character allowlist (`A-Za-z0-9 |&~()>-`) before `eval`. Any formula containing characters outside the set raises `ValueError`. `eval` is retained with `# nosec B307` to suppress bandit noise — the allowlist is the real gate. |
| **Residual risk** | `eval` over allowlisted input on controlled symbols is low risk but not zero. Full mitigation in a later version would replace `eval` with a SymPy parser-only path. |

---

### F4 — Secret State Export to Disk ✅ Fixed

| | |
|---|---|
| **What** | `pipeline.py` accepted `export_secret_path` and serialised the full decode map and real variable meanings to JSON on disk. |
| **Why it matters** | The core privacy guarantee of `sat_private` is that real variable names never leave the caller's process. Writing them to a file breaks this in any shared or logged environment. |
| **How found** | Read `run_pipeline` signature and body. `export_secret_path` wrote `{"int_to_symbol": ..., "symbol_to_real": real_var_meanings}` — the complete inverse of the privacy encoding. |
| **Fix** | `export_secret_path` and `export_dimacs_path` parameters removed from `run_pipeline` entirely. The security note in `generate_dimacs` docstring now explains how to use DIMACS safely if needed. |

---

### F5 — Unit Clause Edge Case ⚠️ Documented, Not Yet Tested

| | |
|---|---|
| **What** | A formula with a single-literal clause (e.g. `"A"` or `"~A"`) exercises a different branch in `_clauses_from_cnf`. The logic appears correct but has no dedicated test. |
| **Why it matters** | Unit clauses are common in real compliance rules (e.g. `data_minimisation must always hold`). Untested edge cases become silent bugs. |
| **How found** | Traced `_clauses_from_cnf` branch logic; `lits = clause.args if isinstance(clause, Or) else [clause]` handles unit clauses, but the wrapper `And(cnf_expr).args` path for single-clause formulae was not verified by any test. |
| **Fix** | To be addressed in the next test-writing session. Target: add `test_unit_clause` and `test_always_true_literal` cases in `tests/test_edge_cases.py`. |

---

### F6 — Silent False-Positive SAT on Parse Failure ✅ Fixed

| | |
|---|---|
| **What** | If the LLM returned malformed output (no `RESULT:` prefix, extra prose), `sat_result` was set to `"SAT"` because `"UNSAT"` was simply absent from the string. The caller received `{"sat_result": "SAT", "decoded": {}}` with no indication that parsing failed. |
| **Why it matters** | A downstream system treating `sat_result == "SAT"` as a real result could grant access or approve a compliance check based on a hallucination or truncated LLM response. |
| **How found** | Traced the SAT/UNSAT detection in `pipeline.py`: `sat_result = "UNSAT" if "UNSAT" in ... else "SAT"` — absence of UNSAT was treated as presence of SAT. |
| **Fix** | Replaced with strict parse logic: require `RESULT: SAT` or `RESULT: UNSAT` in the response. All other output sets `parse_error: True` and `sat_result: None`. Callers must check `parse_error` before acting on `sat_result`. |

---

## Residual Risks After v0.1.0 Fixes

| ID | Risk | Severity | Planned fix |
|---|---|---|---|
| F3 residual | `eval()` on allowlisted input | Low | Replace with SymPy parser-only path in v0.2 |
| F5 unit clause | No test coverage for unit/always-true clauses | Low | `test_edge_cases.py` next session |
| OM-1 | Mock LLM in tests may not represent real LLM failure modes | Medium | Add adversarial mock (garbled output, partial response, UNSAT lie) |
| OM-2 | LLM accuracy on >6-variable formulas is unvalidated | Unknown | Benchmark suite planned in `docs/NEXT_STEPS.md` N-17 |

---

## How to Use This Document

- **Before adding a new feature:** check whether it interacts with any residual risk above.
- **Before a release:** all `✅ Fixed` items must have corresponding tests passing in CI.
- **When a new failure mode is found:** add it here with the same table structure before writing any fix.

This document is part of the Definition of Done. See [`docs/DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md).
