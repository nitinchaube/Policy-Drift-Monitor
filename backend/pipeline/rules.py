"""Rule extraction and the validation gauntlet.

The model authors rules; nothing here lets it decide a claim. Everything it produces
is a proposal that has to survive validation before it reaches the engine.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .engine import OPS
from .llm import chat_json
from .pdf_ingest import locate

DATA = Path(__file__).resolve().parent.parent / "data"
SCHEMA = json.loads((DATA / "claim_schema.json").read_text())

ALLOWED_FIELDS = sorted(list(SCHEMA["top_level"]) + list(SCHEMA["attributes"]))
FIELD_TYPES = {**SCHEMA["top_level"], **SCHEMA["attributes"]}
FIELD_ENUMS = SCHEMA.get("enums", {})
KNOWN_CODES = sorted(k for k in SCHEMA["codes"] if not k.startswith("_"))

IDENTIFIER_FIELDS = {"claim_id", "date_of_service"}
LIST_OPS = {"contains_any"}
NUM_OPS = {">=", "<=", ">", "<"}
BOOL_OPS = {"is_true", "is_false"}


# --------------------------------------------------------------------------- schema
CONDITION = {
    "type": "object",
    "properties": {
        "field":         {"type": "string"},
        "op":            {"type": "string", "enum": list(OPS)},
        "value_kind":    {"type": "string", "enum": ["none", "string", "number", "boolean", "string_list"]},
        "value_string":  {"type": ["string", "null"]},
        "value_number":  {"type": ["number", "null"]},
        "value_boolean": {"type": ["boolean", "null"]},
        "value_list":    {"type": ["array", "null"], "items": {"type": "string"}},
    },
    "required": ["field", "op", "value_kind", "value_string", "value_number", "value_boolean", "value_list"],
    "additionalProperties": False,
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {"rules": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string"}, "title": {"type": "string"},
            "summary": {"type": "string"}, "source_sentence": {"type": "string"},
            "codifiable": {"type": "boolean"},
            "logic": {"type": "object", "properties": {
                "applies_when": {"type": "array", "items": CONDITION},
                "requires":     {"type": "array", "items": CONDITION},
                "combinator":   {"type": "string", "enum": ["ALL", "ANY", "N_OF_M"]},
                "n":            {"type": ["integer", "null"]},
                "on_fail":      {"type": "string", "enum": ["DENY", "REVIEW"]}},
                "required": ["applies_when", "requires", "combinator", "n", "on_fail"],
                "additionalProperties": False}},
        "required": ["rule_id", "title", "summary", "source_sentence", "codifiable", "logic"],
        "additionalProperties": False}}},
    "required": ["rules"], "additionalProperties": False,
}


def _catalogue_line(field: str) -> str:
    line = f"   - {field} ({FIELD_TYPES[field]}"
    if field in FIELD_ENUMS:
        line += ", one of: " + ", ".join(FIELD_ENUMS[field])
    elif field == "procedure_code":
        line += ", HCPCS codes appearing in this policy: " + ", ".join(KNOWN_CODES)
    return line + ")"


# The model needs types and legal enum values, not bare field names. Handed only names,
# it emitted device_type == "cgm" and the validator rejected most of its output for a
# value it was never told was illegal. If the validator enforces the schema, the prompt
# has to state the schema.
FIELD_CATALOGUE = "\n".join(_catalogue_line(f) for f in ALLOWED_FIELDS)

EXTRACT_SYSTEM = f"""You convert health insurance coverage policy text into executable claim rules.

You will be given one section of a Medicare Local Coverage Determination. Emit one rule
for each distinct, checkable requirement or limitation the text states.

HARD CONSTRAINTS

1. source_sentence must be copied VERBATIM from the supplied text. Do not paraphrase, do
   not merge sentences, do not fix typos or drop trailing "; and,". It is checked by exact
   search and the rule is discarded if it is not found.

2. Every `field` must come from this list and nothing else. The type is given, and where a
   field has a fixed set of legal values those are the ONLY values you may use for it:
{FIELD_CATALOGUE}

3. applies_when gates the rule. A rule about continuous glucose monitors must not fire on
   unrelated equipment. Use procedure_code and/or device_type.

4. requires holds the actual test. on_fail is DENY when the policy states a coverage
   condition or an outright exclusion, REVIEW when claim data cannot settle it.

