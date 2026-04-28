"""UC-1 Access Control Policy Evaluation."""
from sat_private import run_pipeline

REAL_VARS = {"A": "user_is_admin", "B": "has_mfa", "C": "is_weekday", "D": "from_vpn"}
FORMULA = "(A | B) & (C | D) & (~A | ~D) & (B | C)"


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
