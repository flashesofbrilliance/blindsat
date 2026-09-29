"""UC-1 Access Control Policy Evaluation."""
from _mock import mock_llm

from sat_private import run_pipeline

REAL_VARS = {"A": "user_is_admin", "B": "has_mfa", "C": "is_weekday", "D": "from_vpn"}
FORMULA = "(A | B) & (C | D) & (~A | ~D) & (B | C)"


if __name__ == "__main__":
    result = run_pipeline(
        expr_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print(result)
