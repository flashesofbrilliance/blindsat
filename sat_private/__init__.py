"""
sat_private — Private SAT pipeline with binary-encoded CNF and LLM solver.
Public API surface: import only what callers need.
"""
from .core import (
    encode_variables,
    generate_sat_prompt,
    generate_verify_prompt,
    generate_dimacs,
    decode_assignment,
)
from .pipeline import run_pipeline

__all__ = [
    "encode_variables",
    "generate_sat_prompt",
    "generate_verify_prompt",
    "generate_dimacs",
    "decode_assignment",
    "run_pipeline",
]
__version__ = "0.1.0"
