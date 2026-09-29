"""UC-2 Feature Flag Dependency Validation."""
from _mock import mock_llm

from sat_private import run_pipeline

REAL_VARS = {
    "A": "dark_mode",
    "B": "ui_v2",
    "C": "legacy_compat",
    "D": "analytics",
    "E": "data_pipeline",
}
FORMULA = "(~A | B | C) & (~D | E) & (~A | ~C) & (B | E)"


if __name__ == "__main__":
    result = run_pipeline(
        expr_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print(result)
