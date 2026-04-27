# Use Cases — sat_private

## Applicability Matrix

| Use Case | Variables | Clauses | Privacy Sensitivity | Example file |
|---|---|---|---|---|
| UC-1 Access Control | 4–8 | 4–12 | High | `examples/access_control.py` |
| UC-2 Feature Flags | 5–15 | 5–20 | Medium | `examples/feature_flags.py` |
| UC-3 Compliance Rules | 6–20 | 8–30 | Very High | `examples/compliance_rules.py` |
| UC-4 Config Space Exploration | 3–10 | 3–15 | Medium | — |
| UC-5 Theorem Proving (prop.) | 4–12 | 4–20 | High | — |

---

## UC-1 · Zero-Knowledge Access Control Policy Evaluation

**Problem:** An organisation needs to check whether its access-control policy is satisfiable (i.e., at least one valid permission assignment exists) without sending attribute names like `user_is_admin` or `has_mfa` to an external LLM.

**How sat_private helps:** Variable names are replaced with opaque hex tokens before the formula reaches the LLM. The caller holds the decode map. The LLM solves over tokens; the caller decodes.

**Example:** See `examples/access_control.py`.

---

## UC-2 · Feature Flag Dependency Validation

**Problem:** Before a release, an engineering team wants to confirm that a proposed combination of feature flags is internally consistent (no contradictions).

**How sat_private helps:** Flag names and their dependency rules are encoded privately. The LLM confirms satisfiability or surfaces UNSAT, indicating a conflict that must be resolved before rollout.

**Example:** See `examples/feature_flags.py`.

---

## UC-3 · Regulatory Compliance Rule Satisfiability

**Problem:** A compliance team needs to check whether overlapping GDPR / SOC2 / HIPAA-style clauses are mutually satisfiable without leaking legal language or internal policy structure to a cloud model.

**How sat_private helps:** Clause semantics stay caller-side. The LLM sees only a structural CNF over hex tokens and returns a satisfying assignment or UNSAT.

**Example:** See `examples/compliance_rules.py`.

---

## UC-4 · Private Configuration Space Exploration

**Problem:** A system has many interdependent configuration knobs. A team wants LLM assistance exploring valid configurations without exposing the schema.

**How sat_private helps:** Configuration constraints become clauses; knob names become tokens. The LLM suggests valid configurations; the caller decodes them into actionable settings.

---

## UC-5 · AI-Assisted Propositional Theorem Proving

**Problem:** A researcher wants LLM heuristics applied to an unpublished propositional formula without revealing the formula's semantic content.

**How sat_private helps:** The formula's structural CNF is exposed to the LLM in token form. Solving proceeds without the LLM ever knowing what the symbols mean. DIMACS export enables ground-truth verification via MiniSAT.
