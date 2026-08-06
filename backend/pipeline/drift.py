"""Drift detection: is an existing rule still supported by a revised policy?

The obvious approach, extracting rules from both versions and diffing the two rulesets,
does not work. The extractor is not perfectly stable, so re-extracting from a nearly
identical document produces differences that come from our own nondeterminism rather
than from the policy. Instead the ruleset is held fixed and the model answers one narrow
classification question per rule.

The model is never asked for the verdict. It reports observations and `derive_verdict`
computes the verdict from a decision table. That went through three iterations: asking
for a verdict directly made it under-sensitive (it missed "injections" becoming
"administrations"), forcing a word-by-word diff first made it over-sensitive (a
renumbered cross-reference started reading as a real change), and separating facts from
judgement fixed both. Never ask a model for a conclusion you can compute from its inputs.
"""
from __future__ import annotations

import json

from .llm import chat_json
from .pdf_ingest import locate

DRIFT_SCHEMA = {
    "type": "object",
    "properties": {
        "evidence_sentence":           {"type": "string"},
        "wording_differences":         {"type": "string"},
        "requirement_still_present":   {"type": "boolean"},
        "was_item_in_criteria_list":   {"type": "boolean"},
        "changes_what_claims_qualify": {"type": "boolean"},
        "explanation":                 {"type": "string"}},
    "required": ["evidence_sentence", "wording_differences", "requirement_still_present",
                 "was_item_in_criteria_list", "changes_what_claims_qualify", "explanation"],
    "additionalProperties": False,
}

DRIFT_SYSTEM = """You audit whether an existing claim rule is still supported by a revised policy.

You get one rule, its executable logic, the sentence it was derived from, and the full text
of the revised policy.

You do NOT decide a verdict. You report five observations and something else computes the
verdict from them.

THE QUESTION THROUGHOUT: does this RULE, as its logic is actually written, still do what
the revised policy requires? You are auditing a rule, not proofreading prose. A sentence
that was edited in a way that does not touch what the rule tests is not a change here.

STEP 1 - evidence_sentence. Find the sentence in the REVISED policy corresponding to the one
the rule came from. Copy it VERBATIM, including any leading list number. It is checked by
exact search and an unfindable quote invalidates the finding. If the requirement was deleted
outright, quote instead the sentence that introduces the list it used to belong to.

STEP 2 - wording_differences. Put the two sentences side by side and compare word by word.
List every difference, or "none". Watch the operative noun or verb ("injections" vs
"administrations"), qualifiers that widen or narrow scope ("Medicare-covered", "multiple"),
and any numbers, counts, frequencies or time windows.

STEP 3 - requirement_still_present. Does the revised policy still impose this requirement
anywhere, in any wording? True if it survives even in altered form. False if it is gone.

STEP 4 - was_item_in_criteria_list. Was this requirement one numbered item in a list the
policy says must ALL be met for coverage? This matters only when the requirement is gone,
because deleting an item from a closed list means claims the rule denies are now covered.

STEP 5 - changes_what_claims_qualify. Look at the rule's LOGIC, not its prose. Would a claim
with identical patient and billing facts get a different decision out of that logic under
the revised policy? Answer true only if the logic itself is now wrong.

Answer FALSE when the sentence was edited but the logic still implements exactly what the
policy requires. These never change any claim outcome:
  - a cross-reference into a renumbered list, "criteria (1-4)" becoming "criteria (1-3)"
    because an earlier item was removed. The rule does not test the other criteria. It
    tests its own condition, and that condition is untouched.
  - renumbering of the criteria themselves, item 5 becoming item 4
  - line breaks, hyphenation, spacing, capitalization, punctuation
A long list of differences of that kind is still no change at all."""


def derive_verdict(obs: dict) -> tuple[str, str]:
    """Decision table. Deterministic, inspectable, identical every time."""
    if not obs["requirement_still_present"]:
        # Removal from a closed list of criteria contradicts a rule that enforces it,
        # because the rule now denies claims the policy covers.
        return ("CONTRADICTED", "RETIRE") if obs["was_item_in_criteria_list"] \
            else ("UNADDRESSED", "HUMAN_REVIEW")
    if obs["changes_what_claims_qualify"]:
        return ("MODIFIED", "REVISE")
    return ("SUPPORTED", "KEEP")


def check_drift(rule: dict, new_text: str, tag: str = ""):
    user = (f"EXISTING RULE\n  id: {rule['rule_id']}\n  title: {rule['title']}\n"
            f"  derived from: \"{rule['source_sentence']}\"\n"
            f"  logic: {json.dumps(rule['logic'])}\n\n"
            f"REVISED POLICY\n---\n{new_text}\n---")
    parsed, src = chat_json(DRIFT_SYSTEM, user, DRIFT_SCHEMA, "drift", run_tag=tag)

    verdict, action = derive_verdict(parsed)
    span = locate(new_text, parsed["evidence_sentence"])
    parsed.update({"verdict": verdict, "recommended_action": action,
                   "evidence_span": list(span) if span else None,
                   "verified": span is not None, "rule_id": rule["rule_id"]})
    if not parsed["verified"]:          # unverifiable evidence never auto-acts
        parsed["recommended_action"] = "HUMAN_REVIEW"
    return parsed, src


# --------------------------------------------------------------------------- gaps
GAP_SCHEMA = {
    "type": "object",
    "properties": {"gaps": {"type": "array", "items": {
        "type": "object",
        "properties": {"requirement": {"type": "string"}, "source_sentence": {"type": "string"},
                       "why_uncovered": {"type": "string"}},
        "required": ["requirement", "source_sentence", "why_uncovered"],
        "additionalProperties": False}}},
    "required": ["gaps"], "additionalProperties": False,
}

GAP_SYSTEM = """You find coverage requirements in a policy that an existing ruleset does not cover.

You get the revised policy and the list of rules that already exist. Identify checkable
requirements the policy states that no listed rule addresses. Quote the source sentence
VERBATIM. If every requirement is already covered, return an empty list. An empty list is
the correct answer more often than not, so do not invent gaps."""


def find_gaps(rules: list, new_text: str, tag: str = "gap"):
    inventory = "\n".join(f"- {r['rule_id']}: {r['summary']}" for r in rules)
    parsed, src = chat_json(
        GAP_SYSTEM,
        f"EXISTING RULES\n{inventory}\n\nREVISED POLICY\n---\n{new_text}\n---",
        GAP_SCHEMA, "gaps", run_tag=tag)
    for g in parsed["gaps"]:
        span = locate(new_text, g["source_sentence"])
        g["source_span"] = list(span) if span else None
        g["verified"] = span is not None
    return parsed["gaps"], src
