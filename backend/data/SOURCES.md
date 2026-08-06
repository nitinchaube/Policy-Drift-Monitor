# Data sources

Every file in this directory, where it came from, and what it is used for.

## Policy documents

All six PDFs were retrieved manually through a browser on 2026-08-05. CMS returns HTTP 403
to programmatic fetches, and the Coverage API (`api.coverage.cms.gov`) requires a bearer
token obtained by accepting the AMA, ADA, and AHA license agreements, so the repository
author accepted those terms and downloaded the documents directly.

Landing page: https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33822
Prior versions: https://localcoverage.cms.gov/mcd_archive

| File | Document | Effective | Ends | Used for |
|---|---|---|---|---|
| `pdfs/L33822_2020.pdf` | LCD L33822, Glucose Monitors | 01/01/2020 | 07/17/2021 | **v1.** Rules are derived from this version |
| `pdfs/L33822_2021.pdf` | LCD L33822 | 07/18/2021 | 02/27/2022 | **v2.** Drift is detected against this version |
| `pdfs/LCD - Glucose Monitors (L33822) superseded.pdf` | LCD L33822 | 04/01/2024 | 09/30/2024 | negative control, "before" |
| `pdfs/LCD - Glucose Monitors (L33822).pdf` | LCD L33822 | 10/01/2024 | current | negative control, "after" |
| `pdfs/Article - Glucose Monitor - Policy Article (A52464).pdf` | Local Coverage Article A52464 | 02/18/2025 | current | HCPCS code lists and coding period rules |
| `pdfs/adaStandardsOfCareSec7.pdf` | ADA Standards of Care in Diabetes 2026, Section 7, Diabetes Technology | 2026 | | clinical guideline cross-check |

### Why this version pair

The 07/18/2021 revision changed three things in the CGM coverage criteria, all stated
verbatim in the LCD's own Revision History Information table:

1. Removed the requirement that the beneficiary was testing with a BGM four or more times
   a day.
2. Changed "three or more daily **injections** of insulin" to "**administrations**".
3. Removed "**Medicare-covered**" from the CSII pump criterion.

It also renumbered the criteria list from six items to five, which changed a
cross-reference from "criteria (1-4)" to "criteria (1-3)" without changing any
requirement. That renumbering is the sharpest false-positive trap in the pair, and it came
from the source rather than being constructed.

### Why the 2024 pair is the negative control

Between 04/01/2024 and 10/01/2024 the only revision was a HCPCS long-descriptor change to
code A4271, which lives outside the coverage criteria. With whitespace removed, the
coverage text of the two versions is byte-identical at 12,917 characters. It is a genuine
no-change control, which is stronger than a synthetic perturbation.

Note that it only reads as a no-change control under the right canonical form. The raw
bytes differ, and collapsing whitespace runs still leaves a one-character difference,
because the newer PDF wrapped a line inside `(1)-(2)` and left `(1)- (2)`. See
`canonical()` in `pipeline/pdf_ingest.py`.

## Ground truth

`gold_revision_history.json` quotes the Revision History Information table published inside
`pdfs/LCD - Glucose Monitors (L33822).pdf` verbatim. CMS states what changed, which gives
an evaluation set without any hand-labeling. It is the only genuinely external
ground truth in this project, which is why it carries the most weight in the scorecard.

## Synthetic data

| File | Origin |
|---|---|
| `claims.json` | Synthetic. No real patient or provider data. Amounts approximate published Medicare DMEPOS allowables. Dates of service fall inside the v1 window. |
| `claim_schema.json` | Authored for this project, with fields chosen to match the actual v1 coverage criteria. |
| `reference_ruleset.json` | Hand-authored by reading the v1 coverage criteria. Every citation is verified by exact search against the PDF at load time. |

## What is and is not published here

**The source PDFs are not committed.** Every CMS coverage document in this set carries an
AMA notice covering CPT content in its code-list sections, and the ADA guideline is ADA
copyright. Publishing them would republish licensed material.

`data/extracted/` holds the coverage-criteria prose instead, which is CMS government work.
Each file was verified to contain no five-digit CPT codes and no AMA notice before being
committed; the assertions that check this are in `data/pdfs/README.md`. `coverage_text()`
falls back to these automatically, so the analysis runs from a clean clone and produces
identical numbers without any PDF present.

## Code sets and licensing

This repository is public, so code set licensing matters.

- **HCPCS Level II** (K0554, K0553, E0607, E2100, E2101, E0470, A4271) is published by CMS
  and is not restricted. Descriptors are included.
- **ICD-10-CM** (E10.x, E11.x, I10, G47.33) is published by CDC and CMS and is not
  restricted.
- **CPT** is copyrighted by the American Medical Association. No CPT descriptors appear
  anywhere in this repository.
- The **ADA Standards of Care** is copyrighted by the American Diabetes Association. The
  PDF is used locally for the guideline cross-check. Only short quoted recommendation
  statements appear in committed output, with citation.

The CPT constraint shaped the choice of clinical area. Durable medical equipment policy
runs on HCPCS rather than CPT, which is one reason glucose monitors work for a public
demonstration where a physician-services policy would not.

## Coding period note

Per Article A52464, a therapeutic CGM is billed as K0554 with supply allowance K0553 for
dates of service from 07/01/2017 through 12/31/2022, and as E2103 from 01/01/2023. The
sample claims carry 2021 dates of service, so K0554 and K0553 are correct for the period
being adjudicated.
