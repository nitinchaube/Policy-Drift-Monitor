"""FastAPI layer. A thin wrapper over pipeline/, which does all the actual work.

Keeping the engine independent of the web layer is deliberate: the CLI produces
identical results, which makes it a working fallback if anything breaks during a live
demo, and it keeps the interface from quietly becoming the place logic lives.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.codegen import generate           # noqa: E402
from pipeline.run import get_analysis           # noqa: E402

app = FastAPI(title="Policy Drift Monitor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    a = get_analysis()
    return {"ok": True, "model": a["model"], "cache": a["cache"],
            "llm_available": a["llm_available"], "warnings": a["warnings"]}


@app.get("/api/analysis")
def analysis():
    """Everything, in one payload. The UI fetches this once on load."""
    return get_analysis()


@app.get("/api/documents")
def documents():
    return get_analysis()["documents"]


@app.get("/api/documents/{version}")
def document(version: str):
    docs = get_analysis()["documents"]
    if version not in docs:
        raise HTTPException(404, f"unknown version {version!r}, expected one of {list(docs)}")
    return docs[version]


@app.get("/api/rules")
def rules():
    a = get_analysis()
    return {"working": a["working_ruleset"], "reference": a["reference_ruleset"],
            "extraction": a["extraction"], "gate": a["gate"],
            "score": a["extraction_score"], "stability": a["stability"]}


@app.get("/api/claims")
def claims():
    a = get_analysis()
    return {"claims": a["claims"], "rejected": a["claims_rejected"]}


@app.get("/api/adjudication")
def adjudication():
    return get_analysis()["adjudication"]


@app.get("/api/drift")
def drift():
    a = get_analysis()
    return {"verdicts": a["drift"], "gaps": a["gaps"],
            "negative_control": a["negative_control"]}


@app.get("/api/scorecard")
def scorecard():
    a = get_analysis()
    return {"scorecard": a["scorecard"], "stability": a["stability"],
            "extraction_score": a["extraction_score"], "gate": a["gate"],
            "negative_control": a["negative_control"],
            "impact": {"flips": len(a["adjudication"]["flips"]),
                       "recovered": a["adjudication"]["recovered"],
                       "claims": len(a["claims"]),
                       "rejected": len(a["claims_rejected"])}}


@app.get("/api/export/python", response_class=PlainTextResponse)
def export_python(which: str = "corrected"):
    """Generate a runnable Python module from a ruleset."""
    a = get_analysis()
    sets = {"working": (a["working_ruleset"], "LCD L33822", "2020-01-01 to 2021-07-17"),
            "corrected": (a["adjudication"]["corrected_ruleset"], "LCD L33822",
                          "2021-07-18 onward (after drift correction)"),
            "reference": (a["reference_ruleset"], "LCD L33822", "2020-01-01 to 2021-07-17")}
    if which not in sets:
        raise HTTPException(404, f"unknown ruleset {which!r}, expected one of {list(sets)}")
    rules_, label, effective = sets[which]
    return generate(rules_, label, effective)
