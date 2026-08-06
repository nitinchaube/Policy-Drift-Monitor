"""Turn a CMS coverage-policy PDF into clean text with stable character offsets.

Real policy arrives as PDF, not as a tidy text file, so this is part of the product
rather than a one-off conversion. Three things make CMS LCD PDFs annoying:

  1. Every document opens with a multi-page contractor jurisdiction table that
     extracts as a long column of state names. It carries no policy content.
  2. Page headers and footers repeat on all 20-60 pages.
  3. The revision history at the end is a table whose columns interleave when
     flattened to text.

So we do not use the whole document. We cut out the sections that actually state
coverage rules and work on those. Everything downstream indexes into the result of
`normalize()`, which is called exactly once here.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF


# Headings that begin a real content section in an LCD or Policy Article.
SECTION_HEADS = [
    "Coverage Indications, Limitations, and/or Medical Necessity",
    "Coverage Indications, Limitations and/or Medical Necessity",
    "HOME BLOOD GLUCOSE MONITORS (BGM)",
    "HOME BLOOD GLUCOSE MONITORS",
    "CONTINUOUS GLUCOSE MONITORS (CGMs)",
    "CONTINUOUS GLUCOSE MONITORS (CGM)",
    "CONTINUOUS GLUCOSE MONITORS",
    "GENERAL",
    "Summary of Evidence",
    "Analysis of Evidence",
    "General Information",
    "Associated Information",
    "Bibliography",
    "Revision History Information",
]

# Where the policy content stops and the apparatus begins.
TAIL_MARKERS = ["Summary of Evidence", "Analysis of Evidence", "Bibliography",
                "Revision History Information", "Associated Documents"]

_PAGE_NOISE = re.compile(
    r"^(Created on \d.*|Page \d+ of \d+|Printed on \d.*|"
    r"Links in PDF documents are not guaranteed to work.*)$",
    re.MULTILINE,
)


def normalize(raw: str) -> str:
    """Canonicalize whitespace and punctuation. Called ONCE per document.

    Everything downstream (citations, offsets, the UI) uses the output of this
    function and never sees the original bytes. That is what keeps character
    offsets meaningful.
    """
    t = raw.replace("\r\n", "\n").replace("\r", "\n")
    t = (t.replace(" ", " ").replace("’", "'").replace("‘", "'")
           .replace("“", '"').replace("”", '"')
           .replace("–", "-").replace("—", "-").replace("•", "-"))
    t = _PAGE_NOISE.sub("", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def canonical(text: str) -> str:
    """Strip whitespace entirely, for change detection only. Never for display.

    `normalize()` collapses whitespace runs, which is enough for most purposes but not
    for comparing two PDF extractions of the same content. A PDF that wraps a line in
    a different place can turn "(1)-(2)" into "(1)- (2)", and that one space is
    indistinguishable from a real edit under collapse-only normalization.

    Removing whitespace outright gives a form that survives re-typesetting, so tier 1
    triage can answer "did anything substantive change?" without escalating a
    reflowed paragraph to a language model.
    """
    return re.sub(r"\s+", "", text)


def raw_text(pdf_path: str | Path) -> str:
    doc = fitz.open(str(pdf_path))
    try:
        return "".join(page.get_text() for page in doc)
    finally:
        doc.close()


def coverage_text(pdf_path: str | Path) -> str:
    """Return just the coverage-criteria portion of the document, normalized.

    Starts at the Coverage Indications heading and stops at the evidence review.
    Falls back to the whole document if the heading is not found, so an unexpected
    layout degrades instead of returning nothing.

    If the PDF is absent, falls back to a pre-extracted copy in data/extracted/. The
    source PDFs are not redistributed: every CMS coverage document carries an AMA CPT
    copyright notice in its code-list sections, so publishing the PDFs would republish
    licensed content. The coverage-criteria prose this function returns is CMS
    government work and contains no CPT, which was checked rather than assumed.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        cached = pdf_path.parent.parent / "extracted" / (pdf_path.stem + ".txt")
        if cached.exists():
            return cached.read_text(encoding="utf-8")
        raise FileNotFoundError(
            f"{pdf_path.name} not found, and no extracted copy at {cached}. "
            f"See data/pdfs/README.md for how to retrieve the source documents."
        )

    text = normalize(raw_text(pdf_path))

    start = -1
    for head in ("Coverage Indications, Limitations, and/or Medical Necessity",
                 "Coverage Indications, Limitations and/or Medical Necessity"):
        # the heading appears once in the table of contents and again for real;
        # the real one is the later occurrence
        hits = [m.start() for m in re.finditer(re.escape(head), text)]
        if hits:
            start = hits[-1] if len(hits) > 1 else hits[0]
            break
    if start == -1:
        return text

    end = len(text)
    for marker in TAIL_MARKERS:
        m = re.search(re.escape(marker), text[start:])
        if m:
            end = min(end, start + m.start())

    return text[start:end].strip()


def segment(text: str) -> list[dict]:
    """Split into named sections that tile the text with no gaps or overlaps."""
    hits = []
    for head in SECTION_HEADS:
        for m in re.finditer(rf"^{re.escape(head)}\s*$", text, flags=re.MULTILINE):
            hits.append((m.start(), head))
    hits.sort()
    # drop a heading that starts inside the span of a longer one matched at the
    # same offset (e.g. "CONTINUOUS GLUCOSE MONITORS" vs "... (CGM)")
    deduped = []
    for pos, head in hits:
        if deduped and deduped[-1][0] == pos:
            if len(head) > len(deduped[-1][1]):
                deduped[-1] = (pos, head)
            continue
        deduped.append((pos, head))

    if not deduped:
        return [{"name": "(whole document)", "start": 0, "end": len(text), "text": text}]

    sections = []
    if deduped[0][0] > 0:
        sections.append({"name": "(preamble)", "start": 0, "end": deduped[0][0]})
    for i, (pos, head) in enumerate(deduped):
        end = deduped[i + 1][0] if i + 1 < len(deduped) else len(text)
        sections.append({"name": head, "start": pos, "end": end})
    for s in sections:
        s["text"] = text[s["start"]:s["end"]]
    return sections


def collapse_with_map(text: str):
    """Collapse whitespace runs to one space, remembering the source index of each
    surviving character. Lets us match loosely but report exact offsets."""
    out, idxmap, prev_space = [], [], False
    for i, ch in enumerate(text):
        if ch.isspace():
            if prev_space:
                continue
            out.append(" "); idxmap.append(i); prev_space = True
        else:
            out.append(ch); idxmap.append(i); prev_space = False
    return "".join(out), idxmap


def locate(text: str, sentence: str):
    """Find `sentence` in `text`, returning (start, end) or None.

    We never ask a model for character offsets. It quotes, we locate. A quote that
    cannot be found is a fabricated citation and the rule is rejected. Matching is
    whitespace-insensitive because the model quotes on one line what the PDF wraps
    across three.
    """
    needle = re.sub(r"\s+", " ", sentence).strip()
    if not needle:
        return None
    hay, idxmap = collapse_with_map(text)
    pos = hay.find(needle)
    if pos == -1:
        return None
    return (idxmap[pos], idxmap[pos + len(needle) - 1] + 1)


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        body = coverage_text(arg)
        print(f"\n{'=' * 78}\n{arg}  ({len(body):,} chars)\n{'=' * 78}")
        for s in segment(body):
            print(f"  {s['name']:<62} {s['start']:>6}-{s['end']:<6} {len(s['text']):>6}")
