"""
UC-1 · Zero-Knowledge Access Control Policy Evaluation
-------------------------------------------------------
Demonstrates how sat_private evaluates access policy satisfiability
without exposing attribute names (user_is_admin, has_mfa, etc.) to the LLM.

The formula encodes:
  - A user must be admin OR have MFA
  - The request must be on a weekday OR from the VPN
  - An admin cannot also be from the VPN (separation of concerns)
  - MFA or weekday must hold
"""

from sat_private import run_pipeline

# Real variable meanings — stay caller-side, never sent to the LLM
REAL_VARS = {
    'A': 'user_is_admin',
    'B': 'has_mfa',
    'C': 'is_weekday',
    'D': 'request_from_vpn',
}

FORMULA = '(A | B) & (C | D) & (~A | ~D) & (B | C)'


def mock_llm(system: str, user: str) -> str:
    """
    Placeholder — replace with your OpenAI/Anthropic call.
    Signature: (system: str, user: str) -> str
    """
    # Extract a token from the VARS block to build a plausible mock response
    vars_block = [l for l in user.splitlines() if len(l) == 8 and l.isupper()]
    lines = ["RESULT: SAT", "ASSIGNMENT:"]
    for i, tok in enumerate(vars_block):
        lines.append(f"{tok}: {'TRUE' if i % 2 == 0 else 'FALSE'}")
    return "\n".join(lines)


if __name__ == '__main__':
    result = run_pipeline(
        formula_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print('\n--- Pipeline Result ---')
    print(f"SAT:         {result['sat_result']}")
    print(f"Verified:    {result.get('verified')}")
    print(f"Parse error: {result.get('parse_error')}")
    print(f"Decoded:     {result.get('decoded')}")
