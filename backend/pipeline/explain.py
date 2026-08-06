"""Plain-English explanation of a claim decision, for the provider who received it.

The model only writes prose. Decision, firing rule, and citation are all handed to
it, and it's told not to introduce requirements outside the trace.
"""
from __future__ import annotations

import json

from .llm import chat_json

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "headline":    {"type": "string"},
        "explanation": {"type": "string"},
        "what_to_do":  {"type": "string"},
    },
    "required": ["headline", "explanation", "what_to_do"],
    "additionalProperties": False,
}

EXPLAIN_SYSTEM = """You write the explanation a healthcare provider receives with a claim decision.

You are given the decision, the claim's relevant facts, and every rule that fired with the
policy sentence behind it. Write for a billing manager at a supplier: literate, not
clinical, and not a lawyer.

HARD CONSTRAINTS

1. Use ONLY the rules and citations supplied. Never introduce a requirement that is not in
   the trace. If the decision rests on one failed requirement, say that one thing.

2. Quote the governing policy language rather than paraphrasing it, so the provider can go
   and read the source.

3. For REVIEW, be explicit that this is not a denial. The record did not carry the
   information needed to decide, and a person is looking at it.

4. For PAY, keep it to a sentence.

5. No apology, no hedging, no filler. A provider reading this wants to know what happened
   and what to do next.

headline: one line, under 90 characters.
explanation: two to four sentences.
what_to_do: the concrete next step, or "No action needed." when the claim was paid."""


def explain(claim: dict, result: dict, tag: str = "") -> dict:
    fired = [t for t in result["trace"] if t["status"] not in ("NOT_APPLICABLE", "PASS")]
    payload = {
        "decision": result["decision"],
        "claim": {
            "claim_id": claim["claim_id"],
            "procedure_code": claim["procedure_code"],
            "date_of_service": claim["date_of_service"],
            "billed_amount": claim["billed_amount"],
            "units": claim["units"],
            "attributes": claim.get("attributes", {}),
        },
        "rules_that_fired": [
            {"rule_id": t["rule_id"], "status": t["status"], "why": t.get("why", ""),
             "policy_language": t.get("citation", "")}
            for t in fired
        ] or "none, no rule objected to this claim",
    }
    parsed, _ = chat_json(EXPLAIN_SYSTEM, json.dumps(payload, indent=2),
                          EXPLAIN_SCHEMA, "explain", run_tag=tag)
    return {"claim_id": claim["claim_id"], "decision": result["decision"], **parsed}
