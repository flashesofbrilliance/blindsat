# Failure Modes — sat_private

> How we found them, what they do, and how to handle them.

This document catalogs every known failure mode, its root cause, detection method,
and recommended mitigation. It is a living document: add entries whenever a new
failure mode is discovered in testing, production, or red-team review.

---

## How We Found These

All failure modes below were identified during an **ARCS gauntlet review** of the
initial POC codebase on 2026-04-27. The gauntlet runs five lenses simultaneously:

| Lens | What it looks for |
|---|---|
| **L1 Kintsugi Scan** | Fractures — places where the seam between components is visibly weak |
| **L2 Diamond (NULL/OM/UNDEFINED)** | What’s provably absent, assumed, or unknown |
| **L3 BAR (Before/After/Risk)** | What breaks if we don’t fix it, and how badly |
| **L4 KKL (Key Leverage)** | Which three moves fix 80% of surface area |
| **L5 True North** | Single most important next action |

The gauntlet operates on the live codebase — `core.py`, `pipeline.py`, and the
test suite — not on a spec. Findings are graded by risk and ordered by leverage.

---

## FM-01 · `llm_call_fn` Signature Mismatch *(Fixed in v0.1.1)*

**Lens that caught it:** L1 Kintsugi — seam between `pipeline.py` and `examples/`

**What happened:**
`pipeline.py` called `llm_call_fn(system, user)` (two args) while every example
and `GETTING_STARTED.md` defined `mock_llm(prompt: str)` (one arg). A user
following the docs exactly would receive `TypeError: mock_llm() takes 1 positional
argument but 2 were given` on their first real LLM call.

**Why it happened:**
The pipeline was written with the two-arg form (matching OpenAI’s chat interface)
before the examples were written. The examples were written for simplicity without
checking the pipeline’s call site.

**Detection:** `TypeError` at runtime on first live LLM call. Would not appear in
unit tests because mocks used lambdas with `*args`.

**Fix:** Standardised `llm_call_fn` to `(system: str, user: str) -> str` everywhere.
Updated all examples, `GETTING_STARTED.md`, and the type annotation in `run_pipeline`.

**Prevention going forward:** Any function accepted as a callback must have its
signature asserted in at least one integration test.

---

## FM-02 · Dual Decode Paths *(Fixed in v0.1.1)*

**Lens that caught it:** L1 Kintsugi — structural duplication

**What happened:**
`pipeline.py` contained an inline re-implementation of the token-parsing logic
that also exists in `core.decode_assignment`. Two code paths doing the same thing
can silently drift apart as either evolves.

**Why it happened:**
`pipeline.py` was written before the `decode_assignment` function in `core.py`
was fully stabilised. The inline version was never removed.

**Detection:** Code review / structural audit. Would only surface as a bug after
one path was modified without updating the other.

**Fix:** `pipeline.py` now calls `core.decode_assignment` exclusively.

**Prevention:** Single decode path enforced by design. Any change to decode logic
has exactly one place to land.

---

## FM-03 · `eval()` Partial Sandbox *(Open — tracked as N-03a)*

**Lens that caught it:** L1 Kintsugi — security surface

**What happened:**
`core._parse_expr` uses `eval(safe, {"sym_map": sym_map, "__builtins__": {}})`.
Suppressing `__builtins__` in Python does not constitute a real security boundary:
a crafted input can still access `object.__subclasses__()` and escape the sandbox.

**Why it happened:**
The `eval` approach is the simplest way to reuse Python’s operator syntax for
boolean expressions. The sandbox was added as a precaution but is insufficient.

**Risk level:** Low in the current POC context (formula strings are caller-supplied,
not user-supplied). Becomes high if `expr_str` ever accepts untrusted external input.

**Mitigations (current):**
- `expr_str` is caller-controlled; callers are trusted in v0.1.
- Input is re-written to reference only `sym_map` keys before eval.

**Recommended fix (N-03a):** Replace `eval` with a proper parser:
- Option A: Use SymPy’s `parse_expr` with `local_dict` and `transformations`.
- Option B: Write a small recursive-descent parser for the four operators.

**Do not accept untrusted `expr_str` input until this is resolved.**

---

## FM-04 · Secret Export to Disk *(Fixed in v0.1.1)*

**Lens that caught it:** L1 Kintsugi — privacy guarantee violation

**What happened:**
`run_pipeline` accepted an `export_secret_path` parameter that wrote the full
decode map *and* real variable meanings to a JSON file on disk. This silently
violates the core privacy guarantee of the pipeline.

**Why it happened:**
Added as a debugging convenience during early development. The warning comment
existed but the parameter remained opt-in-unsafe: callers could trigger it
accidentally.

**Fix:** Parameter removed entirely. `export_dimacs_path` is retained because
DIMACS output contains no variable names and is safe to export.

**If you need cross-process secret persistence:**
Encrypt the `prompt_ctx["decode_map"]` and `real_var_meanings` before any storage
operation. Never write them in plaintext.

---

## FM-05 · Silent False-Positive SAT on Parse Failure *(Fixed in v0.1.1)*

**Lens that caught it:** L2 Diamond (UNDEFINED) — unhandled LLM output states

**What happened:**
When an LLM returned a response containing neither `SAT` nor `UNSAT` (e.g. an
apology, a refusal, or a malformed output), the pipeline set `sat_result = "SAT"`
because the `UNSAT` string was not present. The caller received
`{"sat_result": "SAT", "decoded": {}}` with no indication that anything was wrong.

**Why it happened:**
The original sat/unsat detection was a single condition:
```python
sat_result = "UNSAT" if "UNSAT" in upper else "SAT"
```
This is a closed-world assumption that breaks on any response outside the expected
format.

**Fix:** Explicit three-way parse:
```python
is_sat   = "SAT" in upper and "UNSAT" not in upper
is_unsat = "UNSAT" in upper
if not is_sat and not is_unsat:
    return {..., "sat_result": None, "parse_error": True}
```

Callers should check `result["parse_error"]` before trusting `sat_result`.

**Prevention:** Any new LLM response parser must define all three states:
expected-positive, expected-negative, and unparseable. Tests EC-08 and EC-09
cover this.

---

## FM-06 · Single-Literal Clause Handling *(Monitored — EC-15 covers)*

**Lens that caught it:** L2 Diamond (OM) — assumed but unconfirmed

**What happened:**
Formulas that reduce to a single unit clause (e.g. `"A"`, `"A & B"` after
simplification) go through a SymPy `And(cnf_expr)` wrapper. This is believed
correct but has edge cases depending on SymPy’s internal representation of
single-literal `And` nodes.

**Risk level:** Low. EC-02 and EC-15 cover the known cases. No failures observed.

**Status:** Monitored. If SymPy changes its internal representation in a future
release, `_clauses_from_cnf` may need updating.

---

## Adding New Entries

When a new failure mode is found, add an entry with:

```markdown
## FM-NN · Short Title *(Status)*

**Lens that caught it:**
**What happened:**
**Why it happened:**
**Risk level:**
**Fix / Mitigation:**
**Prevention:**
```

Tag the entry with the ARCS lens that caught it. This builds a corpus over time
that improves the sensitivity of future gauntlet runs.
