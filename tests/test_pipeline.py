"""
tests/test_pipeline.py
Integration tests for sat_private/pipeline.py -- uses mock LLM, no real API calls.

Key design: the mock LLM parses tokens from the *actual* prompt it receives,
so it stays in sync regardless of which random tokens the pipeline generates.
"""
import re

from sat_private import generate_dimacs, generate_sat_prompt, run_pipeline
from tests.conftest import EXPR_MEDIUM, REAL_VARS, VAR_NAMES

NL = chr(10)

_MEDIUM_ASSIGN = {"A": True, "B": False, "C": True, "D": False}


def _build_mock_llm(real_vars, expr, sym_values, verify_pass=True):
    """Build a mock LLM that reads tokens from the prompt it receives.

    Parses the VARS block of the real prompt so the SAT response always uses
    the same tokens the pipeline generated — no dry-run token capture needed.
    """
    var_names_list = list(real_vars.keys())
    idx = [0]

    def mock(system, user):
        if idx[0] == 0:
            # Parse VARS section to get actual tokens in var order
            m = re.search(r"VARS:\n(.*?)\n\n", user, re.DOTALL)
            all_tokens = m.group(1).splitlines() if m else []
            token_map = dict(zip(var_names_list, all_tokens[: len(var_names_list)]))
            lines = ["RESULT: SAT", "ASSIGNMENT:"]
            for sym, val in sym_values.items():
                if sym in token_map:
                    lines.append(token_map[sym] + ": " + ("TRUE" if val else "FALSE"))
            r = NL.join(lines)
        else:
            r = (
                "VERIFICATION: PASS"
                if verify_pass
                else "VERIFICATION: FAIL" + NL + "UNSATISFIED_CLAUSES: 1"
            )
        idx[0] += 1
        return r

    return mock


class TestPipelineSat:
    def test_sat_result_key(self):
        llm = _build_mock_llm(REAL_VARS, EXPR_MEDIUM, _MEDIUM_ASSIGN)
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert result["sat_result"] == "SAT"

    def test_verified_true_on_pass(self):
        llm = _build_mock_llm(
            REAL_VARS, EXPR_MEDIUM,
            {"A": True, "B": False, "C": True, "D": False},
            verify_pass=True,
        )
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert result["verified"] is True

    def test_decoded_contains_real_names(self):
        llm = _build_mock_llm(REAL_VARS, EXPR_MEDIUM, _MEDIUM_ASSIGN)
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert set(result["decoded"].keys()) <= set(REAL_VARS.values())

    def test_parse_error_false_on_clean_response(self):
        llm = _build_mock_llm(REAL_VARS, EXPR_MEDIUM, _MEDIUM_ASSIGN)
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        assert result["parse_error"] is False

    def test_result_keys_present(self):
        llm = _build_mock_llm(REAL_VARS, EXPR_MEDIUM, _MEDIUM_ASSIGN)
        result = run_pipeline(EXPR_MEDIUM, REAL_VARS, llm_call_fn=llm)
        for key in ["sat_result", "verified", "parse_error", "decoded",
                    "raw_response", "verify_response", "prompt_ctx"]:
            assert key in result, f"Missing key: {key}"


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
        result = run_pipeline(
            "A | B", {"A": "x", "B": "y"},
            llm_call_fn=lambda s, u: "RESULT: MAYBE",
        )
        assert result["parse_error"] is True


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


class TestPipelineDecoyCount:
    def test_decoy_count_in_header(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES, decoy_count=3)
        first_line = ctx["user"].splitlines()[0]
        assert str(len(VAR_NAMES) + 3) in first_line


class TestFileExport:
    def test_dimacs_via_generate_dimacs(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        dimacs, _ = generate_dimacs(ctx)
        assert dimacs.startswith("c DIMACS")
        assert "p cnf" in dimacs

    def test_secret_state_in_prompt_ctx(self):
        ctx = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        assert "token_map" in ctx
        assert "decode_map" in ctx

    def test_run_pipeline_has_no_export_params(self):
        import inspect
        sig = inspect.signature(run_pipeline)
        assert "export_secret_path" not in sig.parameters
        assert "export_dimacs_path" not in sig.parameters
