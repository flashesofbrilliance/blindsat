"""
sat_private/pipeline.py
-----------------------
High-level orchestrator: calls core functions in order, handles LLM wiring,
verification gating, and structured result output.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .core import (
    decode_assignment,
    generate_sat_prompt,
    generate_verify_prompt,
)

# Canonical llm_call_fn signature: (system: str, user: str) -> str
# All examples, docs, and tests must match this exactly.
LLMCallable = Callable[[str, str], str]


def run_pipeline(
    expr_str: str,
    real_var_meanings: dict[str, str],
    *,
    llm_call_fn: LLMCallable | None = None,
    decoy_count: int = 0,
) -> dict[str, Any]:
    """
    Full private SAT pipeline.

    Parameters
    ----------
    expr_str            : Boolean formula string (symbols = real_var_meanings keys)
    real_var_meanings   : {symbol: real_name} — STAYS CALLER-SIDE, never sent to LLM
    llm_call_fn         : Callable(system: str, user: str) -> str
                          Pass None for a dry run that skips LLM calls.
    decoy_count         : Number of noise tokens to inject (default 0)

    Returns
    -------
    {
        sat_result      : "SAT" | "UNSAT" | None (dry run)
        verified        : bool | None
        parse_error     : bool  — True if LLM output could not be cleanly parsed
        decoded         : {real_name: bool}   — empty if UNSAT or parse_error
        raw_response    : str   — raw LLM text (SAT call)
        verify_response : str   — raw LLM text (verify call)
        prompt_ctx      : dict  — includes token_map / decode_map (CALLER SECRET)
    }
    """
    var_names = list(real_var_meanings.keys())
    prompt_ctx = generate_sat_prompt(expr_str, var_names, decoy_count=decoy_count)

    if llm_call_fn is None:
        print("[DRY RUN] Skipping LLM calls. Prompt preview:")
        print("  System:", prompt_ctx["system"][:80].replace("\n", " "), "...")
        print("  User  :", prompt_ctx["user"][:120].replace("\n", " "), "...")
        return {
            "sat_result": None,
            "verified": None,
            "parse_error": False,
            "decoded": {},
            "raw_response": "",
            "verify_response": "",
            "prompt_ctx": prompt_ctx,
        }

    raw_response = llm_call_fn(prompt_ctx["system"], prompt_ctx["user"])

    # ── Strict parse: require RESULT: SAT or RESULT: UNSAT ──────────────────
    upper = raw_response.upper()
    if "RESULT: UNSAT" in upper:
        return {
            "sat_result": "UNSAT",
            "verified": False,
            "parse_error": False,
            "decoded": {},
            "raw_response": raw_response,
            "verify_response": "",
            "prompt_ctx": prompt_ctx,
        }
    if "RESULT: SAT" not in upper:
        return {
            "sat_result": None,
            "verified": None,
            "parse_error": True,
            "decoded": {},
            "raw_response": raw_response,
            "verify_response": "",
            "prompt_ctx": prompt_ctx,
        }

    sat_result = "SAT"

    # ── Build token assignment from raw response ─────────────────────────────
    token_assignment: dict[str, bool] = {}
    for line in raw_response.splitlines():
        for token in prompt_ctx["decode_map"]:
            if token in line:
                token_assignment[token] = "TRUE" in line.upper()

    # ── Verification call ────────────────────────────────────────────────────
    verify_response = ""
    verified = None
    if token_assignment:
        vp = generate_verify_prompt(prompt_ctx, token_assignment)
        verify_response = llm_call_fn(vp["system"], vp["user"])
        verified = "PASS" in verify_response.upper()

    # ── Decode via single canonical path (core.decode_assignment) ────────────
    sym_decoded = decode_assignment(raw_response, prompt_ctx["decode_map"])
    real_decoded = {
        real_var_meanings[sym]: val
        for sym, val in sym_decoded.items()
        if sym in real_var_meanings
    }

    return {
        "sat_result": sat_result,
        "verified": verified,
        "parse_error": False,
        "decoded": real_decoded,
        "raw_response": raw_response,
        "verify_response": verify_response,
        "prompt_ctx": prompt_ctx,
    }
