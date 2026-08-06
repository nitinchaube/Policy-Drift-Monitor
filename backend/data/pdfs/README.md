# Source PDFs are not in this repository

Deliberately. Every CMS coverage document here carries an AMA notice covering CPT content
in its code-list sections, and the ADA guideline is American Diabetes Association
copyright. Publishing the PDFs in a public repository would republish licensed material.

What is committed instead is `../extracted/`: the coverage-criteria prose only, which is
CMS government work. I checked rather than assumed. Each extracted file was verified to
contain no five-digit CPT codes and no AMA notice before being committed, and that check
is reproduced in the export step.

`coverage_text()` in `pipeline/pdf_ingest.py` falls back to `../extracted/` automatically
when a PDF is absent, so **the whole analysis runs from a clean clone and produces
identical numbers**. You only need the PDFs to re-derive the extracted text or to work on
ingestion itself.

## Retrieving them

CMS returns HTTP 403 to programmatic fetches, and the Coverage API requires a bearer token
obtained by accepting the AMA, ADA and AHA license agreements. Retrieve them through a
browser and accept the license yourself.

| Save as | Document | Where |
|---|---|---|
| `L33822_2020.pdf` | LCD L33822, effective 01/01/2020, ending 07/17/2021 | [MCD Archive](https://localcoverage.cms.gov/mcd_archive), search L33822 |
| `L33822_2021.pdf` | LCD L33822, effective 07/18/2021, ending 02/27/2022 | MCD Archive |
| `LCD - Glucose Monitors (L33822) superseded.pdf` | LCD L33822, effective 04/01/2024, ending 09/30/2024 | MCD Archive |
| `LCD - Glucose Monitors (L33822).pdf` | LCD L33822, current | [MCD](https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33822) |
| `Article - Glucose Monitor - Policy Article (A52464).pdf` | Local Coverage Article A52464 | [MCD](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId=52464) |
| `adaStandardsOfCareSec7.pdf` | ADA Standards of Care 2026, Section 7 | [Diabetes Care](https://diabetesjournals.org/care/article/49/Supplement_1/S150/163922/) |

Only the first four are used by the pipeline. The Article informs the HCPCS coding-period
notes in `claim_schema.json`, and the ADA guideline was retrieved for a guideline
cross-check that was not built.

## Re-deriving the extracted text

With the PDFs in place:

```bash
cd backend && python3 - <<'EOF'
import re, sys; sys.path.insert(0, '.')
from pathlib import Path
from pipeline.pdf_ingest import coverage_text
for stem in ['L33822_2020', 'L33822_2021',
             'LCD - Glucose Monitors (L33822) superseded',
             'LCD - Glucose Monitors (L33822)']:
    t = coverage_text(f'data/pdfs/{stem}.pdf')
    assert not re.search(r'American Medical Association|Current Procedural Terminology', t, re.I)
    assert not re.findall(r'\b\d{5}\b', t)          # no CPT codes
    Path(f'data/extracted/{stem}.txt').write_text(t, encoding='utf-8')
    print(stem, len(t), 'chars, CPT-free')
EOF
```

The two assertions are the licensing check. If either fails, that file must not be
committed.
