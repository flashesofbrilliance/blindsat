"""
tests/conftest.py
Shared fixtures and helpers for the sat_private test suite.
"""
import pytest

from sat_private import generate_sat_prompt

EXPR_SIMPLE = "(A | B) & (~A | C)"
EXPR_MEDIUM = "(A | B) & (~A | C) & (~B | ~C) & (C | D) & (~D | B)"
EXPR_UNSAT = "A & ~A"
VAR_NAMES = ["A", "B", "C", "D"]
REAL_VARS = {
    "A": "user_is_admin",
    "B": "has_mfa",
    "C": "is_weekday",
    "D": "request_from_vpn",
}


@pytest.fixture
def simple_ctx():
    return generate_sat_prompt(EXPR_SIMPLE, ["A", "B", "C"])


@pytest.fixture
def medium_ctx():
    return generate_sat_prompt(EXPR_MEDIUM, VAR_NAMES)


@pytest.fixture
def mock_llm():
    """Returns a mock LLM that reads its expected output from a list keyed by call index."""

    class MockLLM:
        def __init__(self, responses):
            self._responses = responses
            self._count = 0

        def __call__(self, system, user):
            r = self._responses[self._count % len(self._responses)]
            self._count += 1
            return r

    return MockLLM
