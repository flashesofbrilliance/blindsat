"""
tests/test_core.py
Unit tests for sat_private/core.py -- no LLM calls needed.
"""
import re

from sat_private import decode_assignment, encode_variables, generate_dimacs, generate_sat_prompt
from tests.conftest import EXPR_MEDIUM, EXPR_SIMPLE, EXPR_UNSAT, VAR_NAMES


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
        # Symbols must not appear as standalone identifiers in the user message.
        # Single-char symbols (A-D) legitimately appear inside hex tokens and
        # header words like "sat", so we use a word-character boundary that
        # excludes any alphanumeric/underscore neighbour.
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        user = ctx["user"]
        for sym in VAR_NAMES:
            pattern = rf"(?<![A-Za-z0-9_]){re.escape(sym)}(?![A-Za-z0-9_])"
            assert not re.search(pattern, user), (
                f"Symbol '{sym}' leaked as standalone identifier in user message"
            )

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
        # SymPy simplify=True reduces (A|B)&(~A|B) -> B: assert >= 1
        ctx = generate_sat_prompt("(A | B) & (~A | B)", ["A", "B"])
        assert len(ctx["clauses"]) >= 1

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
    def _make_sat_response(self, ctx, values):
        tm = ctx["token_map"]
        NL = chr(10)
        lines = ["RESULT: SAT", "ASSIGNMENT:"]
        for sym, val in values.items():
            lines.append(tm[sym] + ": " + ("TRUE" if val else "FALSE"))
        return NL.join(lines)

    def test_full_roundtrip(self, medium_ctx):
        expected = {"A": False, "B": True, "C": False, "D": True}
        response = self._make_sat_response(medium_ctx, expected)
        decoded = decode_assignment(response, medium_ctx["decode_map"])
        assert decoded == expected

    def test_unsat_returns_empty(self):
        assert decode_assignment("RESULT: UNSAT", {}) == {}

    def test_partial_assignment(self, simple_ctx):
        tm = simple_ctx["token_map"]
        NL = chr(10)
        partial_response = NL.join([
            "RESULT: SAT", "ASSIGNMENT:",
            tm["A"] + ": TRUE",
            tm["B"] + ": FALSE",
        ])
        decoded = decode_assignment(partial_response, simple_ctx["decode_map"])
        assert decoded["A"] is True
        assert decoded["B"] is False

    def test_case_insensitive_true_false(self, simple_ctx):
        tm = simple_ctx["token_map"]
        NL = chr(10)
        r = NL.join([
            "RESULT: SAT", "ASSIGNMENT:",
            tm["A"] + ": true",
            tm["B"] + ": false",
        ])
        decoded = decode_assignment(r, simple_ctx["decode_map"])
        assert decoded.get("A") is True
