"""
tests/test_pipeline.py
Integration tests for run_pipeline — uses mock LLM, no API calls.
"""
import os, json, tempfile, pytest
from sat_private import generate_sat_prompt
from sat_private.pipeline import run_pipeline
from tests.conftest import EXPR_MEDIUM, REAL_VARS, EXPR_UNSAT


def _make_sat_response(ctx, sym_values: dict) -> str:
    tm = ctx["token_map"]
    lines = ["RESULT: SAT", "ASSIGNMENT:"]
    for sym, val in sym_values.items():
        if sym in tm:
            lines.append(f"{tm[sym]}: {'TRUE' if val else 'FALSE'}")
    return "\n".join(lines)


class TestDryRun:
    def test_dry_run_returns_none_result(self, capsys):
        r = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=None)
        assert r["sat_result"] is None
        assert r["verified"] is None
        assert r["decoded"] == {}
        out = capsys.readouterr().out
        assert "[DRY RUN]" in out


class TestSATWithMockLLM:
    def _build_mock(self, ctx, sym_values, verify_pass=True):
        sat_resp = _make_sat_response(ctx, sym_values)
        verify_resp = "VERIFICATION: PASS" if verify_pass else "VERIFICATION: FAIL\nUNSATISFIED_CLAUSES: 2"
        calls = [sat_resp, verify_resp]
        idx = [0]
        def mock(system, user):
            r = calls[idx[0] % len(calls)]
            idx[0] += 1
            return r
        return mock

    def test_sat_verified_pass_decodes_real_names(self):
        sym_vals = {"A": False, "B": True, "C": False, "D": True}
        ctx  = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        mock = self._build_mock(ctx, sym_vals, verify_pass=True)
        r = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=mock)
        assert r["sat_result"] == "SAT"
        assert r["verified"] is True
        assert isinstance(r["decoded"], dict)
        for real in REAL_VARS.values():
            assert real in r["decoded"]

    def test_sat_verified_fail_still_returns_result(self):
        sym_vals = {"A": True, "B": True, "C": True, "D": True}
        ctx  = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        mock = self._build_mock(ctx, sym_vals, verify_pass=False)
        r = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=mock)
        assert r["sat_result"] == "SAT"
        assert r["verified"] is False

    def test_llm_call_count_is_two(self):
        log = []
        ctx = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        sym_vals = {"A": False, "B": True, "C": False, "D": True}
        sat_resp = _make_sat_response(ctx, sym_vals)
        def mock(system, user):
            log.append(system[:30])
            if len(log) == 1:
                return sat_resp
            return "VERIFICATION: PASS"
        run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=mock)
        assert len(log) == 2


class TestUNSAT:
    def test_unsat_returns_empty_decoded(self):
        r = run_pipeline(EXPR_UNSAT, {"A": "flag_x"},
                         llm_call_fn=lambda s, u: "RESULT: UNSAT")
        assert r["sat_result"] == "UNSAT"
        assert r["decoded"] == {}
        assert r["verified"] is None


class TestDecoys:
    def test_decoy_count_in_header(self):
        r = run_pipeline(EXPR_MEDIUM, REAL_VARS,
                         llm_call_fn=None, decoy_count=3)
        user = r["prompt_ctx"]["user"]
        first_line = user.splitlines()[0]
        assert "7" in first_line


class TestFileExport:
    def test_dimacs_file_written(self):
        with tempfile.NamedTemporaryFile(suffix=".cnf", delete=False) as f:
            path = f.name
        run_pipeline(EXPR_MEDIUM, REAL_VARS,
                     llm_call_fn=None, export_dimacs_path=path)
        with open(path) as f:
            content = f.read()
        assert content.startswith("c DIMACS")
        assert "p cnf" in content
        os.unlink(path)

    def test_secret_state_file_written(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        run_pipeline(EXPR_MEDIUM, REAL_VARS,
                     llm_call_fn=None, export_secret_path=path)
        with open(path) as f:
            data = json.load(f)
        assert "int_to_symbol" in data
        assert "symbol_to_real" in data
        os.unlink(path)
