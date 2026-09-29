"""Deterministic offline stand-in for an LLM, used by the examples.

It answers both prompts honestly: the solver prompt with a real satisfying
assignment (brute force over the opaque tokens), and the verifier prompt by
actually checking every clause. It only ever sees hex tokens, same as a real LLM.
"""
import itertools
import re

_TOKEN = re.compile(r"\b[0-9A-F]{8}\b")


def _parse_clauses(block: str) -> list[list[tuple[str, bool]]]:
    clauses = []
    for line in block.splitlines():
        if "(" not in line:
            continue
        body = line[line.index("(") + 1 : line.rindex(")")]
        lits = []
        for lit in body.split("|"):
            lit = lit.strip()
            lits.append((lit.lstrip("~"), not lit.startswith("~")))
        clauses.append(lits)
    return clauses


def _satisfied(clauses, assignment) -> list[int]:
    return [
        i + 1
        for i, c in enumerate(clauses)
        if not any(assignment.get(t, False) == pos for t, pos in c)
    ]


def mock_llm(system: str, user: str) -> str:
    if "VERIFICATION" in system:
        clause_part, assign_part = user.split("ASSIGNMENT:")
        clauses = _parse_clauses(clause_part)
        assignment = {
            t: v.strip() == "TRUE"
            for t, v in (ln.split(":") for ln in assign_part.strip().splitlines())
        }
        bad = _satisfied(clauses, assignment)
        if bad:
            return "VERIFICATION: FAIL\nUNSATISFIED_CLAUSES: " + ",".join(map(str, bad))
        return "VERIFICATION: PASS"

    var_block = user.split("VARS:")[1].split("CLAUSES:")[0]
    tokens = _TOKEN.findall(var_block)
    clauses = _parse_clauses(user.split("CLAUSES:")[1])
    for values in itertools.product([True, False], repeat=len(tokens)):
        assignment = dict(zip(tokens, values))
        if not _satisfied(clauses, assignment):
            lines = ["RESULT: SAT", "ASSIGNMENT:"]
            lines += [f"{t}: {'TRUE' if v else 'FALSE'}" for t, v in assignment.items()]
            return "\n".join(lines)
    return "RESULT: UNSAT"
