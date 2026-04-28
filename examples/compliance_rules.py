"""UC-3 Regulatory Compliance Rule Satisfiability."""
from sat_private import run_pipeline

REAL_VARS = {
    "A": "gdpr_consent",
    "B": "legitimate_interest",
    "C": "data_minimisation",
    "D": "cross_border_transfer",
    "E": "standard_contractual_clauses",
}
FORMULA = "(A | B) & C & (~D | E) & (~A | ~B)"


def mock_llm(system: str, user: str) -> str:
    tokens = [ln for ln in user.splitlines() if len(ln) == 8 and ln.isupper()]
    lines = ["RESULT: SAT", "ASSIGNMENT:"]
    for i, t in enumerate(tokens):
        val = "TRUE" if i % 2 == 0 else "FALSE"
        lines.append(t + ": " + val)
    sep = chr(10)
    return sep.join(lines)


if __name__ == "__main__":
    result = run_pipeline(
        expr_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print(result)
