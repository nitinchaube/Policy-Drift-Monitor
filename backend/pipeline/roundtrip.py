"""Round-trip verification: compile policy to a rule, decompile the rule back to prose,
then compare the two.

The value is that it needs no labels. Scoring extraction against a hand-authored gold
ruleset only works on documents somebody already did by hand, which is none of the
documents you actually care about. This works anywhere, because the source sentence is
its own ground truth.

The decompile step deliberately never sees the source sentence. If it did, it would
paraphrase the policy rather than describe the logic, and the comparison would always
agree with itself. Showing it only field names, operators and values forces it to say
what the rule genuinely does.
"""
from __future__ import annotations

import json

from .llm import chat_json

DECOMPILE_SCHEMA = {
    "type": "object",
    "properties": {"plain_english": {"type": "string"}},
    "required": ["plain_english"],
    "additionalProperties": False,
}

DECOMPILE_SYSTEM = """You translate a machine-readable claim rule back into plain English.

You are given only the rule's logic: field names, operators, values and how they combine.
You are NOT given the policy it came from, and you must not guess at policy language.

Describe exactly what the logic tests, in one or two sentences. Be literal. If conditions
are combined with ANY, say "or". If with ALL, say "and". Name every condition. Do not
soften, summarise away, or add requirements the logic does not contain. If the logic tests
only one thing, say only that one thing."""

COMPARE_SCHEMA = {
    "type": "object",
    "properties": {
        "missing_from_rule": {"type": "string"},
        "extra_in_rule":     {"type": "string"},
        "faithful":          {"type": "boolean"},
        "severity":          {"type": "string", "enum": ["none", "minor", "material"]},
        "explanation":       {"type": "string"},
    },
    "required": ["missing_from_rule", "extra_in_rule", "faithful", "severity", "explanation"],
    "additionalProperties": False,
}

COMPARE_SYSTEM = """You compare a policy sentence against a description of the rule built from it.

The description was written by someone who could see only the rule's logic, never the
policy. Your job is to find places where the rule would DECIDE A CLAIM DIFFERENTLY from
what the policy requires.

You are not proofreading for completeness. A rule is a test over structured claim data,
not a restatement of the sentence, and it is expected to be far shorter than the prose.

A CLAIM FIELD IS A PROXY FOR A WHOLE CLAUSE. A boolean named in_person_visit_within_6mo
stands for the entire clause about a treating practitioner conducting an in-person visit
within six months. The rule referencing that field HAS captured the requirement. Do not
report the surrounding narrative as missing.

THESE ARE NOT OMISSIONS, and must be reported as "none":
  - narrative context describing why or how something is done ("to evaluate their diabetes
    control", "by the beneficiary", "on the basis of testing results")
  - pointers to external material ("refer to the ICD-10 code list in the Policy Article")
  - who performed an action, when a field already records that it happened
  - documentation, record-keeping or supplier-conduct language
  - anything the available claim fields simply cannot express

THESE ARE MATERIAL OMISSIONS:
  - a dropped ALTERNATIVE. The policy says "A or B" and the rule tests only A. This makes
    the rule too strict and denies claims that qualify through B. It is the single most
    important thing to catch.
  - a dropped or altered THRESHOLD, count, quantity or time window
  - a dropped QUALIFIER that changes who qualifies, such as "Medicare-covered"
  - a condition with its own available claim field that the rule ignores entirely
  - a condition the rule tests that the policy does not state at all

You will be shown the claim fields that exist. Something can only be a material omission
if a field exists that could have expressed it.

missing_from_rule: material omissions only, or "none".
extra_in_rule: conditions the rule tests that the policy does not state, or "none".
faithful: true when both are "none".
severity: "none" when faithful. "minor" for wording differences that change no claim
outcome. "material" when some claim would be decided differently."""


def decompile(rule: dict, tag: str = "") -> str:
    """Render a rule's logic as prose, without showing the model the source sentence."""
    logic = rule["logic"]
    payload = {
        "applies_when": logic["applies_when"],
        "requires": logic["requires"],
        "combinator_for_requires": logic["combinator"],
        "action_if_requirements_not_met": logic["on_fail"],
    }
    parsed, _ = chat_json(DECOMPILE_SYSTEM,
                          f"Rule logic:\n{json.dumps(payload, indent=2)}",
                          DECOMPILE_SCHEMA, "decompile", run_tag=tag)
    return parsed["plain_english"]


def check(rule: dict, tag: str = "") -> dict:
    """Full round trip for one rule. Returns the rendering plus the comparison."""
    from .rules import ALLOWED_FIELDS

    rendered = decompile(rule, tag=f"dc-{tag}")
    parsed, _ = chat_json(
        COMPARE_SYSTEM,
        f"POLICY SENTENCE\n\"{rule['source_sentence']}\"\n\n"
        f"DESCRIPTION OF THE RULE BUILT FROM IT\n\"{rendered}\"\n\n"
        f"CLAIM FIELDS THAT EXIST (nothing outside this list can be encoded)\n"
        f"{', '.join(ALLOWED_FIELDS)}",
        COMPARE_SCHEMA, "roundtrip", run_tag=f"cmp-{tag}")
    return {"rule_id": rule["rule_id"], "title": rule.get("title", ""),
            "source_sentence": rule["source_sentence"], "decompiled": rendered, **parsed}


def check_all(rules: list, prefix: str = "") -> list:
    return [check(r, tag=f"{prefix}{r['rule_id']}") for r in rules]
