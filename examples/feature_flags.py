"""
UC-2 · Feature Flag Dependency Validation
------------------------------------------
Checks that a proposed combination of feature flags is internally
consistent before a release, without leaking flag names to the LLM.
"""

from sat_private import run_pipeline

REAL_VARS = {
    'A': 'new_checkout_enabled',
    'B': 'legacy_checkout_disabled',
    'C': 'payment_v2_enabled',
    'D': 'analytics_v3_enabled',
    'E': 'ab_test_cohort_active',
}

FORMULA = '(~A | B) & (~A | C) & (~D | E) & A & D'


def mock_llm(system: str, user: str) -> str:
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
