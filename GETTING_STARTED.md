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
git clone https://github.com/flashesofbrilliance/blindsat.git
cd blindsat
pip install -e .[dev]
```

---

## Step 2 — Run an Example (Mock Mode)

No API key needed.

```bash
python examples/access_control.py
```

Expected output:

```
--- Pipeline Result ---
SAT:         SAT
Verified:    True
Parse error: False
Decoded:     {'user_is_admin': True, 'has_mfa': False, ...}
```

---

## Step 3 — Run the Test Suite

```bash
make test          # all tests
make coverage      # pytest + coverage report (target: ≥90%)
make lint          # ruff style check
```

---

## Step 4 — Wire in a Real LLM

`llm_call_fn` signature: `(system: str, user: str) -> str`.
Both arguments are positional strings — system prompt first, user message second.

### OpenAI

```python
from openai import OpenAI
from sat_private import run_pipeline

client = OpenAI()  # reads OPENAI_API_KEY from environment

def openai_call(system: str, user: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0,
    )
    return response.choices[0].message.content

result = run_pipeline(
    formula_str='(A | B) & (C | D) & (~A | ~D) & (B | C)',
    real_var_meanings={
        'A': 'user_is_admin', 'B': 'has_mfa',
        'C': 'is_weekday',    'D': 'request_from_vpn',
    },
    llm_call_fn=openai_call,
)
print(result)
```

### Anthropic

```python
import anthropic
from sat_private import run_pipeline

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

def anthropic_call(system: str, user: str) -> str:
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text

result = run_pipeline(
    formula_str='(A | B) & (C | D) & (~A | ~D) & (B | C)',
    real_var_meanings={
        'A': 'user_is_admin', 'B': 'has_mfa',
        'C': 'is_weekday',    'D': 'request_from_vpn',
    },
    llm_call_fn=anthropic_call,
)
print(result)
```

---

## Step 5 — Understand the Result Object

```python
{
    'sat_result'      : 'SAT',      # 'SAT' | 'UNSAT' | None (dry run / parse error)
    'verified'        : True,       # verifier confirmed the assignment
    'decoded'         : {'user_is_admin': True, 'has_mfa': False, ...},
    'parse_error'     : False,      # True if LLM returned unparseable output
    'raw_response'    : '...',      # raw LLM solver output
    'verify_response' : '...',      # raw LLM verifier output
    'prompt_ctx'      : {...},      # contains token_map / decode_map — CALLER SECRET
}
```

> **If `parse_error` is True:** the LLM returned output that contained neither
> `SAT` nor `UNSAT`. Retry the call; consider reducing temperature or increasing
> `max_tokens`. See `docs/FAILURE_MODES.md` for full diagnostics.

---

## Step 6 — DIMACS Cross-Check *(Optional)*

```python
result = run_pipeline(..., export_dimacs_path='formula.cnf')
```

```bash
minisat formula.cnf
rm formula.cnf   # covered by .gitignore; delete after use
```

---

## Step 7 — Write Your Own Formula

| Operator | Syntax | Example |
|---|---|---|
| AND | `&` | `A & B` |
| OR | `\|` | `A \| B` |
| NOT | `~` | `~A` |
| Implies | `>>` | `A >> B` |
| Grouping | `()` | `(A \| B) & C` |

Variable names must be single uppercase letters (A–Z) for this POC.
See `docs/NEXT_STEPS.md` N-16 for multi-char variable support.

---

## Environment Variables

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SAT_PRIVATE_DEBUG=0    # set to 1 to log full prompts (never in production)
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: sat_private` | Not installed | Run `pip install -e .` |
| `TypeError: mock_llm() takes 1 positional argument` | Old single-arg signature | Update to `def fn(system, user)` |
| `parse_error: True` | LLM returned prose instead of structured output | Retry at temperature=0; see `docs/FAILURE_MODES.md` |
| `verified: False` | LLM hallucinated an assignment | Retry; cross-check with MiniSAT |
| `decoded: {}` on a SAT result | LLM returned SAT but no token lines | Enable debug mode; check for response truncation |
| `ruff` lint errors in CI | Style violations | Run `make lint` locally before pushing |

---

## Next Steps

- [`docs/FAILURE_MODES.md`](docs/FAILURE_MODES.md) — failure taxonomy and mitigations
- [`docs/USE_CASES.md`](docs/USE_CASES.md) — three concrete applications
- [`docs/DEFINITION_OF_DONE.md`](docs/DEFINITION_OF_DONE.md) — contribution criteria
- [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md) — full backlog
