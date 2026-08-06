# Policy Drift Monitor

Cotiviti intern assessment, Topic 3: Content Management in Health Care.

A payer reads a coverage policy, writes claim rules from it, and puts those rules into
production. Then the policy gets revised and the rules do not. This finds the rules that
went stale, and prices what they cost in claim decisions.

Everything here runs on real CMS documents. The evaluation set comes from the revision
history CMS publishes inside the policy itself, so none of the ground truth was authored
by me.

## What it does

1. Reads a Medicare coverage determination out of the PDF, preserving character offsets.
2. Converts the prose into executable rules. Every rule quotes the sentence it came from,
   and that quote is verified by exact search against the document.
3. Compiles the rules and adjudicates claims. No model anywhere in the decision path.
4. When a revised version arrives, classifies each existing rule against it, then re-runs
   the same claims to show which decisions change and what that is worth.

## Results

| | |
|---|---|
| Documented policy changes caught | 3 of 3 |
| False alarms | 0 |
| Must-not-flag traps passed | 1 of 1 |
| Negative control (real 2024 version pair) | 0 findings, 0 model calls spent |
| Claims changed by drift correction | 6 of 20 |
| Wrongly withheld | $1,208.71 |
| Extraction vs a hand-authored ruleset | 7 of 7 rules, same requirements |

The extraction quality gate still **fails**, on two rules with material omissions found by
round-trip verification. That is reported rather than suppressed, and it is why the
hand-authored ruleset is what feeds drift detection. See "Known limitations" below.

## Running it

Python 3.12 and Node 20. Install:

```bash
pip install -r requirements.txt
```

Headless, prints the whole analysis:

```bash
cd backend && python3 -m cli
```

Generate a runnable Python rules module from the corrected ruleset:

```bash
cd backend && python3 -m cli --quiet --export rules.py
```

The web app is two processes. Backend:

```bash
cd backend && python3 -m uvicorn api.main:app --port 8000
```

Frontend:

```bash
cd frontend && npm install && npm run dev
```

Then open `http://localhost:5173`. Vite binds IPv6 here, so use `localhost`, not
`127.0.0.1`.

**No API key and no source PDFs are needed.** Every model response is cached in
`backend/cache/`, and the coverage-criteria text is committed in `backend/data/extracted/`,
so the whole analysis replays offline from a clean clone and produces identical numbers. To
re-run the model stages for real, copy `backend/.env.example` to `backend/.env` and add a
key.

The PDFs themselves are deliberately not published: every CMS coverage document carries an
AMA notice covering CPT content in its code-list sections. See `backend/data/pdfs/README.md`
for retrieval instructions and for the assertions that verify the committed text is
CPT-free.

## Layout

```
notebooks/01_pipeline_walkthrough.ipynb   the pipeline built one stage at a time, with
                                          no AI at all until section 5
backend/pipeline/                         pdf_ingest, engine, rules, drift, roundtrip,
                                          explain, codegen, run
backend/api/                              FastAPI, a thin wrapper over pipeline/
backend/data/extracted/                   coverage-criteria text, CPT-free, committed
backend/data/pdfs/                        source PDFs, NOT committed, see pdfs/README.md
backend/cache/                            cached model responses, committed on purpose
frontend/                                 Vite + React, four screens
report/Report.docx                        two pages plus APA bibliography
slides/Presentation.pptx                  twelve slides
video/VIDEO_SCRIPT.md                     timed script for the recording
```

The notebook is the artifact to read first. Sections 1 to 4 use no AI whatsoever: you load
a real PDF, hand-write a rule, and build the adjudication engine yourself, so that by the
time a model appears in section 5 you already know exactly what shape it has to produce.

## Design decisions worth defending

**The model authors rules. Ordinary code executes them.** A denial has to be reproducible,
identical every time, and defensible three years later on appeal. A model in the decision
path gives you none of those.

**Citations are verified, never trusted.** Models are unreliable at counting characters and
reliable at quoting text. So the model quotes a sentence and the code goes and finds it. An
unfindable quote is a fabricated citation and the rule is discarded.

**The claim schema is the validator.** Checking that a field exists is not enough. The
extractor produced `claim_id contains_any ["K0554"]`, which references a real field and is
meaningless. Type and range checks against the schema catch that class of output for free.

**Missing data never denies.** Evaluation is three-valued. If a claim lacks a field a rule
needs, the answer is "we cannot tell", which routes to a human. Absence of evidence is not
evidence of ineligibility.

**The model reports facts; a decision table derives the verdict.** Asking the drift detector
for a verdict directly made it miss a wording change that altered eligibility. Forcing a
word-by-word diff first made it over-sensitive to renumbering. Separating observation from
judgement fixed both. Never ask a model for a conclusion you can compute from its inputs.

**Drift is classification, not re-extraction.** Extracting from both versions and diffing
would fill the results with the extractor's own nondeterminism rather than actual policy
change.

**No vector database.** The corpus is a handful of documents and retrieval here is
structural, from document to span to rule. Reaching for a vector store because the project
involves documents would have been the wrong instinct.

## Known limitations

- n is tiny. Three documented edits, twenty synthetic claims, one document pair. This
  demonstrates behaviour; it is not statistically meaningful.
- One clinical area, one document format, one payer. Nothing here shows it generalises.
- The hand-authored ruleset and the claims were written by the same person who built the
  extractor, so only the CMS revision history is genuinely independent.
- Two rules fail round-trip verification. One encodes a per-30-day limit the claim schema
  cannot express, which is a real gap in the schema rather than in the model.
- No OCR. Every source PDF here has a text layer.
- No database, no promotion pipeline, no tier-2 triage classifier. All described in the
  report, none built.
- Payer-provider contracts are not covered at all. No public corpus exists and fabricating
  inputs would have made the whole thing worthless.

## Data and licensing

See `backend/data/SOURCES.md` for every document, where it came from, and when it was
retrieved. Short version: HCPCS Level II and ICD-10-CM are public and used freely. **CPT is
AMA-copyrighted and no CPT descriptors appear anywhere in this repository**, which is part
of why durable medical equipment policy was chosen for a public demonstration. Claims are
synthetic; no real patient or provider data is present.
