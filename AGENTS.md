<!-- intent:begin -->
## Intent
- **Why:** A private SAT pipeline: encode CNF over opaque hex tokens, have an LLM solve and a second call verify, and keep the decode map with the caller so the model never sees variable names.
- **Done looks like:** The demo verifies end to end and the package is installable.
- **Not this:** Not on PyPI despite a `pyproject.toml` (not-found on 2026-10-03). Not a general SAT solver: correctness comes from the verify step, not the LLM.
- **Status:** active (last merge `a1a8dbe` 2026-09-29)
- **Last verified:** 2026-10-03 (`git log`; PyPI JSON API returned not-found for `blindsat`)
- **Spec:** none
<!-- intent:end -->
