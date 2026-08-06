"""Orchestration: one result object, shared by the CLI and the API.

ingest both policy versions -> extract rules -> validate/score/gate the extraction
-> detect drift -> apply corrections -> re-adjudicate -> score against the CMS
revision history. Runs in a couple seconds from a warm cache, no network calls.
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path

from . import drift as drift_mod
from . import explain as explain_mod
from . import roundtrip
from .engine import adjudicate, load_claims
from .llm import NoAPIKey, cache_stats, model_name
from .pdf_ingest import canonical, coverage_text, locate, segment
from .rules import (ALLOWED_FIELDS, FIELD_CATALOGUE, cite_key, extract_rules, load_reference,
                    logic_hash, norm_conditions, requires_hash, validate_rule, vote_rules)

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "data"
PDFS = DATA / "pdfs"

V1_PDF = PDFS / "L33822_2020.pdf"
V2_PDF = PDFS / "L33822_2021.pdf"
NEG_A_PDF = PDFS / "LCD - Glucose Monitors (L33822) superseded.pdf"
NEG_B_PDF = PDFS / "LCD - Glucose Monitors (L33822).pdf"

N_STABILITY_RUNS = 5

# the human-authored fix for a REVISE-flagged rule -- keyed on the cited sentence,
# not the rule id, since a model-extracted ruleset invents its own ids
HUMAN_PATCH = {
    "the beneficiary is insulin-treated with multiple (three or more) daily injections of "
    "insulin or a medicare-covered continuous subcutaneous insulin infusion (csii) pump; and,": {
        "source_sentence": "The beneficiary is insulin-treated with multiple (three or more) daily "
                           "administrations of insulin or a continuous subcutaneous insulin "
                           "infusion (CSII) pump; and,",
        "requires": [{"field": "insulin_administrations_per_day", "op": ">=", "value": 3},
                     {"field": "csii_pump", "op": "is_true", "value": None}],
        "note": "injections became administrations, and 'Medicare-covered' was dropped from the pump test",
    }
}

_norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()


def _cgm_section(text: str) -> dict:
    return next(s for s in segment(text) if s["name"].startswith("CONTINUOUS GLUCOSE"))


def analyze() -> dict:
    out: dict = {"model": model_name(), "cache": cache_stats(), "llm_available": True, "warnings": []}

    # ---------------------------------------------------------------- 1. ingest
    v1_text, v2_text = coverage_text(V1_PDF), coverage_text(V2_PDF)
    v1_cgm = _cgm_section(v1_text)

    out["documents"] = {
        "v1": {"id": "L33822-2020", "label": "LCD L33822", "effective": "2020-01-01",
               "ends": "2021-07-17", "pdf": V1_PDF.name, "text": v1_text,
               "sections": [{k: s[k] for k in ("name", "start", "end")} for s in segment(v1_text)]},
        "v2": {"id": "L33822-2021", "label": "LCD L33822", "effective": "2021-07-18",
               "ends": "2022-02-27", "pdf": V2_PDF.name, "text": v2_text,
               "sections": [{k: s[k] for k in ("name", "start", "end")} for s in segment(v2_text)]},
    }

    # ---------------------------------------------------------------- 2. reference
    reference = load_reference()
    for r in reference:
        span = locate(v1_text, r["source_sentence"])
        r["source_span"], r["source_doc"] = (list(span) if span else None), "L33822-2020"
    out["reference_ruleset"] = reference

    # ---------------------------------------------------------------- 3. extract
    # five runs, needed anyway for stability -- also used as a voting ensemble for free
    runs, single_run, rejected = [], [], []
    try:
        raw, _ = extract_rules(v1_cgm["text"], v1_text, "L33822-2020", run_tag="run0")
        for r in raw:
            _, problems = validate_rule(r, v1_text)
            (single_run if not problems else rejected).append(
                r if not problems else {**r, "problems": problems})

        for i in range(N_STABILITY_RUNS):
            rs, _ = extract_rules(v1_cgm["text"], v1_text, "L33822-2020", run_tag=f"stability{i}")
            runs.append([r for r in rs if not validate_rule(r, v1_text)[1]])
    except NoAPIKey as e:
        out["llm_available"] = False
        out["warnings"].append(str(e))

    if len(runs) == N_STABILITY_RUNS:
        def arbiter(candidate):
            """Round-trip severity for one candidate encoding of a disputed rule."""
            try:
                return roundtrip.check(
                    candidate, tag=f"arb-{requires_hash(candidate)}")["severity"]
            except NoAPIKey:
                return None

        extracted, vote_report = vote_rules(runs, arbiter=arbiter)
        n_arb = sum(1 for v in vote_report if v.get("arbitrated"))
        extraction_method = (f"majority vote across {N_STABILITY_RUNS} runs"
                             + (f", {n_arb} dispute(s) settled by round-trip verification"
                                if n_arb else ""))
    else:
        extracted, vote_report = single_run, []
        extraction_method = "single run"

    out["extraction"] = {"accepted": extracted, "rejected": rejected,
                         "single_run": single_run, "method": extraction_method,
                         "vote_report": vote_report,
                         "section": {"name": v1_cgm["name"], "start": v1_cgm["start"],
                                     "end": v1_cgm["end"]}}

    # ------------------------------------------------- 3b. round-trip verification
    # decompile each rule back to prose (source sentence withheld) and compare --
    # needs no gold ruleset, unlike the scoring below
    roundtrip_findings = []
    if extracted:
        try:
            roundtrip_findings = roundtrip.check_all(extracted, prefix="v1-")
        except NoAPIKey as e:
            out["warnings"].append(f"round-trip verification unavailable: {e}")
    out["roundtrip"] = roundtrip_findings

    # ---------------------------------------------------------------- 4. stability
    stability = None
    if len(runs) == N_STABILITY_RUNS:
        seen = Counter()
        titles = {}
        for rs in runs:
            for r in rs:
                titles.setdefault(cite_key(r), r["title"])
            for k in {cite_key(r) for r in rs}:
                seen[k] += 1
        stability = {
            "runs": N_STABILITY_RUNS,
            "rules": [{"cite": k, "title": titles.get(k, ""), "agreement": n,
                       "unanimous": n == N_STABILITY_RUNS} for k, n in seen.most_common()],
            "unanimous": sum(1 for n in seen.values() if n == N_STABILITY_RUNS),
            "distinct": len(seen),
        }
    out["stability"] = stability

    # ---------------------------------------------------------------- 5. score + gate
    gold_by_cite = {cite_key(r): r for r in reference}
    in_scope = {k: r for k, r in gold_by_cite.items()
                if locate(v1_cgm["text"], r["source_sentence"])}

    score, gate_reasons = None, []
    if extracted:
        got = {cite_key(r): r for r in extracted}
        matched, used, by_logic = {}, set(), []

        for k in in_scope:
            if k in got:
                matched[k] = got[k]
                used.add(k)
        # second pass on identical logic: a paragraph can state one requirement twice,
        # and the model may cite the other sentence than gold did
        for k, gold_rule in in_scope.items():
            if k in matched:
                continue
            gh = requires_hash(gold_rule)
            for gk, got_rule in got.items():
                if gk not in used and requires_hash(got_rule) == gh:
                    matched[k], _ = got_rule, used.add(gk)
                    by_logic.append({"gold_cites": k, "model_cites": gk})
                    break

        found = sorted(matched)
        missed = [k for k in in_scope if k not in matched]
        spurious = [k for k in got if k not in gold_by_cite and k not in used]
        same_req = [k for k in found if requires_hash(matched[k]) == requires_hash(in_scope[k])]
        same_all = [k for k in found if logic_hash(matched[k]) == logic_hash(in_scope[k])]

        score = {
            "in_scope": len(in_scope), "document_wide": len(gold_by_cite),
            "found": len(found), "same_requirements": len(same_req), "identical": len(same_all),
            "missed": [{"cite": k, "title": in_scope[k]["title"]} for k in missed],
            "beyond_gold": [{"cite": k, "title": got[k]["title"]} for k in spurious],
            "spurious": [],
            "matched_by_logic": by_logic,
            "differences": [{"title": in_scope[k]["title"],
                             "gold": norm_conditions(in_scope[k]["logic"]["requires"]),
                             "model": norm_conditions(matched[k]["logic"]["requires"])}
                            for k in found if k not in same_req],
        }
        # a model rule citing a real, verified sentence not in gold isn't spurious --
        # it's a rule the human author missed, so it isn't gated on
        if len(found) < len(in_scope):
            gate_reasons.append(f"only found {len(found)} of {len(in_scope)} in-scope gold rules")
        if len(same_req) < len(found):
            gate_reasons.append(f"{len(found) - len(same_req)} rule(s) encode different "
                                f"requirements than gold")
    else:
        gate_reasons.append("no model output available")

    material = [f for f in roundtrip_findings if f.get("severity") == "material"]
    if material:
        gate_reasons.append(f"{len(material)} rule(s) failed round-trip verification with a "
                            f"material omission")

    working = reference if gate_reasons else extracted
    out["extraction_score"] = score
    out["gate"] = {"passed": not gate_reasons, "reasons": gate_reasons,
                   "ruleset_used": "hand-authored reference" if gate_reasons else "model-extracted"}
    out["working_ruleset"] = working

    # ---------------------------------------------------------------- 6. drift
    verdicts = []
    try:
        for r in working:
            v, _ = drift_mod.check_drift(r, v2_text, tag=f"2020to2021-{r['rule_id']}")
            verdicts.append(v)
    except NoAPIKey as e:
        out["warnings"].append(f"drift unavailable: {e}")
    out["drift"] = verdicts

    # ---------------------------------------------------------------- 7. negative control
    a, b = coverage_text(NEG_A_PDF), coverage_text(NEG_B_PDF)
    flat = lambda s: re.sub(r"\s+", " ", s).strip()
    out["negative_control"] = {
        "from": {"pdf": NEG_A_PDF.name, "effective": "2024-04-01", "ends": "2024-09-30",
                 "chars": len(a)},
        "to": {"pdf": NEG_B_PDF.name, "effective": "2024-10-01", "ends": None, "chars": len(b)},
        "tier0_bytes_identical": a == b,
        "tier1_whitespace_collapsed_identical": flat(a) == flat(b),
        "tier1b_canonical_identical": canonical(a) == canonical(b),
        "cms_revision_text": "Revision Effective Date: 10/01/2024. HCPCS CODES: Revised: "
                             "Long descriptor for HCPCS code A4271 in Group 2 Codes",
        "model_calls_needed": 0,
    }

    # ---------------------------------------------------------------- 8. gaps
    try:
        gaps, _ = drift_mod.find_gaps(working, v2_text, tag="v2gap")
        out["gaps"] = gaps
    except NoAPIKey:
        out["gaps"] = []

    # ---------------------------------------------------------------- 9. impact
    retire = {v["rule_id"] for v in verdicts if v["recommended_action"] == "RETIRE"}
    revise = {v["rule_id"] for v in verdicts if v["recommended_action"] == "REVISE"}

    # deepcopy: HUMAN_PATCH edits in place, and without a copy it'd corrupt the
    # baseline via shared dict references
    corrected = [copy.deepcopy(r) for r in working if r["rule_id"] not in retire]
    patches = []
    for r in corrected:
        patch = HUMAN_PATCH.get(cite_key(r))
        if patch and r["rule_id"] in revise:
            r["logic"]["requires"] = patch["requires"]
            r["source_sentence"] = patch["source_sentence"]
            span = locate(v2_text, patch["source_sentence"])
            r["source_span"], r["source_doc"] = (list(span) if span else None), "L33822-2021"
            patches.append({"rule_id": r["rule_id"], "note": patch["note"]})

    claims, claims_rejected = load_claims(DATA / "claims.json")
    before = {c["claim_id"]: adjudicate(c, working) for c in claims}
    after = {c["claim_id"]: adjudicate(c, corrected) for c in claims}
    amounts = {c["claim_id"]: c["billed_amount"] for c in claims}

    def tally(res):
        t = {"PAY": 0, "DENY": 0, "REVIEW": 0}
        for r in res.values():
            t[r["decision"]] += 1
        return t

    flips, recovered = [], 0.0
    for cid in sorted(before):
        was, now = before[cid]["decision"], after[cid]["decision"]
        if was == now:
            continue
        if was == "DENY" and now == "PAY":
            recovered += amounts[cid]
        flips.append({"claim_id": cid, "was": was, "now": now, "amount": amounts[cid],
                      "caused_by": [f["rule_id"] for f in before[cid]["fired"]
                                    if f["rule_id"] in retire | revise]})

    out["claims"] = claims
    out["claims_rejected"] = [{"claim_id": c, "reason": w} for c, w in claims_rejected]
    out["adjudication"] = {
        "before": before, "after": after,
        "tally_before": tally(before), "tally_after": tally(after),
        "flips": flips, "recovered": round(recovered, 2),
        "retired": sorted(retire), "revised": sorted(revise), "human_patches": patches,
        "corrected_ruleset": corrected,
    }

    # ------------------------------------------------ 9b. provider explanations
    # generated for every non-PAY claim, plus every claim that flipped
    explanations = {"before": {}, "after": {}}
    flipped_ids = {f["claim_id"] for f in flips}
    try:
        for c in claims:
            cid = c["claim_id"]
            if before[cid]["decision"] != "PAY":
                explanations["before"][cid] = explain_mod.explain(c, before[cid], tag=f"before-{cid}")
            if cid in flipped_ids:
                explanations["after"][cid] = explain_mod.explain(c, after[cid], tag=f"after-{cid}")
    except NoAPIKey as e:
        out["warnings"].append(f"explanations unavailable: {e}")
    out["explanations"] = explanations

    # ---------------------------------------------------------------- 10. scorecard
    gold = json.loads((DATA / "gold_revision_history.json").read_text())
    by_rule = {v["rule_id"]: v for v in verdicts}
    cite2rid = {cite_key(r): r["rule_id"] for r in working}

    affected, changes = set(), []
    for ch in gold["documented_changes"]:
        if not ch["scoreable"]:
            continue
        rid = cite2rid.get(_norm(ch["affects_source_sentence_v1"]))
        affected.add(rid)
        got_v = by_rule.get(rid, {}).get("verdict")
        changes.append({"change_id": ch["change_id"], "revision_text": ch["revision_text"],
                        "expected": ch["expected_verdict"], "got": got_v,
                        "rule_id": rid, "hit": got_v == ch["expected_verdict"]})

    must_not = []
    for mn in gold.get("must_not_flag", []):
        rid = cite2rid.get(_norm(mn["source_sentence_v1"]))
        got_v = by_rule.get(rid, {}).get("verdict")
        must_not.append({"case_id": mn["case_id"], "rule_id": rid, "why": mn["why"],
                         "expected": mn["expected_verdict"], "got": got_v,
                         "passed": got_v == mn["expected_verdict"]})

    out["scorecard"] = {
        "revision_effective_date": gold["revision_effective_date"],
        "documented_changes": changes,
        "caught": sum(1 for c in changes if c["hit"]),
        "total_changes": len(changes),
        "must_not_flag": must_not,
        "false_alarms": [{"rule_id": v["rule_id"], "verdict": v["verdict"]} for v in verdicts
                         if v["rule_id"] not in affected and v["verdict"] != "SUPPORTED"],
        "excluded": gold.get("excluded_from_scoring", []),
        "scoring_notes": gold["scoring_notes"],
    }
    return out


_CACHED: dict | None = None


def get_analysis(refresh: bool = False) -> dict:
    global _CACHED
    if _CACHED is None or refresh:
        _CACHED = analyze()
    return _CACHED
