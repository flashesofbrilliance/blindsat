"""
sat_private/pipeline.py
-----------------------
High-level orchestrator: calls core functions in order, handles LLM wiring,
verification gating, and structured result output.
"""
from __future__ import annotations
from typing import Callable, Any
from .core import (
    generate_sat_prompt, generate_verify_prompt,
    generate_dimacs, decode_assignment,
)


def run_pipeline(
    expr_str: str,
    real_var_meanings: dict[str, str],
    *,
    llm_call_fn: Callable[[str, str], str] | None = None,
    decoy_count: int = 0,
    export_dimacs_path: str | None = None,
    export_secret_path: str | None = None,
) -> dict[str, Any]:
    """
    Full private SAT pipeline.

    Parameters
    ----------
    expr_str            : Boolean formula string (symbols = real_var_meanings keys)
    real_var_meanings   : {symbol: real_name} — STAYS CALLER-SIDE, never sent to LLM
    llm_call_fn         : Callable(system_prompt, user_prompt) -> str
                          Pass None for a dry run that skips LLM calls.
    decoy_count         : Number of noise tokens to inject (default 0)
    export_dimacs_path  : If set, write DIMACS CNF to this path
    export_secret_path  : If set, write caller_secret_state JSON to this path
                          WARNING: never use in production; secret state is in-memory only

    Returns
    -------
    {
        sat_result   : "SAT" | "UNSAT" | None (dry run)
        verified     : bool | None
        decoded      : {real_name: bool}   — empty if UNSAT
        raw_response : str                 — raw LLM text (SAT call)
        verify_response : str              — raw LLM text (verify call)
        prompt_ctx   : dict                — includes token_map / decode_map (CALLER SECRET)
    }
    """
    var_names  = list(real_var_meanings.keys())
    prompt_ctx = generate_sat_prompt(expr_str, var_names, decoy_count=decoy_count)

    dimacs_str, caller_map = generate_dimacs(prompt_ctx)
    if export_dimacs_path:
        with open(export_dimacs_path, "w") as f:
            f.write(dimacs_str)
    if export_secret_path:
        import json
        with open(export_secret_path, "w") as f:
            json.dump({"int_to_symbol": caller_map,
                       "symbol_to_real": real_var_meanings}, f, indent=2)

    if llm_call_fn is None:
        print("[DRY RUN] Skipping LLM calls. Prompt preview:")
        print("  System:", prompt_ctx["system"][:80].replace("\n", " "), "...")
        print("  User  :", prompt_ctx["user"][:120].replace("\n", " "), "...")
        return {
            "sat_result": None,
            "verified": None,
            "decoded": {},
            "raw_response": "",
            "verify_response": "",
            "prompt_ctx": prompt_ctx,
        }

    raw_response = llm_call_fn(prompt_ctx["system"], prompt_ctx["user"])
    sat_result   = "UNSAT" if "UNSAT" in raw_response.upper() else "SAT"

    token_assignment: dict[str, bool] = {}
    for line in raw_response.splitlines():
        for token in prompt_ctx["decode_map"]:
            if token in line:
                token_assignment[token] = "TRUE" in line.upper()

    verify_response = ""
    verified        = None
    if sat_result == "SAT" and token_assignment:
        vp              = generate_verify_prompt(prompt_ctx, token_assignment)
        verify_response = llm_call_fn(vp["system"], vp["user"])
        verified        = "PASS" in verify_response.upper()

    sym_decoded  = decode_assignment(raw_response, prompt_ctx["decode_map"])
    real_decoded = {real_var_meanings[sym]: val for sym, val in sym_decoded.items()
                    if sym in real_var_meanings}

    return {
        "sat_result"     : sat_result,
        "verified"       : verified,
        "decoded"        : real_decoded,
        "raw_response"   : raw_response,
        "verify_response": verify_response,
        "prompt_ctx"     : prompt_ctx,
    }
