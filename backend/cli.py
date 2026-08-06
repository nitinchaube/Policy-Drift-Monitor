"""Headless run of the whole analysis.

Produces the same results as the notebook and the web app. Two reasons this exists:
it is a working fallback if the UI breaks during a live demo, and keeping the engine
runnable without the web layer stops logic from migrating into the interface.

    python -m cli                    full report
    python -m cli --json out.json    dump the raw result
    python -m cli --export rules.py  generate a Python module from the corrected ruleset
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from textwrap import shorten

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.codegen import generate     # noqa: E402
from pipeline.run import analyze          # noqa: E402

BAR = "=" * 78


def report(a: dict) -> None:
    print(BAR)
    print("POLICY DRIFT MONITOR")
    print(BAR)
    d1, d2 = a["documents"]["v1"], a["documents"]["v2"]
    print(f"  v1     {d1['label']}  effective {d1['effective']} to {d1['ends']}  "
          f"({len(d1['text']):,} chars of coverage text)")
    print(f"  v2     {d2['label']}  effective {d2['effective']} to {d2['ends']}  "
          f"({len(d2['text']):,} chars)")
    print(f"  model  {a['model']}   cache: {a['cache']['entries']} entries, "
          f"{a['cache']['prompt_tokens']:,} prompt tokens")
    for w in a["warnings"]:
        print(f"  WARNING: {w}")

    print(f"\n{BAR}\nEXTRACTION\n{BAR}")
    ex, sc = a["extraction"], a["extraction_score"]
    print(f"  accepted {len(ex['accepted'])}, rejected {len(ex['rejected'])} by validation")
    for r in ex["rejected"]:
        print(f"    {r['rule_id']}: {r['problems']}")
    if sc:
        print(f"  vs gold  found {sc['found']}/{sc['in_scope']} in-scope rules, "
              f"{sc['same_requirements']} with identical requirements, "
              f"{sc['identical']} identical throughout")
        print(f"           {len(sc['missed'])} missed, {len(sc['spurious'])} spurious")
        for m in sc["matched_by_logic"]:
            print(f"    matched by identical logic despite a different citation:")
            print(f"       gold  cites \"{shorten(m['gold_cites'], 58)}\"")
            print(f"       model cites \"{shorten(m['model_cites'], 58)}\"")
        for d in sc["differences"]:
            print(f"    DIFFERENT REQUIREMENTS: {d['title']}")
            print(f"       gold : {d['gold']}")
            print(f"       model: {d['model']}")
    if a["stability"]:
        s = a["stability"]
        print(f"  stability {s['unanimous']}/{s['distinct']} rules unanimous across {s['runs']} runs")
        for r in s["rules"]:
            if not r["unanimous"]:
                print(f"    {r['agreement']}/{s['runs']}  {shorten(r['title'] or r['cite'], 60)}")

    g = a["gate"]
    print(f"\n  GATE: {'PASSED' if g['passed'] else 'FAILED'}")
    for r in g["reasons"]:
        print(f"    - {r}")
    print(f"  ruleset carried downstream: {g['ruleset_used']} ({len(a['working_ruleset'])} rules)")

    print(f"\n{BAR}\nDRIFT  (rule set held fixed, each rule classified against v2)\n{BAR}")
    print(f"  {'rule':<10} {'present?':<9} {'in list?':<9} {'affects':<8} | "
          f"{'VERDICT':<14} {'action':<13} cite")
    print("  " + "-" * 74)
    for v in a["drift"]:
        print(f"  {v['rule_id']:<10} {str(v['requirement_still_present']):<9} "
              f"{str(v['was_item_in_criteria_list']):<9} "
              f"{str(v['changes_what_claims_qualify']):<8} | "
              f"{v['verdict']:<14} {v['recommended_action']:<13} {v['verified']}")
    for v in a["drift"]:
        if v["verdict"] != "SUPPORTED":
            print(f"\n  {v['rule_id']}: {shorten(v['wording_differences'], 90)}")

    n = a["negative_control"]
    print(f"\n{BAR}\nNEGATIVE CONTROL  ({n['from']['effective']} vs {n['to']['effective']})\n{BAR}")
    print(f"  tier 0  bytes identical              {n['tier0_bytes_identical']}")
    print(f"  tier 1  whitespace collapsed equal   {n['tier1_whitespace_collapsed_identical']}")
    print(f"  tier 1b canonical equal              {n['tier1b_canonical_identical']}")
    print(f"  model calls spent: {n['model_calls_needed']}")
    print(f"  CMS says: {n['cms_revision_text']}")

    print(f"\n{BAR}\nGAPS  (requirements in v2 no rule covers)\n{BAR}")
    print(f"  {len(a['gaps'])} found")
    for gp in a["gaps"][:5]:
        print(f"    - {shorten(gp['requirement'], 88)}")
    if len(a["gaps"]) > 5:
        print(f"    ... and {len(a['gaps']) - 5} more")

    adj = a["adjudication"]
    print(f"\n{BAR}\nIMPACT\n{BAR}")
    print(f"  retired: {adj['retired'] or 'none'}   revised: {adj['revised'] or 'none'}")
    for p in adj["human_patches"]:
        print(f"  human patch on {p['rule_id']}: {p['note']}")
    b, af = adj["tally_before"], adj["tally_after"]
    print(f"\n  {'':10} {'PAY':>5} {'DENY':>5} {'REVIEW':>7}")
    print(f"  {'before':<10} {b['PAY']:>5} {b['DENY']:>5} {b['REVIEW']:>7}")
    print(f"  {'after':<10} {af['PAY']:>5} {af['DENY']:>5} {af['REVIEW']:>7}")
    print(f"\n  {'claim':<8} {'was':<8} {'now':<8} {'amount':>10}   caused by")
    print("  " + "-" * 62)
    for f in adj["flips"]:
        print(f"  {f['claim_id']:<8} {f['was']:<8} {f['now']:<8} {f['amount']:>10,.2f}   "
              f"{', '.join(f['caused_by']) or 'ruleset changed'}")
    print(f"\n  {len(adj['flips'])} of {len(a['claims'])} claims changed decision")
    print(f"  ${adj['recovered']:,.2f} wrongly withheld across the DENY to PAY flips")

    s = a["scorecard"]
    print(f"\n{BAR}\nSCORECARD  vs the revision history CMS published inside the LCD\n{BAR}")
    for c in s["documented_changes"]:
        print(f"  [{'HIT ' if c['hit'] else 'MISS'}] {c['change_id']}: {shorten(c['revision_text'], 56)}")
        print(f"         expected {c['expected']:<13} got {c['got']}  (rule {c['rule_id']})")
    print(f"\n  caught {s['caught']} of {s['total_changes']} documented edits")
    for m in s["must_not_flag"]:
        print(f"  [{'PASS' if m['passed'] else 'FAIL'}] must-not-flag {m['case_id']} "
              f"(rule {m['rule_id']}): expected {m['expected']}, got {m['got']}")
    print(f"  false alarms: {len(s['false_alarms'])}")
    for f in s["false_alarms"]:
        print(f"    {f['rule_id']}: {f['verdict']}")
    print(f"\n  note: {s['scoring_notes']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Policy Drift Monitor, headless")
    ap.add_argument("--json", metavar="PATH", help="write the raw result object here")
    ap.add_argument("--export", metavar="PATH", help="generate a Python rules module here")
    ap.add_argument("--quiet", action="store_true", help="suppress the printed report")
    args = ap.parse_args()

    a = analyze()
    if not args.quiet:
        report(a)
    if args.json:
        Path(args.json).write_text(json.dumps(a, indent=2))
        print(f"\nwrote {args.json}")
    if args.export:
        code = generate(a["adjudication"]["corrected_ruleset"], "LCD L33822",
                        "2021-07-18 onward (after drift correction)")
        Path(args.export).write_text(code)
        print(f"wrote {args.export}")


if __name__ == "__main__":
    main()
