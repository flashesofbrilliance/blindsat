"""UC-3 Regulatory Compliance Rule Satisfiability."""
from _mock import mock_llm

from sat_private import run_pipeline

REAL_VARS = {
    "A": "gdpr_consent",
    "B": "legitimate_interest",
    "C": "data_minimisation",
    "D": "cross_border_transfer",
    "E": "standard_contractual_clauses",
}
FORMULA = "(A | B) & C & (~D | E) & (~A | ~B)"


if __name__ == "__main__":
    result = run_pipeline(
        expr_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print(result)
