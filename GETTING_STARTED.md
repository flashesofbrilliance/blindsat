# Getting Started — sat_private

This guide takes you from a fresh clone to a working pipeline in under 10 minutes.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Check with `python --version` |
| pip | 23+ | Check with `pip --version` |
| An LLM API key | — | OpenAI or Anthropic (optional for mock runs) |
| MiniSAT *(optional)* | any | For DIMACS cross-validation only |

---

## Step 1 — Clone and Install

```bash
git clone https://github.com/flashesofbrilliance/sat-private.git
cd sat-private
pip install -e .[dev]
```

This installs `sat_private` as an editable package plus dev dependencies (`pytest`, `ruff`, `pytest-cov`).

---

## Step 2 — Run an Example (Mock Mode)

No API key needed. The example uses a placeholder `mock_llm` function.

```bash
python examples/access_control.py
```

Expected output:

```
--- Pipeline Result ---
SAT:      None          # None because mock_llm returns a placeholder
Verified: None
Decoded:  {}
Meanings: {}
```

This confirms the pipeline wiring is correct. To get a real SAT result, wire in a live LLM (Step 4).

---

## Step 3 — Run the Test Suite

```bash
make test          # all 46 tests
make coverage      # same, with coverage report (target: ≥90%)
make lint          # ruff style check
```

All tests use mock LLM responses — no API key required.

---

## Step 4 — Wire in a Real LLM

The pipeline accepts any callable with signature `(prompt: str) -> str`.
Pass it as `llm_call_fn`.

### OpenAI

```python
from openai import OpenAI
from sat_private import run_pipeline

client = OpenAI()  # reads OPENAI_API_KEY from environment

def openai_call(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise SAT solver. Follow instructions exactly."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content

REAL_VARS = {
    'A': 'user_is_admin',
    'B': 'has_mfa',
    'C': 'is_weekday',
    'D': 'request_from_vpn',
}

result = run_pipeline(
    formula_str='(A | B) & (C | D) & (~A | ~D) & (B | C)',
    real_var_meanings=REAL_VARS,
    llm_call_fn=openai_call,
)

print(result)
```

### Anthropic

```python
import anthropic
from sat_private import run_pipeline

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

def anthropic_call(prompt: str) -> str:
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text

result = run_pipeline(
    formula_str='(A | B) & (C | D) & (~A | ~D) & (B | C)',
    real_var_meanings={'A': 'user_is_admin', 'B': 'has_mfa',
                       'C': 'is_weekday', 'D': 'request_from_vpn'},
    llm_call_fn=anthropic_call,
)

print(result)
```

---

## Step 5 — Understand the Result Object

`run_pipeline` returns a dict:

```python
{
    'satisfiable': True,           # or False if UNSAT
    'verified': True,              # verifier confirmed the assignment
    'raw_assignment': {            # LLM output before decode
        'A1B2C3D4': True,
        'E5F6G7H8': False,
        ...
    },
    'decoded': {                   # symbol names → bool
        'A': True,
        'B': False,
        ...
    },
    'real_meanings': {             # real variable names → bool  ← what you actually want
        'user_is_admin': True,
        'has_mfa': False,
        ...
    },
    'dimacs': 'p cnf 4 4\n1 2 0\n...',  # DIMACS string for MiniSAT cross-check
}
```

The only field that contains real meanings is `real_meanings` — and it is computed **locally** by the caller. It never touches the LLM.

---

## Step 6 — Cross-Check with MiniSAT *(Optional)*

If you have MiniSAT installed:

```python
result = run_pipeline(...)

with open('formula.cnf', 'w') as f:
    f.write(result['dimacs'])
```

```bash
minisat formula.cnf
# SAT / UNSAT  ← should agree with result['satisfiable']
rm formula.cnf   # formula.cnf is .gitignored; delete after use
```

---

## Step 7 — Write Your Own Formula

Formulas use standard propositional logic syntax via SymPy:

| Operator | Syntax | Example |
|---|---|---|
| AND | `&` | `A & B` |
| OR | `\|` | `A \| B` |
| NOT | `~` | `~A` |
| Implies | `>>` | `A >> B` (equivalent to `~A \| B`) |
| Grouping | `()` | `(A \| B) & C` |

Variable names must be single uppercase letters (A–Z) for this POC.
See `docs/NEXT_STEPS.md` N-16 for the roadmap to multi-char and first-order variables.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
# edit .env with your keys
```

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SAT_PRIVATE_DEBUG=0    # set to 1 to log full prompts (never in production)
```

> **Never commit `.env`.** It is covered by `.gitignore`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: sat_private` | Not installed | Run `pip install -e .` |
| `verified: False` | LLM hallucinated an assignment | Retry; consider lower temperature |
| `satisfiable: False` on a valid formula | LLM returned UNSAT incorrectly | Cross-check with MiniSAT |
| `KeyError` in decode | LLM returned an unknown token | Enable debug mode; check for prompt truncation |
| `ruff` lint errors in CI | Style violations in source | Run `make lint` locally and fix before pushing |

---

## Next Steps

- Read [`docs/USE_CASES.md`](docs/USE_CASES.md) for three concrete applications.
- Read [`docs/DEFINITION_OF_DONE.md`](docs/DEFINITION_OF_DONE.md) for contribution criteria.
- Check [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md) for the full backlog.
- Open the annotated notebook: `jupyter notebook notebooks/`
