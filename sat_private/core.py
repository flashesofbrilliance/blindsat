"""
sat_private/core.py
-------------------
Pure functions: encode, prompt generation, DIMACS export, decode.
No I/O, no LLM calls — fully testable in isolation.
"""
from __future__ import annotations
import re
import secrets
from typing import Any
from sympy.logic.boolalg import to_cnf, And, Or, Not, BooleanFalse, BooleanTrue
from sympy import symbols as sym_symbols


# ──────────────────────────────────────────────────────────────────[...]
# SECTION 1 — Variable encoding
# ──────────────────────────────────────────────────────────────────[...]

def encode_variables(var_names: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Assign a unique random 8-char uppercase hex token to each symbolic variable.

    The returned maps are the *caller's secret state* — they must never be
    included in any prompt sent to an LLM.

    Parameters
    ----------
    var_names : list[str]
        Symbolic variable names used in the formula (e.g. ["A", "B", "C"]).

    Returns
    -------
    token_map  : dict  symbol  -> hex_token   (A -> "CC01DC8C")
    decode_map : dict  hex_token -> symbol    (inverse)
    """
    token_map: dict[str, str] = {}
    seen: set[str] = set()
    for name in var_names:
        while True:
            token = secrets.token_hex(4).upper()
            if token not in seen:
                seen.add(token)
                token_map[name] = token
                break
    decode_map = {v: k for k, v in token_map.items()}
    return token_map, decode_map


# ──────────────────────────────────────────────────────────────────[...]
# SECTION 2 — CNF conversion helpers
# ──────────────────────────────────────────────────────────────────[...]

# Allowlist: only permit these characters in formula strings.
# Prevents injection via crafted formula input (F3 mitigation).
_FORMULA_ALLOWLIST = re.compile(r'^[A-Za-z0-9 |&~()>
	-]+$')


def _validate_formula(expr_str: str) -> None:
    """Raise ValueError if expr_str contains characters outside the allowlist."""
    if not _FORMULA_ALLOWLIST.match(expr_str):
        raise ValueError(
            f"Formula contains disallowed characters. "
            f"Only A-Z, a-z, 0-9, spaces, and |&~()>
	- are permitted. "
            f"Got: {expr_str!r}"
        )


def _parse_expr(expr_str: str, var_names: list[str]):
    """Parse a boolean expression string into a SymPy CNF object."""
    _validate_formula(expr_str)  # F3: allowlist gate before eval
    syms = sym_symbols(" ".join(var_names))
    sym_map = dict(zip(var_names, syms if hasattr(syms, "__iter__") else [syms]))
    safe = expr_str
    for name in sorted(var_names, key=len, reverse=True):
        safe = re.sub(rf"\b{re.escape(name)}\b", f"sym_map['{name}']", safe)
    expr = eval(safe, {"sym_map": sym_map, "__builtins__": {{}}})  # nosec B307
    return to_cnf(expr, simplify=True), sym_map


def _clauses_from_cnf(cnf_expr) -> list[list[str]]:
    """Extract clause list (list of lists of literal strings) from SymPy CNF."""
    if isinstance(cnf_expr, (BooleanFalse, BooleanTrue)):
        return []
    top = cnf_expr if isinstance(cnf_expr, And) else And(cnf_expr)
    clauses = []
    for clause in top.args if isinstance(top, And) else [top]:
        lits = clause.args if isinstance(clause, Or) else [clause]
        literals = []
        for lit in lits:
            if isinstance(lit, Not):
                literals.append(f"-{lit.args[0].name}")
            else:
                literals.append(lit.name)
        clauses.append(literals)
    return clauses


# ──────────────────────────────────────────────────────────────────[...]
# SECTION 3 — Prompt generation
# ──────────────────────────────────────────────────────────────────[...]

_SOLVER_SYSTEM = """
You are a pure structural SAT solver. You receive a SAT problem encoded with
opaque hex tokens — the tokens have no semantic meaning. Your only job is to
find a satisfying assignment or prove UNSAT.

RULES:
1. Treat every token as an abstract symbol with no meaning.
2. Apply unit propagation and DPLL where helpful.
3. Return EXACTLY this format and nothing else:

RESULT: SAT
ASSIGNMENT:
<TOKEN>: TRUE|FALSE
...

or:

RESULT: UNSAT

Do not explain. Do not add commentary. Tokens are case-sensitive."""

_VERIFIER_SYSTEM = """
You are a SAT assignment verifier. Given a set of clauses and an assignment,
check every clause. Return EXACTLY one of:

VERIFICATION: PASS

or:

VERIFICATION: FAIL
UNSATISFIED_CLAUSES: <comma-separated clause numbers>

No commentary. Clause numbering starts at 1."""


def generate_sat_prompt(
    expr_str: str,
    var_names: list[str],
    *,
    decoy_count: int = 0,
) -> dict[str, Any]:
    """
    Build the fully-encoded SAT solver prompt.

    Parameters
    ----------
    expr_str    : Boolean expression using var_names (e.g. "(A | B) & (~A | C)")
    var_names   : List of variable names appearing in expr_str
    decoy_count : Number of extra decoy tokens to inject (default 0).
                  Decoys add noise that makes problem-size inference harder.

    Returns
    -------
    dict with keys:
        system      - LLM system prompt (str)
        user        - LLM user message (str) — safe to send; contains only hex
        token_map   - {symbol: hex_token}  — CALLER SECRET
        decode_map  - {hex_token: symbol}  — CALLER SECRET
        clauses     - raw clause list (list[list[str]] of symbols)
    """
    token_map, decode_map = encode_variables(var_names)
    cnf, _ = _parse_expr(expr_str, var_names)
    clauses = _clauses_from_cnf(cnf)

    encoded_clauses: list[list[str]] = []
    for clause in clauses:
        enc = []
        for lit in clause:
            neg = lit.startswith("-")
            sym = lit.lstrip("-")
            enc.append(f"{'~' if neg else ''}{token_map[sym]}")
        encoded_clauses.append(enc)

    all_tokens = list(token_map.values())
    decoys: list[str] = []
    for _ in range(decoy_count):
        while True:
            d = secrets.token_hex(4).upper()
            if d not in decode_map and d not in decoys:
                decoys.append(d)
                break

    header = f"p sat {len(var_names) + decoy_count} {len(encoded_clauses)}\n\n"
    var_block = "VARS:\n" + "\n".join(all_tokens + decoys) + "\n\n"
    clause_block = "CLAUSES:\n" + "\n".join(
        "(" + " | ".join(lits) + ")" for lits in encoded_clauses
    )
    user_msg = header + var_block + clause_block

    return {
        "system": _SOLVER_SYSTEM,
        "user": user_msg,
        "token_map": token_map,
        "decode_map": decode_map,
        "clauses": clauses,
    }


def generate_verify_prompt(
    prompt_ctx: dict[str, Any],
    assignment: dict[str, bool],
) -> dict[str, Any]:
    """
    Build the independent verifier prompt.

    Parameters
    ----------
    prompt_ctx : dict returned by generate_sat_prompt
    assignment : {hex_token: bool} — the LLM's proposed assignment

    Returns
    -------
    dict with keys: system (str), user (str)
    """
    token_map = prompt_ctx["token_map"]
    clauses = prompt_ctx["clauses"]

    assign_lines = "\n".join(
        f"{token_map[sym]}: {'TRUE' if val else 'FALSE'}"
        for sym, val in {s: assignment.get(token_map[s], False)
                         for s in token_map}.items()
    )
    clause_lines = "\n".join(
        f"{i+1}. (" + " | ".join(
            f"{'~' if lit.startswith('-') else ''}{token_map[lit.lstrip('-')]}"
            for lit in clause
        ) + ")"
        for i, clause in enumerate(clauses)
    )

    user_msg = f"CLAUSES:\n{clause_lines}\n\nASSIGNMENT:\n{assign_lines}"
    return {"system": _VERIFIER_SYSTEM, "user": user_msg}


# ──────────────────────────────────────────────────────────────────[...]
# SECTION 4 — DIMACS export
# ──────────────────────────────────────────────────────────────────[...] 

def generate_dimacs(
    prompt_ctx: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    """
    Export the formula as standard DIMACS CNF (compatible with MiniSAT/Glucose).

    The integer->symbol mapping is returned separately as caller secret state —
it must NOT be written into the .cnf file.

    Parameters
    ----------
    prompt_ctx : dict returned by generate_sat_prompt

    Returns
    -------
    dimacs_str : str  — DIMACS CNF text; safe to write to formula.cnf
    caller_map : dict — {int_str: symbol}  — CALLER SECRET, never in .cnf

    Security note
    -------------
    Write the returned dimacs_str to a temp file only. Delete immediately after
    use. Never commit formula.cnf — it is covered by .gitignore.
    """
    var_names = list(prompt_ctx["token_map"].keys())
    int_map   = {name: i + 1 for i, name in enumerate(var_names)}
    caller_map = {str(v): k for k, v in int_map.items()}

    clauses = prompt_ctx["clauses"]
    lines = [
        "c DIMACS CNF — variable map held by caller (secret state)",
        f"p cnf {len(var_names)} {len(clauses)}",
    ]
    for clause in clauses:
        ints = []
        for lit in clause:
            neg = lit.startswith("-")
            sym = lit.lstrip("-")
            n = int_map[sym]
            ints.append(str(-n if neg else n))
        lines.append(" ".join(ints) + " 0")

    return "\n".join(lines), caller_map


# ──────────────────────────────────────────────────────────────────[...]
# SECTION 5 — Decode
# ──────────────────────────────────────────────────────────────────[...] 

def decode_assignment(
    llm_response: str,
    decode_map: dict[str, str],
) -> dict[str, bool]:
    """
    Parse LLM SAT response and decode hex tokens back to symbolic names.

    This is the single canonical decode path. pipeline.py routes through
    here — never re-implements token parsing inline.

    Parameters
    ----------
    llm_response : Raw text returned by the LLM
    decode_map   : {hex_token: symbol} — the caller's secret inverse map

    Returns
    -------
    dict {symbol: bool} — empty dict if UNSAT or parse failure
    """
    if "UNSAT" in llm_response.upper():
        return {}
    result: dict[str, bool] = {}
    for line in llm_response.splitlines():
        for token, sym in decode_map.items():
            if token in line:
                val = "TRUE" in line.upper()
                result[sym] = val
    return result
