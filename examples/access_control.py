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

# Propositional formula over symbolic variable names
FORMULA = '(A | B) & (C | D) & (~A | ~D) & (B | C)'


def mock_llm(prompt: str) -> str:
    """Placeholder — replace with your OpenAI/Anthropic call."""
    # A valid satisfying assignment: A=False, B=True, C=True, D=False
    # Token values will differ each run; this is illustrative only.
    lines = [line for line in prompt.splitlines() if 'VARS:' in line or ':' in line]
    return "SATISFIABLE\nASSIGNMENT:\n# Replace with real LLM output"


if __name__ == '__main__':
    result = run_pipeline(
        formula_str=FORMULA,
        real_var_meanings=REAL_VARS,
        llm_call_fn=mock_llm,
    )
    print('\n--- Pipeline Result ---')
    print(f"SAT:      {result['satisfiable']}")
    print(f"Verified: {result.get('verified')}")
    print(f"Decoded:  {result.get('decoded')}")
    print(f"Meanings: {result.get('real_meanings')}")
