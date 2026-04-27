"""
sat_private — Private SAT pipeline with binary-encoded CNF and LLM solver.
Public API surface: import only what callers need.
"""
from .core import (
    decode_assignment,
    encode_variables,
    generate_dimacs,
    generate_sat_prompt,
    generate_verify_prompt,
)
from .pipeline import run_pipeline

__all__ = [
    "decode_assignment",
    "encode_variables",
    "generate_dimacs",
    "generate_sat_prompt",
    "generate_verify_prompt",
    "run_pipeline",
]
__version__ = "0.1.0"
