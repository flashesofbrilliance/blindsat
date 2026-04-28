"""UC-2 Feature Flag Dependency Validation."""
from sat_private import run_pipeline

REAL_VARS = {
    "A": "dark_mode",
    "B": "ui_v2",
    "C": "legacy_compat",
    "D": "analytics",
    "E": "data_pipeline",
}
FORMULA = "(~A | B | C) & (~D | E) & (~A | ~C) & (B | E)"


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
