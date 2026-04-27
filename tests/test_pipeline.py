"""
tests/test_pipeline.py
Integration tests for sat_private/pipeline.py — uses mock LLM, no real API calls.
"""
import pytest
from sat_private import (
    generate_sat_prompt,
    generate_dimacs,
    run_pipeline,
)
from tests.conftest import EXPR_MEDIUM, REAL_VARS, VAR_NAMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sat_response(ctx, values: dict) -> str:
    """Build a well-formed RESULT: SAT response for the given symbol->bool map."""
    tm = ctx["token_map"]
    lines = ["RESULT: SAT", "ASSIGNMENT:"]
    for sym, val in values.items():
        lines.append(f"{tm[sym]}: {'TRUE' if val else 'FALSE'}")
    return "\n".join(lines)


def _make_mock_llm(ctx, sym_values: dict, verify_pass: bool = True):
    """Return a 2-arg mock LLM that answers SAT then VERIFICATION: PASS/FAIL."""
    sat_response    = _make_sat_response(ctx, sym_values)
    verify_response = "VERIFICATION: PASS" if verify_pass else "VERIFICATION: FAIL\nUNSATISFIED_CLAUSES: 1"
    responses = [sat_response, verify_response]
    idx = [0]

    def mock(system: str, user: str) -> str:
        r = responses[idx[0] % len(responses)]
        idx[0] += 1
        return r

    return mock


# ---------------------------------------------------------------------------
# TestPipelineSat — happy path
# ---------------------------------------------------------------------------

class TestPipelineSat:
    def test_sat_result_key(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        llm = _make_mock_llm(ctx, {"A": True, "B": False, "C": True, "D": False})
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert result["sat_result"] == "SAT"

    def test_verified_true_on_pass(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        llm = _make_mock_llm(ctx, {"A": True, "B": False, "C": True, "D": False}, verify_pass=True)
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert result["verified"] is True

    def test_decoded_contains_real_names(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        llm = _make_mock_llm(ctx, {"A": True, "B": False, "C": True, "D": False})
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert set(result["decoded"].keys()) <= set(REAL_VARS.values())

    def test_parse_error_false_on_clean_response(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        llm = _make_mock_llm(ctx, {"A": True, "B": False, "C": True, "D": False})
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert result["parse_error"] is False

    def test_result_keys_present(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)
        llm = _make_mock_llm(ctx, {"A": True, "B": False, "C": True, "D": False})
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        for key in ["sat_result", "verified", "parse_error", "decoded",
                    "raw_response", "verify_response", "prompt_ctx"]:
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# TestPipelineUnsat
# ---------------------------------------------------------------------------

class TestPipelineUnsat:
    def test_unsat_result(self):
        result = run_pipeline(
            "A & ~A", {"A": "always_false"},
            llm_call_fn=lambda s, u: "RESULT: UNSAT",
        )
        assert result["sat_result"] == "UNSAT"

    def test_unsat_decoded_empty(self):
        result = run_pipeline(
            "A & ~A", {"A": "always_false"},
            llm_call_fn=lambda s, u: "RESULT: UNSAT",
        )
        assert result["decoded"] == {}

    def test_unsat_verified_false(self):
        result = run_pipeline(
            "A & ~A", {"A": "always_false"},
            llm_call_fn=lambda s, u: "RESULT: UNSAT",
        )
        assert result["verified"] is False

    def test_unsat_parse_error_false(self):
        result = run_pipeline(
            "A & ~A", {"A": "always_false"},
            llm_call_fn=lambda s, u: "RESULT: UNSAT",
        )
        assert result["parse_error"] is False


# ---------------------------------------------------------------------------
# TestPipelineParseError — F6 regression
# ---------------------------------------------------------------------------

class TestPipelineParseError:
    def test_garbled_sets_parse_error(self):
        result = run_pipeline(
            "A | B", {"A": "x", "B": "y"},
            llm_call_fn=lambda s, u: "Sorry, I cannot solve this.",
        )
        assert result["parse_error"] is True
        assert result["sat_result"] is None

    def test_garbled_decoded_empty(self):
        result = run_pipeline(
            "A | B", {"A": "x", "B": "y"},
            llm_call_fn=lambda s, u: "Sorry, I cannot solve this.",
        )
        assert result["decoded"] == {}

    def test_partial_result_line_only(self):
        """Response has RESULT but no SAT/UNSAT — should be parse_error."""
        result = run_pipeline(
            "A | B", {"A": "x", "B": "y"},
            llm_call_fn=lambda s, u: "RESULT: MAYBE",
        )
        assert result["parse_error"] is True


# ---------------------------------------------------------------------------
# TestPipelineDryRun
# ---------------------------------------------------------------------------

class TestPipelineDryRun:
    def test_dry_run_no_llm(self, capsys):
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=None)
        assert result["sat_result"] is None
        assert result["verified"] is None
        assert result["parse_error"] is False
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_dry_run_returns_prompt_ctx(self):
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=None)
        assert "token_map" in result["prompt_ctx"]
        assert "decode_map" in result["prompt_ctx"]


# ---------------------------------------------------------------------------
# TestPipelineDecoyCount
# ---------------------------------------------------------------------------

class TestPipelineDecoyCount:
    def test_decoy_count_in_header(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES, decoy_count=3)
        first_line = ctx["user"].splitlines()[0]
        assert str(len(VAR_NAMES) + 3) in first_line


# ---------------------------------------------------------------------------
# TestFileExport — F4 regression (export params removed)
# ---------------------------------------------------------------------------

class TestFileExport:
    def test_dimacs_via_generate_dimacs(self):
        """DIMACS is accessible via generate_dimacs(result['prompt_ctx']) — not via run_pipeline param."""
        ctx = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        dimacs, _ = generate_dimacs(ctx)
        assert dimacs.startswith("c DIMACS")
        assert "p cnf" in dimacs

    def test_secret_state_in_prompt_ctx(self):
        """Secret state lives in result['prompt_ctx'], never written to disk by default."""
        ctx = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        assert "token_map" in ctx
        assert "decode_map" in ctx

    def test_run_pipeline_has_no_export_params(self):
        """F4 regression: run_pipeline must not accept export_secret_path or export_dimacs_path."""
        import inspect
        sig = inspect.signature(run_pipeline)
        assert "export_secret_path" not in sig.parameters
        assert "export_dimacs_path" not in sig.parameters