5. Set codifiable=false when the requirement turns on clinical judgment that a claim
   record cannot settle (phrases like "severe enough to require", "reasonable and
   necessary", "as documented in the medical record"). Those route to a human and never
   auto-deny, so use on_fail=REVIEW.

6. For an unconditional exclusion, gate it with applies_when and give it a requirement
   that can never be met, so it always denies when it applies.

7. Emit nothing for background, evidence review, or boilerplate. Zero rules is a valid
   answer for a section stating no checkable requirement.

8. Emit exactly ONE rule per numbered coverage criterion. Do not emit an aggregate rule
   restating that all criteria must be met. That is already implied by the individual
   rules, and encoding it again double-counts every requirement.

9. Never reference an identifier field (claim_id, date_of_service) inside `requires`.
   Those identify a claim, they do not test it.

10. Operators must match the field's type. contains_any is only for list fields. The
    comparison operators are only for numeric fields. is_true and is_false are only for
    boolean fields. For `in`, every value must be one the field can actually hold.

11. If a requirement cannot be expressed with the available fields, omit the rule. Do not
    approximate it with an unrelated field."""


# --------------------------------------------------------------------------- coercion
def coerce_condition(c: dict) -> dict:
    """Strict JSON schema has no union types, so `value` arrives in typed slots."""
    return {"field": c["field"], "op": c["op"], "value": {
        "none": None, "string": c["value_string"], "number": c["value_number"],
        "boolean": c["value_boolean"], "string_list": c["value_list"]}[c["value_kind"]]}


def coerce_rule(r: dict, doc_text: str, doc_id: str) -> dict:
    lg, out = r["logic"], dict(r)
    out["logic"] = {"applies_when": [coerce_condition(c) for c in lg["applies_when"]],
                    "requires":     [coerce_condition(c) for c in lg["requires"]],
                    "combinator":   lg["combinator"], "n": lg.get("n"), "on_fail": lg["on_fail"]}
    sp = locate(doc_text, r["source_sentence"])
    out["source_span"], out["source_doc"] = (list(sp) if sp else None), doc_id
    return out


def extract_rules(section_text: str, doc_text: str, doc_id: str,
                  run_tag: str = "", temperature: float = 0.0):
    user = f"Extract rules from this policy section.\n\n---\n{section_text}\n---"
    parsed, src = chat_json(EXTRACT_SYSTEM, user, EXTRACTION_SCHEMA, "rules",
                            temperature=temperature, run_tag=run_tag)
    return [coerce_rule(r, doc_text, doc_id) for r in parsed["rules"]], src


# --------------------------------------------------------------------------- validation
def validate_rule(rule: dict, doc_text: str) -> tuple:
    """Return (span, [problems]). An empty problem list means the rule may compile.

    Checking that a field merely *exists* is not enough. The extractor produced
    `claim_id contains_any ['K0554']` and `device_type in ['PDAC_approved']`, both of
    which reference real fields and are both meaningless. The claim schema already
    declares types and legal values, so enforcing it here catches that class of output
    deterministically and for free.
    """
    problems = []

    span = locate(doc_text, rule["source_sentence"])
    if span is None:
        problems.append("citation not found in source document (fabricated quote)")

    for where, conds in (("applies_when", rule["logic"]["applies_when"]),
                         ("requires", rule["logic"]["requires"])):
        for c in conds:
            f, op, val = c["field"], c["op"], c.get("value")

            if f not in ALLOWED_FIELDS:
                problems.append(f"unknown field '{f}' (not in claim schema)")
                continue
            if op not in OPS:
                problems.append(f"unsupported operator '{op}'")
                continue

            if where == "requires" and f in IDENTIFIER_FIELDS:
                problems.append(f"'{f}' is an identifier and cannot be a requirement")

            ftype = FIELD_TYPES[f]
            if op in LIST_OPS and not ftype.startswith("list"):
                problems.append(f"operator '{op}' needs a list field, but '{f}' is {ftype}")
            if op in NUM_OPS and ftype not in ("int", "number"):
                problems.append(f"operator '{op}' needs a numeric field, but '{f}' is {ftype}")
            if op in BOOL_OPS and ftype != "bool":
                problems.append(f"operator '{op}' needs a boolean field, but '{f}' is {ftype}")

            if f in FIELD_ENUMS:
                supplied = val if isinstance(val, list) else [val]
                bad = [v for v in supplied if v is not None and v not in FIELD_ENUMS[f]]
                if bad:
                    problems.append(f"value(s) {bad} are not valid for '{f}' "
                                    f"(allowed: {FIELD_ENUMS[f]})")

    if not rule["logic"]["requires"]:
        problems.append("rule has no requirements, it can never fire")
    if rule["logic"].get("combinator") == "N_OF_M" and not rule["logic"].get("n"):
        problems.append("N_OF_M combinator without n")

    return span, problems


# --------------------------------------------------------------------------- identity
# A quoted criterion may carry its list marker ("2. The beneficiary has been using..."),
# which is document formatting rather than part of the requirement. Strip it for matching
# only; source_sentence stays verbatim so it can still be located in the document.
_LIST_MARKER = re.compile(r"^\s*(?:\(?\d{1,2}[.)]|\(?[a-z][.)])\s+")


def cite_key(rule: dict) -> str:
    s = re.sub(r"\s+", " ", rule["source_sentence"]).strip().lower()
    return _LIST_MARKER.sub("", s).strip()


def norm_conditions(cs: list) -> list:
    """is_true and is_false ignore their operand, so null and true are the same condition."""
    out = []
    for c in cs:
        val = None if c["op"] in ("is_true", "is_false") else c.get("value")
        out.append(f"{c['field']}|{c['op']}|{json.dumps(val, sort_keys=True)}")
    return sorted(out)


def requires_hash(rule: dict) -> str:
    return hashlib.sha256(json.dumps(
        {"r": norm_conditions(rule["logic"]["requires"]),
         "c": rule["logic"]["combinator"]}, sort_keys=True).encode()).hexdigest()[:12]


def logic_hash(rule: dict) -> str:
    lg = rule["logic"]
    return hashlib.sha256(json.dumps(
        {"a": norm_conditions(lg["applies_when"]), "r": norm_conditions(lg["requires"]),
         "c": lg["combinator"], "n": lg.get("n"), "f": lg["on_fail"]},
        sort_keys=True).encode()).hexdigest()[:12]


def load_reference() -> list:
    """The hand-authored ruleset: gold standard for scoring, fallback when the gate fails."""
    return json.loads((DATA / "reference_ruleset.json").read_text())["rules"]


# --------------------------------------------------------------------------- ensemble
def vote_rules(runs: list[list[dict]], min_agreement: int | None = None, arbiter=None):
    """Combine several extraction runs by majority vote.

    Running extraction five times to measure stability and then keeping only the first
    run throws away four samples that were already paid for. Voting uses them.

    Identity is the cited sentence, since two rules quoting the same sentence are
    attempts at the same requirement. Among the runs that produced a rule for a given
    sentence, the most common logic wins. A tie is broken by the more specific rule, on
    the grounds that a dropped condition is the failure mode we actually see: the
    extractor omitted "or a Medicare-covered CSII pump" from one criterion, and no run
    ever invented a condition that was not there.

    Returns (voted_rules, report).
    """
    n_runs = len(runs)
    if min_agreement is None:
        min_agreement = n_runs // 2 + 1          # simple majority

    seen: dict[str, list[dict]] = {}
    for run in runs:
        for rule in run:
            seen.setdefault(cite_key(rule), []).append(rule)

    voted, report = [], []
    for key, candidates in seen.items():
        runs_with = sum(1 for run in runs if any(cite_key(r) == key for r in run))
        if runs_with < min_agreement:
            report.append({"cite": key, "runs_present": runs_with, "kept": False,
                           "reason": f"appeared in {runs_with}/{n_runs} runs, below the "
                                     f"{min_agreement}-run threshold"})
            continue

        by_logic: dict[str, list[dict]] = {}
        for r in candidates:
            by_logic.setdefault(requires_hash(r), []).append(r)

        groups = sorted(by_logic.values(), key=len, reverse=True)
        arbitrated = False
        verdicts = {}

        # Plain majority vote only corrects random variance. When the model is
        # systematically wrong in the same way across runs, the wrong answer wins the
        # vote. That is exactly what happens on the insulin criterion: the plurality
        # drops the "or a Medicare-covered CSII pump" alternative.
        #
        # So when the runs disagree, ask an arbiter to check each variant against the
        # source sentence and prefer one it finds faithful. Votes only break ties among
        # equally faithful variants.
        if arbiter and len(groups) > 1:
            for g in groups:
                verdicts[requires_hash(g[0])] = arbiter(g[0])
            faithful = [g for g in groups if verdicts.get(requires_hash(g[0])) == "none"]
            if faithful:
                best = max(faithful, key=lambda g: (len(g), len(g[0]["logic"]["requires"])))
                arbitrated = True
            else:
                best = groups[0]
        else:
            best = max(groups, key=lambda g: (len(g), len(g[0]["logic"]["requires"])))

        voted.append(best[0])
        report.append({
            "cite": key, "runs_present": runs_with, "kept": True,
            "title": best[0]["title"],
            "variants": len(by_logic),
            "winning_votes": len(best),
            "disputed": len(by_logic) > 1,
            "arbitrated": arbitrated,
            "alternatives": [
                {"votes": len(g), "requires": norm_conditions(g[0]["logic"]["requires"]),
                 "roundtrip": verdicts.get(requires_hash(g[0])),
                 "won": g is best}
                for g in groups
            ] if len(by_logic) > 1 else [],
        })

    return voted, report
