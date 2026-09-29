"""The shipped examples must verify, and must never leak a real name into a prompt."""
import importlib.util
import pathlib
import sys

import pytest

from sat_private import run_pipeline

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"
sys.path.insert(0, str(EXAMPLES))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("name", ["access_control", "compliance_rules", "feature_flags"])
def test_example_verifies_without_leaking(name):
    mod = _load(name)
    seen = []

    def spy(system, user):
        seen.append(system + user)
        return mod.mock_llm(system, user)

    result = run_pipeline(expr_str=mod.FORMULA, real_var_meanings=mod.REAL_VARS, llm_call_fn=spy)
    assert result["sat_result"] == "SAT"
    assert result["verified"] is True
    assert set(result["decoded"]) == set(mod.REAL_VARS.values())
    for prompt in seen:
        for real in mod.REAL_VARS.values():
            assert real not in prompt
