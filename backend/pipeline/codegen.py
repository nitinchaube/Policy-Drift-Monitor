"""Generate a standalone Python module from a ruleset: one function per rule, with
its source sentence in the docstring."""
from __future__ import annotations

import re
import textwrap
from datetime import date

_PY_OPS = {
    "==": "{v} == {lit}", "!=": "{v} != {lit}",
    ">=": "{v} >= {lit}", "<=": "{v} <= {lit}",
    ">":  "{v} > {lit}",  "<":  "{v} < {lit}",
    "in": "{v} in {lit}", "not_in": "{v} not in {lit}",
    "contains_any": "bool(set({v} or []) & set({lit}))",
    "is_true": "{v} is True", "is_false": "{v} is False",
}


def _fn_name(rule_id: str) -> str:
    return "rule_" + re.sub(r"[^0-9a-z]+", "_", rule_id.lower()).strip("_")


def _condition(cond: dict) -> str:
    value = cond.get("value")
    lit = repr(tuple(value)) if isinstance(value, list) else repr(value)
    return _PY_OPS[cond["op"]].format(v=f"get(claim, {cond['field']!r})", lit=lit)


def _join(conds: list, combinator: str, n: int | None) -> str:
    parts = [_condition(c) for c in conds]
    if not parts:
        return "True"
    if combinator == "ANY":
        return " or ".join(parts)
    if combinator == "N_OF_M":
        return f"sum([{', '.join(parts)}]) >= {n}"
    return " and ".join(parts)


def generate(rules: list, doc_label: str, effective: str) -> str:
    lines = [
        '"""Claim rules generated from a Medicare coverage policy.',
        "",
        f"Source document : {doc_label}",
        f"Effective       : {effective}",
        f"Generated       : {date.today().isoformat()}",
        "",
        "No LLM calls in this file -- rules were authored upstream, this just runs them.",
        "Each function returns None (not applicable), \"PASS\", \"DENY\", or \"REVIEW\"",
        "(requirement met, failed, or the claim is missing a field it needs). Missing",
        "data never returns DENY.",
        '"""',
        "",
        "",
        "def get(claim, field):",
        '    """Claims are shallow-nested: top level plus an attributes bag."""',
        "    if field in claim:",
        "        return claim[field]",
        '    return claim.get("attributes", {}).get(field)',
        "",
        "",
        "def _missing(claim, fields):",
        "    return [f for f in fields if get(claim, f) is None]",
        "",
    ]

    for rule in rules:
        logic = rule["logic"]
        needed = sorted({c["field"] for c in logic["requires"]})
        citation = re.sub(r"\s+", " ", rule["source_sentence"]).strip()

        lines += ["", f"def {_fn_name(rule['rule_id'])}(claim):", '    """' + rule["title"] + ".", ""]
        lines += ["    " + ln for ln in textwrap.wrap(rule["summary"], 74)]
        lines += ["", "    Source:"]
        lines += ["    " + ln for ln in textwrap.wrap(f'"{citation}"', 74)]
        if not rule.get("codifiable", True):
            lines += ["", "    Marked non-codifiable: this requirement turns on clinical judgment",
                      "    that a claim record cannot settle, so it always routes to a human."]
        lines += ['    """']

        lines.append(f"    if not ({_join(logic['applies_when'], 'ALL', None)}):")
        lines.append("        return None")

        if not rule.get("codifiable", True):
            lines.append('    return "REVIEW"')
            lines.append("")
            continue

        lines.append(f"    missing = _missing(claim, {needed!r})")
        lines.append("    if missing:")
        lines.append('        return "REVIEW"')
        lines.append(f"    if {_join(logic['requires'], logic.get('combinator', 'ALL'), logic.get('n'))}:")
        lines.append('        return "PASS"')
        lines.append(f'    return "{logic["on_fail"]}"')
        lines.append("")

    lines += [
        "",
        "ALL_RULES = [",
        *[f"    ({rule['rule_id']!r}, {_fn_name(rule['rule_id'])})," for rule in rules],
        "]",
        "",
        "",
        "_PRECEDENCE = {\"DENY\": 3, \"REVIEW\": 2, \"PAY\": 1}",
        "",
        "",
        "def adjudicate(claim):",
        '    """Run every rule and combine outcomes: DENY beats REVIEW beats PAY.',
        "",
        "    A claim no rule objects to is paid. No rule means no basis to deny.",
        '    """',
        "    outcomes, trace = [], []",
        "    for rule_id, fn in ALL_RULES:",
        "        result = fn(claim)",
        "        if result is None or result == \"PASS\":",
        "            trace.append((rule_id, result or \"NOT_APPLICABLE\"))",
        "            continue",
        "        trace.append((rule_id, result))",
        "        outcomes.append(result)",
        "    decision = max(outcomes, key=_PRECEDENCE.get) if outcomes else \"PAY\"",
        "    return decision, trace",
        "",
    ]
    return "\n".join(lines)
