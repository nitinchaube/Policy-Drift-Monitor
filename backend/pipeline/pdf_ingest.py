"""PDF -> clean text with stable character offsets, for CMS coverage-policy PDFs.

Three quirks to work around: a multi-page contractor jurisdiction table up front
with no policy content, repeating headers/footers across 20-60 pages, and a
revision-history table whose columns interleave when flattened to text.
coverage_text() cuts to just the coverage-criteria section. normalize() runs once;
everything downstream (citations, offsets, the UI) indexes into its output.
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
    """Canonicalize whitespace/punctuation. Called once per document; offsets are
    computed against the result, so nothing downstream should see raw bytes again."""
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
    """All whitespace removed -- for change detection only, never for display.

    normalize() collapses whitespace runs but a re-wrapped line can still leave a
    stray space (e.g. "(1)-(2)" -> "(1)- (2)"), which reads as an edit. This form
    survives re-typesetting, so "did anything change?" can be answered without
    escalating to a model call.
    """
    return re.sub(r"\s+", "", text)


def raw_text(pdf_path: str | Path) -> str:
    doc = fitz.open(str(pdf_path))
    try:
        return "".join(page.get_text() for page in doc)
    finally:
        doc.close()


def coverage_text(pdf_path: str | Path) -> str:
    """Coverage-criteria section only, normalized. Starts at the "Coverage
    Indications" heading and stops before the evidence review; falls back to the
    whole document if the heading isn't found.

    Falls back to data/extracted/<stem>.txt if the PDF itself is missing. The PDFs
    aren't redistributed here (AMA CPT notices in the code-list sections), but the
    extracted coverage prose is CMS government work, verified CPT-free before commit.
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
    """Collapse whitespace runs to one space, tracking each surviving char's source
    index -- lets locate() match loosely but still report exact offsets."""
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
    """Find `sentence` in `text` (whitespace-insensitive), returning (start, end) or
    None. The model quotes; this locates -- an unfindable quote means a fabricated
    citation, and the caller rejects the rule."""
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
