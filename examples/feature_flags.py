"""
UC-2 · Feature Flag Dependency Validation
------------------------------------------
Demonstrates how sat_private checks whether a set of feature flag
dependency constraints can be simultaneously satisfied — without
exposing flag names to the LLM.
"""
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
    """
    Placeholder — replace with your OpenAI/Anthropic call.
    Signature: (system: str, user: str) -> str
    """
    vars_block = [line for line in user.splitlines() if len(line) == 8 and line.isupper()]
    lines = ["RESULT: SAT", "ASSIGNMENT:"]
    for i, tok in enumerate(vars_block):
        lines.append(f"{tok}: {'TRUE' if i % 2 == 0 else 'FALSE'}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_pipeline(
        expr_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print("\n--- Pipeline Result ---")
    print(f"SAT:         {result['sat_result']}")
    print(f"Verified:    {result.get('verified')}")
    print(f"Parse error: {result.get('parse_error')}")
    print(f"Decoded:     {result.get('decoded')}")
