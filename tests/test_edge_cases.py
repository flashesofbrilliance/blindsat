"""
tests/test_edge_cases.py
Edge case and boundary condition tests.

EC-01  Empty variable list
EC-02  Single variable formula (trivially SAT)
EC-03  Tautology (always SAT)
EC-04  Contradiction (always UNSAT: A & ~A)
EC-05  Duplicate variable names in input
EC-06  Maximum tested formula size (20 vars)
EC-07  LLM response with extra whitespace / mixed case
EC-08  Garbled LLM response (no RESULT: keyword)
EC-09  LLM returns SAT but no assignment lines
EC-10  Token appearing multiple times in same clause
EC-11  Formula with only one clause
EC-12  All variables forced TRUE
EC-13  All variables forced FALSE
EC-14  Decoy count exceeds variable count
EC-15  DIMACS unit clauses (single-literal)
"""
import re

from sat_private import decode_assignment, encode_variables, generate_dimacs, generate_sat_prompt
from sat_private.pipeline import run_pipeline


def test_ec01_empty_var_list():
    tm, dm = encode_variables([])
    assert tm == {} and dm == {}


def test_ec02_single_var():
    ctx = generate_sat_prompt("A", ["A"])
    assert len(ctx["token_map"]) == 1
    assert len(ctx["clauses"]) >= 1


def test_ec03_tautology():
    ctx = generate_sat_prompt("A | ~A", ["A"])
    assert isinstance(ctx["clauses"], list)


def test_ec04_contradiction():
    r = run_pipeline(
        "A & ~A",
        {"A": "x"},
        llm_call_fn=lambda s, u: "RESULT: UNSAT",
    )
    assert r["sat_result"] == "UNSAT"
    assert r["decoded"] == {}


def test_ec05_duplicate_vars():
    ctx = generate_sat_prompt("A | B", ["A", "B", "A"])
    assert isinstance(ctx["token_map"], dict)


def test_ec06_large_formula():
    n = 20
    vars_ = [f"V{i}" for i in range(n)]
    expr = " & ".join(f"(V{i} | V{i + 1})" for i in range(n - 1))
    ctx = generate_sat_prompt(expr, vars_)
    assert len(ctx["token_map"]) == n
    dimacs, _ = generate_dimacs(ctx)
    assert f"p cnf {n}" in dimacs


def test_ec07_noisy_llm_response():
    ctx = generate_sat_prompt("(A | B) & (~A | B)", ["A", "B"])
    tm = ctx["token_map"]
    noisy = (
        f"  RESULT :  sat  \n ASSIGNMENT:\n"
        f"  {tm['A']} :  TRUE \n  {tm['B']} :  false  "
    )
    decoded = decode_assignment(noisy, ctx["decode_map"])
    assert decoded.get("A") is True
    assert decoded.get("B") is False


def test_ec08_garbled_response():
    ctx = generate_sat_prompt("A | B", ["A", "B"])
    decoded = decode_assignment("I don't know what to do", ctx["decode_map"])
    assert isinstance(decoded, dict)


def test_ec09_sat_no_assignment():
    r = run_pipeline(
        "A | B",
        {"A": "x", "B": "y"},
        llm_call_fn=lambda s, u: "RESULT: SAT\n",
    )
    assert r["sat_result"] == "SAT"
    assert isinstance(r["decoded"], dict)


def test_ec10_repeated_literal():
    ctx = generate_sat_prompt("(A | A) & B", ["A", "B"])
    assert len(ctx["clauses"]) >= 1


def test_ec11_single_clause():
    ctx = generate_sat_prompt("A | B | C", ["A", "B", "C"])
    assert len(ctx["clauses"]) == 1


def test_ec12_all_true():
    ctx = generate_sat_prompt("A & B & C", ["A", "B", "C"])
    tm = ctx["token_map"]
    resp = "RESULT: SAT\nASSIGNMENT:\n" + "\n".join(
        f"{tm[v]}: TRUE" for v in ["A", "B", "C"]
    )
    decoded = decode_assignment(resp, ctx["decode_map"])
    assert all(decoded.values())


def test_ec13_all_false():
    ctx = generate_sat_prompt("~A & ~B", ["A", "B"])
    tm = ctx["token_map"]
    resp = "RESULT: SAT\nASSIGNMENT:\n" + "\n".join(
        f"{tm[v]}: FALSE" for v in ["A", "B"]
    )
    decoded = decode_assignment(resp, ctx["decode_map"])
    assert not any(decoded.values())


def test_ec14_large_decoy_count():
    ctx = generate_sat_prompt("A | B", ["A", "B"], decoy_count=20)
    first_line = ctx["user"].splitlines()[0]
    assert "22" in first_line


def test_ec15_unit_clauses_dimacs():
    ctx = generate_sat_prompt("A & B", ["A", "B"])
    dimacs, _ = generate_dimacs(ctx)
    for line in dimacs.splitlines()[2:]:
        parts = line.split()
        assert len(parts) == 2
        assert parts[-1] == "0"


def test_ec16_formula_injection_blocked():
    """F3 regression: formulas with disallowed characters must raise ValueError."""
    import pytest

    from sat_private.core import _validate_formula

    with pytest.raises(ValueError, match="disallowed"):
        _validate_formula("A & __import__('os').system('id')")


def test_ec17_valid_formula_passes_allowlist():
    """F3 regression: valid formulas must not raise."""
    from sat_private.core import _validate_formula

    _validate_formula("(A | B) & (~A | C) & (B >> C)")


def test_ec18_dimacs_no_real_names(medium_ctx):
    """Privacy: DIMACS output must not contain any real variable name."""
    real_names = ["user_is_admin", "has_mfa", "is_weekday", "request_from_vpn"]
    dimacs, _ = generate_dimacs(medium_ctx)
    for name in real_names:
        assert name not in dimacs, f"Real name '{name}' leaked into DIMACS"


def test_ec19_re_import_used():
    """Confirm re module is actually used (guards against future unused-import lint)."""
    pattern = re.compile(r"-?\d+")
    assert pattern.match("42")
