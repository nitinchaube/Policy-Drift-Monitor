"""Deterministic rule compilation and claim adjudication.

No language model is involved anywhere in this file, and that is the point. A model
authors rules upstream; ordinary code executes them here. A denial has to be
reproducible, identical every time, and defensible three years later on appeal, and
a model in the decision path gives you none of those things.

Evaluation is three-valued. A condition is TRUE, FALSE, or UNKNOWN. UNKNOWN exists
because a claim that is missing a field has not told us the requirement failed, only
that we cannot tell. Absence of data is not evidence of ineligibility, so UNKNOWN
routes to a human rather than to a denial.
"""
from __future__ import annotations

import json
from pathlib import Path

TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"
MISSING = object()

OPS = {
    "==":           lambda a, b: a == b,
    "!=":           lambda a, b: a != b,
    ">=":           lambda a, b: a >= b,
    "<=":           lambda a, b: a <= b,
    ">":            lambda a, b: a > b,
    "<":            lambda a, b: a < b,
    "in":           lambda a, b: a in b,
    "not_in":       lambda a, b: a not in b,
    "contains_any": lambda a, b: bool(set(a) & set(b)),
    "is_true":      lambda a, b: a is True,
    "is_false":     lambda a, b: a is False,
}

PRECEDENCE = {"DENY": 3, "REVIEW": 2, "PAY": 1}
REQUIRED_CLAIM_FIELDS = ["claim_id", "date_of_service", "procedure_code", "units", "billed_amount"]


def get_field(claim: dict, field: str):
    if field in claim:
        return claim[field]
    if field in claim.get("attributes", {}):
        return claim["attributes"][field]
    return MISSING


def eval_condition(claim: dict, cond: dict) -> str:
    value = get_field(claim, cond["field"])
    if value is MISSING:
        return UNKNOWN
    try:
        return TRUE if OPS[cond["op"]](value, cond.get("value")) else FALSE
    except (TypeError, KeyError):
        return UNKNOWN          # a type mismatch is also "we cannot tell"


def combine(results: list[str], combinator: str = "ALL", n: int | None = None) -> str:
    if combinator == "ALL":
        if FALSE in results:
            return FALSE        # one definite failure settles it
        return UNKNOWN if UNKNOWN in results else TRUE
    if combinator == "ANY":
        if TRUE in results:
            return TRUE         # one definite success settles it
        return UNKNOWN if UNKNOWN in results else FALSE
    if combinator == "N_OF_M":
        t, u = results.count(TRUE), results.count(UNKNOWN)
        if t >= n:
            return TRUE
        return UNKNOWN if t + u >= n else FALSE
    raise ValueError(f"unknown combinator {combinator!r}")


def eval_rule(claim: dict, rule: dict) -> dict:
    """Evaluate one rule against one claim. Returns a readable trace entry."""
    logic = rule["logic"]
    rid = rule["rule_id"]

    applies = combine([eval_condition(claim, c) for c in logic.get("applies_when", [])], "ALL")
    if applies == FALSE:
        return {"rule_id": rid, "status": "NOT_APPLICABLE", "outcome": None}
    if applies == UNKNOWN:
        return {"rule_id": rid, "status": "APPLICABILITY_UNKNOWN", "outcome": "REVIEW",
                "why": "cannot determine whether this rule applies",
                "citation": rule.get("source_sentence")}

    # A rule marked non-codifiable encodes a clinical judgment. It applies, but it is
    # never permitted to decide on its own.
    if not rule.get("codifiable", True):
        return {"rule_id": rid, "status": "NOT_CODIFIABLE", "outcome": "REVIEW",
                "why": "policy language requires human judgment",
                "citation": rule.get("source_sentence")}

    per_condition = [eval_condition(claim, c) for c in logic["requires"]]
    verdict = combine(per_condition, logic.get("combinator", "ALL"), logic.get("n"))

    if verdict == TRUE:
        return {"rule_id": rid, "status": "PASS", "outcome": None}
    if verdict == FALSE:
        failed = [c["field"] for c, r in zip(logic["requires"], per_condition) if r == FALSE]
        return {"rule_id": rid, "status": "FAIL", "outcome": logic["on_fail"],
                "why": f"failed on {failed}", "citation": rule.get("source_sentence")}

    unknown = [c["field"] for c, r in zip(logic["requires"], per_condition) if r == UNKNOWN]
    return {"rule_id": rid, "status": "UNDETERMINED", "outcome": "REVIEW",
            "why": f"missing data: {unknown}", "citation": rule.get("source_sentence")}


def adjudicate(claim: dict, rules: list[dict]) -> dict:
    """Run every rule, then combine outcomes by precedence: DENY > REVIEW > PAY."""
    trace = [eval_rule(claim, r) for r in rules]
    outcomes = [t["outcome"] for t in trace if t["outcome"]]

    # No rule objected, so there is no basis to deny.
    decision = "PAY" if not outcomes else max(outcomes, key=lambda o: PRECEDENCE[o])

    return {"claim_id": claim["claim_id"], "decision": decision,
            "fired": [t for t in trace if t["status"] not in ("NOT_APPLICABLE", "PASS")],
            "trace": trace}


def load_claims(path: str | Path):
    """Load claims, rejecting malformed records with a stated reason."""
    blob = json.loads(Path(path).read_text())["claims"]
    good, rejected, seen = [], [], set()
    for c in blob:
        missing = [f for f in REQUIRED_CLAIM_FIELDS if f not in c]
        if missing:
            rejected.append((c.get("claim_id", "?"), f"missing required field(s): {missing}"))
            continue
        if c["claim_id"] in seen:
            rejected.append((c["claim_id"], "duplicate claim_id"))
            continue
        if not isinstance(c["units"], int) or c["units"] < 1:
            rejected.append((c["claim_id"], f"units must be an integer >= 1, got {c['units']}"))
            continue
        seen.add(c["claim_id"])
        good.append(c)
    return good, rejected


def validate_rule(rule: dict, doc_text: str, allowed_fields, locate_fn):
    """Return (span, [problems]). An empty problem list means the rule may compile."""
    problems = []

    span = locate_fn(doc_text, rule["source_sentence"])
    if span is None:
        problems.append("citation not found in source document (fabricated quote)")

    for c in rule["logic"]["applies_when"] + rule["logic"]["requires"]:
        if c["field"] not in allowed_fields:
            problems.append(f"unknown field '{c['field']}' (not in claim schema)")
        if c["op"] not in OPS:
            problems.append(f"unsupported operator '{c['op']}'")

    if not rule["logic"]["requires"]:
        problems.append("rule has no requirements, it can never fire")
    if rule["logic"].get("combinator") == "N_OF_M" and not rule["logic"].get("n"):
        problems.append("N_OF_M combinator without n")

    return span, problems
