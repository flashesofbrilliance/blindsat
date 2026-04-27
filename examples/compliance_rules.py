"""
UC-3 · Regulatory Compliance Rule Satisfiability
--------------------------------------------------
Checks whether overlapping GDPR / SOC2 / HIPAA-style clauses are mutually
satisfiable, without leaking legal language to the LLM.
"""

from sat_private import run_pipeline

REAL_VARS = {
    'A': 'gdpr_consent_obtained',
    'B': 'data_minimisation_applied',
    'C': 'retention_limit_enforced',
    'D': 'cross_border_transfer_approved',
    'E': 'dpa_signed',
    'F': 'breach_notification_ready',
}

FORMULA = '(A | ~D) & (B & C) & (~D | E) & F & (A | B)'


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
