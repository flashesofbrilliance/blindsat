"""
UC-2 · Feature Flag Dependency Validation
------------------------------------------
Checks that a proposed combination of feature flags is internally
consistent before a release, without leaking flag names to the LLM.

The formula encodes:
  - New checkout requires legacy checkout to be disabled
  - New checkout requires Payment v2
  - Analytics v3 requires the A/B cohort to be active
  - Both new checkout and analytics v3 are being enabled in this release
"""

from sat_private import run_pipeline

REAL_VARS = {
    'A': 'new_checkout_enabled',
    'B': 'legacy_checkout_disabled',
    'C': 'payment_v2_enabled',
    'D': 'analytics_v3_enabled',
    'E': 'ab_test_cohort_active',
}

# (~A | B): if new checkout, then legacy must be off
# (~A | C): if new checkout, then payment_v2 must be on
# (~D | E): if analytics_v3, then ab_test must be active
# A & D:   both flags are being turned on in this release
FORMULA = '(~A | B) & (~A | C) & (~D | E) & A & D'


def mock_llm(prompt: str) -> str:
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
