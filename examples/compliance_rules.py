"""
UC-3 · Regulatory Compliance Rule Satisfiability
-------------------------------------------------
Demonstrates how sat_private checks whether a compliance rule set
can be simultaneously satisfied — without exposing regulation names
or internal policy identifiers to the LLM.
"""
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
        formula_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print("\n--- Pipeline Result ---")
    print(f"SAT:         {result['sat_result']}")
    print(f"Verified:    {result.get('verified')}")
    print(f"Parse error: {result.get('parse_error')}")
    print(f"Decoded:     {result.get('decoded')}")
