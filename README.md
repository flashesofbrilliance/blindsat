# BlindSAT

> A private SAT pipeline: binary-encoded CNF + LLM solver + secret caller state.

The LLM **never sees your variable names**. It solves a structurally equivalent formula over opaque hex tokens. You hold the decode map.

---

## How It Works

```
Your formula  →  encode  →  opaque CNF  →  LLM solves  →  verify  →  decode  →  real meanings
(A | B) & ...    (private)   hex tokens     over tokens    2nd call   caller      user_is_admin=True
```

1. **Encode** — variable names replaced with random 8-char hex tokens per session.
2. **Prompt 1** — LLM receives token-only CNF, returns a satisfying assignment.
3. **Prompt 2** — A second LLM call verifies every clause evaluates to TRUE.
4. **DIMACS** — Standard `.cnf` export for ground-truth MiniSAT cross-check.
5. **Decode** — Caller maps tokens → symbols → real meanings. Never leaves your process.

📖 **New here? Start with [GETTING_STARTED.md](GETTING_STARTED.md)**

---

## Quick Start

```bash
git clone https://github.com/flashesofbrilliance/blindsat.git
cd blindsat
pip install -e .[dev]
python examples/access_control.py   # mock mode, no API key needed
```

To use a real LLM, see the [LLM wiring section in GETTING_STARTED.md](GETTING_STARTED.md#step-4--wire-in-a-real-llm).

---

## Project Structure

```
sat_private/          Core library (encode, prompts, DIMACS, decode, pipeline)
tests/                Unit, integration, and edge-case tests
docs/                 Definition of Done, user testing plan, use cases, next steps
examples/             Three runnable use cases (access control, feature flags, compliance)
notebooks/            Annotated Jupyter walkthrough
.github/workflows/    CI: pytest + coverage + security checks
```

---

## Testing

```bash
make test        # run all 46 tests (no API key needed)
make coverage    # pytest + coverage report (target ≥90%)
make lint        # ruff style check
```

---

## Use Cases

| # | Use Case | Example |
|---|---|---|
| UC-1 | Zero-knowledge access control policy evaluation | `examples/access_control.py` |
| UC-2 | Feature flag dependency validation | `examples/feature_flags.py` |
| UC-3 | Regulatory compliance rule satisfiability | `examples/compliance_rules.py` |
| UC-4 | Private configuration space exploration | — |
| UC-5 | AI-assisted propositional theorem proving | — |

See [`docs/USE_CASES.md`](docs/USE_CASES.md) for full detail.

---

## Security Guarantees

- Token map is ephemeral — regenerated every `run_pipeline` call.
- Real variable names never appear in prompts, DIMACS output, or logs.
- `.gitignore` blocks `formula.cnf` and `caller_secret_state.json`.
- CI includes a security job that scans CNF files and validates `.gitignore` coverage.

---

## Docs

- [GETTING_STARTED.md](GETTING_STARTED.md) ← **start here**
- [`docs/USE_CASES.md`](docs/USE_CASES.md)
- [`docs/DEFINITION_OF_DONE.md`](docs/DEFINITION_OF_DONE.md)
- [`docs/USER_TESTING.md`](docs/USER_TESTING.md)
- [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md)
- [`CHANGELOG.md`](CHANGELOG.md)
