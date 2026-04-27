"""
tests/test_core.py
Unit tests for sat_private/core.py — no LLM calls needed.
"""
import re, pytest
from sat_private import encode_variables, generate_sat_prompt, generate_dimacs, decode_assignment
from tests.conftest import EXPR_MEDIUM, VAR_NAMES, EXPR_SIMPLE, EXPR_UNSAT


class TestEncodeVariables:
    def test_tokens_unique(self):
        tm, _ = encode_variables(VAR_NAMES)
        assert len(set(tm.values())) == len(VAR_NAMES)

    def test_hex_format_8_chars(self):
        tm, _ = encode_variables(VAR_NAMES * 3)
        for tok in list(set(tm.values())):
            assert re.fullmatch(r"[0-9A-F]{8}", tok), f"Bad format: {tok}"

    def test_decode_map_is_inverse(self):
        tm, dm = encode_variables(VAR_NAMES)
        assert {v: k for k, v in dm.items()} == tm

    def test_single_variable(self):
        tm, dm = encode_variables(["X"])
        assert len(tm) == 1
        assert dm[list(tm.values())[0]] == "X"

    def test_large_variable_set(self):
        names = [f"V{i}" for i in range(50)]
        tm, _ = encode_variables(names)
        assert len(set(tm.values())) == 50


class TestGenerateSatPrompt:
    def test_required_keys(self, medium_ctx):
        for key in ["system", "user", "token_map", "decode_map", "clauses"]:
            assert key in medium_ctx

    def test_no_symbol_leak(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        for sym in VAR_NAMES:
            assert sym not in ctx["user"], f"Symbol '{sym}' leaked into user message"

    def test_all_tokens_in_user(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        for tok in ctx["token_map"].values():
            assert tok in ctx["user"]

    def test_decoy_injection(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES, decoy_count=4)
        first_line = ctx["user"].splitlines()[0]
        assert "8" in first_line

    def test_unsat_formula_has_no_clauses(self):
        ctx = generate_sat_prompt(EXPR_UNSAT, ["A"])
        assert isinstance(ctx["clauses"], list)

    def test_simple_formula_clause_count(self):
        ctx = generate_sat_prompt("(A | B) & (~A | B)", ["A", "B"])
        assert len(ctx["clauses"]) == 2

    def test_tokens_different_across_calls(self):
        ctx1 = generate_sat_prompt(EXPR_SIMPLE, ["A", "B", "C"])
        ctx2 = generate_sat_prompt(EXPR_SIMPLE, ["A", "B", "C"])
        assert ctx1["token_map"] != ctx2["token_map"]


class TestGenerateDimacs:
    def test_header_format(self, medium_ctx):
        dimacs, _ = generate_dimacs(medium_ctx)
        lines = dimacs.splitlines()
        assert lines[0].startswith("c ")
        assert lines[1].startswith("p cnf ")

    def test_clause_lines_end_with_zero(self, medium_ctx):
        dimacs, _ = generate_dimacs(medium_ctx)
        for line in dimacs.splitlines()[2:]:
            assert line.endswith(" 0"), f"Clause line must end with ' 0': {line}"

    def test_var_count_matches(self, medium_ctx):
        dimacs, _ = generate_dimacs(medium_ctx)
        parts = dimacs.splitlines()[1].split()
        assert int(parts[2]) == len(VAR_NAMES)

    def test_caller_map_no_real_names(self, medium_ctx):
        _, caller_map = generate_dimacs(medium_ctx)
        for val in caller_map.values():
            assert val in VAR_NAMES

    def test_dimacs_integer_only(self, medium_ctx):
        dimacs, _ = generate_dimacs(medium_ctx)
        for line in dimacs.splitlines()[2:]:
            for token in line.split():
                assert re.fullmatch(r"-?\d+", token), f"Non-integer in DIMACS: {token}"


class TestDecodeAssignment:
    def _make_sat_response(self, ctx, values: dict) -> str:
        tm = ctx["token_map"]
        lines = ["RESULT: SAT", "ASSIGNMENT:"]
        for sym, val in values.items():
            lines.append(f"{tm[sym]}: {'TRUE' if val else 'FALSE'}")
        return "\n".join(lines)

    def test_full_roundtrip(self, medium_ctx):
        expected = {"A": False, "B": True, "C": False, "D": True}
        response = self._make_sat_response(medium_ctx, expected)
        decoded  = decode_assignment(response, medium_ctx["decode_map"])
        assert decoded == expected

    def test_unsat_returns_empty(self):
        assert decode_assignment("RESULT: UNSAT", {}) == {}

    def test_partial_assignment(self, simple_ctx):
        tm = simple_ctx["token_map"]
        partial_response = f"RESULT: SAT\nASSIGNMENT:\n{tm['A']}: TRUE\n{tm['B']}: FALSE"
        decoded = decode_assignment(partial_response, simple_ctx["decode_map"])
        assert decoded["A"] is True
        assert decoded["B"] is False

    def test_case_insensitive_true_false(self, simple_ctx):
        tm = simple_ctx["token_map"]
        r = f"RESULT: SAT\nASSIGNMENT:\n{tm['A']}: true\n{tm['B']}: false"
        decoded = decode_assignment(r, simple_ctx["decode_map"])
        assert decoded.get("A") is True
