"""
sat_private/pipeline.py
-----------------------
High-level orchestrator: calls core functions in order, handles LLM wiring,
verification gating, and structured result output.
"""
from __future__ import annotations
from typing import Callable, Any
from .core import (
    generate_sat_prompt,
    generate_verify_prompt,
    generate_dimacs,
    decode_assignment,
)


def run_pipeline(
    expr_str: str,
    real_var_meanings: dict[str, str],
    *,
    llm_call_fn: Callable[[str, str], str] | None = None,
    decoy_count: int = 0,
    export_dimacs_path: str | None = None,
) -> dict[str, Any]:
    """
    Full private SAT pipeline.

    Parameters
    ----------
    expr_str            : Boolean formula string (symbols = real_var_meanings keys).
                          Supported operators: & (AND), | (OR), ~ (NOT), >> (implies).
    real_var_meanings   : {symbol: real_name}.
                          STAYS CALLER-SIDE — never sent to LLM.
    llm_call_fn         : Callable(system_prompt: str, user_prompt: str) -> str.
                          Pass None for a dry run that skips LLM calls.
                          Signature is (system, user) — both positional strings.
    decoy_count         : Number of noise tokens to inject into the VARS block (default 0).
    export_dimacs_path  : If set, write DIMACS CNF to this path.
                          DIMACS is safe to export — it contains no variable names.

    Returns
    -------
    dict with keys:
        sat_result      : "SAT" | "UNSAT" | None (dry run or parse error)
        verified        : bool | None
        decoded         : {real_name: bool}  — empty if UNSAT or parse error
        parse_error     : bool  — True when LLM response could not be parsed
        raw_response    : str   — raw LLM text (SAT solver call)
        verify_response : str   — raw LLM text (verifier call)
        prompt_ctx      : dict  — includes token_map / decode_map (CALLER SECRET)

    Security note
    -------------
    The caller's secret state (token_map, decode_map, real_var_meanings) lives
    only in the returned prompt_ctx dict and in the caller's process memory.
    Never log, serialise, or write it to disk.
    If you need cross-process persistence, encrypt the caller_map before storage.
    """
    var_names = list(real_var_meanings.keys())
    prompt_ctx = generate_sat_prompt(expr_str, var_names, decoy_count=decoy_count)

    dimacs_str, _ = generate_dimacs(prompt_ctx)
    if export_dimacs_path:
        with open(export_dimacs_path, "w") as f:
            f.write(dimacs_str)

    if llm_call_fn is None:
        print("[DRY RUN] Skipping LLM calls. Prompt preview:")
        print("  System:", prompt_ctx["system"][:80].replace("\n", " "), "...")
        print("  User  :", prompt_ctx["user"][:120].replace("\n", " "), "...")
        return {
            "sat_result": None,
            "verified": None,
            "decoded": {},
            "parse_error": False,
            "raw_response": "",
            "verify_response": "",
            "prompt_ctx": prompt_ctx,
        }

    # ── SAT solver call ─────────────────────────────────────────────────────────────
    raw_response = llm_call_fn(prompt_ctx["system"], prompt_ctx["user"])
    upper = raw_response.upper()

    # F6: detect parse failure before interpreting the response
    is_sat   = "SAT" in upper and "UNSAT" not in upper
    is_unsat = "UNSAT" in upper
    if not is_sat and not is_unsat:
        return {
            "sat_result": None,
            "verified": None,
            "decoded": {},
            "parse_error": True,
            "raw_response": raw_response,
            "verify_response": "",
            "prompt_ctx": prompt_ctx,
        }

    sat_result = "UNSAT" if is_unsat else "SAT"

    # F2: single decode path via core.decode_assignment
    sym_decoded = decode_assignment(raw_response, prompt_ctx["decode_map"])
    real_decoded = {
        real_var_meanings[sym]: val
        for sym, val in sym_decoded.items()
        if sym in real_var_meanings
    }

    # ── Verifier call (SAT only) ───────────────────────────────────────────────────────
    verify_response = ""
    verified = None
    if sat_result == "SAT" and sym_decoded:
        token_assignment = {
            prompt_ctx["token_map"][sym]: val
            for sym, val in sym_decoded.items()
        }
        vp = generate_verify_prompt(prompt_ctx, token_assignment)
        verify_response = llm_call_fn(vp["system"], vp["user"])
        verified = "PASS" in verify_response.upper()

    return {
        "sat_result": sat_result,
        "verified": verified,
        "decoded": real_decoded,
        "parse_error": False,
        "raw_response": raw_response,
        "verify_response": verify_response,
        "prompt_ctx": prompt_ctx,
    }
