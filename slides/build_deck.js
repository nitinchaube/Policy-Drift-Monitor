const pptxgen = require('pptxgenjs');

// Palette chosen for the topic: ink for policy documents, brick for a denial or a
// contradicted rule, green for a paid claim. Deliberately not generic corporate blue.
const INK = '1C3141';
const INK2 = '2A4759';
const PAPER = 'FFFFFF';
const MIST = 'F1F4F6';
const LINE = 'D8DEE3';
const RED = 'B4453A';
const GREEN = '3E7A5E';
const AMBER = '9A7420';
const MUTED = '6B7A85';

const SERIF = 'Cambria';
const SANS = 'Calibri';
const MONO = 'Courier New';

const W = 13.3, H = 7.5, M = 0.65;

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.author = 'Nitin Chaube';
pres.title = 'Policy Drift Monitor';

// Motif: a small monospace tag with a filled square, repeated on every content slide.
function tag(slide, text, color = INK) {
  slide.addShape(pres.ShapeType.rect, { x: M, y: 0.45, w: 0.1, h: 0.1, fill: { color } });
  slide.addText(text, {
    x: M + 0.2, y: 0.32, w: 8, h: 0.34, margin: 0,
    fontFace: MONO, fontSize: 11, color: MUTED, charSpacing: 0.6,
  });
}

function title(slide, text, color = INK) {
  slide.addText(text, {
    x: M, y: 0.72, w: W - 2 * M, h: 0.85, margin: 0,
    fontFace: SERIF, fontSize: 32, bold: true, color, valign: 'top',
  });
}

function card(slide, { x, y, w, h, fill = MIST }) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.04, fill: { color: fill },
    line: { color: LINE, width: 0.75 },
  });
}

// ------------------------------------------------------------------ 1. title
{
  const s = pres.addSlide();
  s.background = { color: INK };
  s.addText('Policy Drift Monitor', {
    x: M, y: 2.25, w: 10, h: 0.95, margin: 0,
    fontFace: SERIF, fontSize: 46, bold: true, color: PAPER,
  });
  s.addText('When a coverage policy changes, which of your claim rules just went wrong?', {
    x: M, y: 3.25, w: 10.2, h: 0.55, margin: 0,
    fontFace: SANS, fontSize: 18, color: 'AFC0CC',
  });
  s.addShape(pres.ShapeType.rect, { x: M, y: 4.15, w: 1.1, h: 0.03, fill: { color: RED } });
  s.addText('Nitin Chaube', {
    x: M, y: 4.5, w: 8, h: 0.34, margin: 0, fontFace: SANS, fontSize: 15, color: PAPER,
  });
  s.addText('Cotiviti Intern Assessment  ·  Topic 3: Content Management in Health Care', {
    x: M, y: 4.85, w: 9, h: 0.34, margin: 0, fontFace: SANS, fontSize: 13, color: '8FA3B2',
  });
  s.addText('CMS LCD L33822  ·  v1 eff. 2020-01-01   v2 eff. 2021-07-18', {
    x: M, y: 5.3, w: 9, h: 0.3, margin: 0, fontFace: MONO, fontSize: 11, color: '6E8798',
  });
  s.addNotes('Opening line: a payer turns written policy into claim rules. The policy changes. The rules do not. This is a working tool that finds the gap, built on real Medicare documents.');
}

// ------------------------------------------------------------------ 2. problem
{
  const s = pres.addSlide();
  tag(s, 'THE PROBLEM');
  title(s, 'Rules are derived once. Policies change forever.');

  const steps = [
    ['JAN', 'Policy v1 published', 'An analyst reads it and writes 12 claim rules. They go live.', INK2],
    ['FEB–JUN', 'Rules decide claims', 'Thousands of decisions a day. Working exactly as intended.', INK2],
    ['JUL', 'CMS revises the policy', 'Three coverage criteria change. Nobody re-reads the rule library.', AMBER],
    ['AUG+', 'Rules are now wrong', 'They keep denying claims the policy now covers. Silently.', RED],
  ];
  const cw = (W - 2 * M - 0.45) / 4;
  steps.forEach(([when, head, body, col], i) => {
    const x = M + i * (cw + 0.15);
    card(s, { x, y: 2.0, w: cw, h: 2.5, fill: i === 3 ? 'F7EDEC' : MIST });
    s.addText(when, {
      x: x + 0.22, y: 2.22, w: cw - 0.44, h: 0.3, margin: 0,
      fontFace: MONO, fontSize: 11, bold: true, color: col,
    });
    s.addText(head, {
      x: x + 0.22, y: 2.6, w: cw - 0.44, h: 0.7, margin: 0,
      fontFace: SANS, fontSize: 15, bold: true, color: INK,
    });
    s.addText(body, {
      x: x + 0.22, y: 3.3, w: cw - 0.44, h: 1.05, margin: 0,
      fontFace: SANS, fontSize: 12, color: MUTED,
    });
  });

  s.addText('Nobody’s job is to re-read thousands of policies checking whether old rules still hold.', {
    x: M, y: 4.95, w: W - 2 * M, h: 0.45, margin: 0,
    fontFace: SERIF, fontSize: 19, italic: true, color: INK,
  });
  s.addNotes('The failure is not that the rule was written badly. It was correct in January. The failure is that nothing revisits it.');
}

// ------------------------------------------------------------------ 3. what it does
{
  const s = pres.addSlide();
  tag(s, 'WHAT IT DOES');
  title(s, 'Four stages, one loop');

  const stages = [
    ['1', 'Read', 'A real CMS policy PDF becomes clean text with character offsets preserved.'],
    ['2', 'Convert', 'A model emits rules in a fixed schema. Every rule quotes its source sentence, and the quote is verified by exact search.'],
    ['3', 'Adjudicate', 'Rules compile to Python predicates and decide claims. No model in the decision path.'],
    ['4', 'Detect drift', 'When the policy is revised, each existing rule is re-checked against it and priced in claim decisions.'],
  ];
  const rh = 1.02;
  stages.forEach(([n, head, body], i) => {
    const y = 1.85 + i * (rh + 0.16);
    s.addShape(pres.ShapeType.ellipse, {
      x: M, y: y + 0.14, w: 0.5, h: 0.5, fill: { color: i === 3 ? RED : INK },
    });
    s.addText(n, {
      x: M, y: y + 0.14, w: 0.5, h: 0.5, margin: 0, align: 'center', valign: 'middle',
      fontFace: SANS, fontSize: 16, bold: true, color: PAPER,
    });
    s.addText(head, {
      x: M + 0.75, y: y + 0.1, w: 2.1, h: 0.4, margin: 0,
      fontFace: SANS, fontSize: 17, bold: true, color: INK,
    });
    s.addText(body, {
      x: M + 2.9, y: y + 0.08, w: W - M - 3.55, h: 0.85, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: MUTED,
    });
  });
  s.addNotes('Stages 1 to 3 are the product a payer already has, in miniature. Stage 4 is the part nobody does.');
}

// ------------------------------------------------------------------ 4. real data
{
  const s = pres.addSlide();
  tag(s, 'THE DATA IS REAL');
  title(s, 'Three documented changes, taken from CMS itself');

  s.addText('CMS publishes a revision history inside every coverage determination. That is our answer key, which means nothing here was hand-labelled by me.', {
    x: M, y: 1.7, w: W - 2 * M, h: 0.5, margin: 0, fontFace: SANS, fontSize: 14, color: MUTED,
  });

  const rows = [
    ['R1', 'Removed: four or more times per day BGM testing as a prerequisite', 'CONTRADICTED', RED],
    ['R2', 'Revised: "injections" → "administrations" of insulin', 'MODIFIED', AMBER],
    ['R3', 'Removed: "Medicare-covered" from the CSII pump criterion', 'MODIFIED', AMBER],
    ['—', 'List renumbered 1–6 → 1–5, cross-reference "(1-4)" → "(1-3)"', 'MUST NOT FLAG', GREEN],
  ];
  rows.forEach(([id, text, verdict, col], i) => {
    const y = 2.4 + i * 0.78;
    card(s, { x: M, y, w: W - 2 * M, h: 0.66, fill: i === 3 ? 'EDF3EF' : MIST });
    s.addText(id, {
      x: M + 0.22, y: y + 0.17, w: 0.5, h: 0.32, margin: 0,
      fontFace: MONO, fontSize: 12, bold: true, color: col,
    });
    s.addText(text, {
      x: M + 0.85, y: y + 0.15, w: 7.6, h: 0.38, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: INK,
    });
    s.addText(verdict, {
      x: W - M - 2.5, y: y + 0.17, w: 2.3, h: 0.32, margin: 0, align: 'right',
      fontFace: MONO, fontSize: 11.5, bold: true, color: col,
    });
  });

  s.addText('The fourth row is a trap the document set handed us: the sentence changed, the requirement did not.', {
    x: M, y: 5.62, w: W - 2 * M, h: 0.4, margin: 0,
    fontFace: SANS, fontSize: 13, italic: true, color: MUTED,
  });
  s.addNotes('Emphasise: the evaluation set came from CMS, not from me. That is the difference between a demo and a measurement.');
}

// ------------------------------------------------------------------ 5. results
{
  const s = pres.addSlide();
  s.background = { color: INK };
  tag(s, 'RESULTS', RED);
  title(s, 'What it found', PAPER);

  const stats = [
    ['3 / 3', 'documented changes caught', GREEN],
    ['0', 'false alarms', GREEN],
    ['1 / 1', 'must-not-flag traps passed', GREEN],
    ['$1,208.71', 'wrongly withheld, 6 of 20 claims', RED],
  ];
  const cw = (W - 2 * M - 0.6) / 4;
  stats.forEach(([v, k, col], i) => {
    const x = M + i * (cw + 0.2);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 2.2, w: cw, h: 1.75, rectRadius: 0.04,
      fill: { color: '253F52' }, line: { color: '38596E', width: 0.75 },
    });
    s.addText(v, {
      x: x + 0.2, y: 2.5, w: cw - 0.4, h: 0.8, margin: 0,
      fontFace: SANS, fontSize: v.length > 8 ? 30 : 40, bold: true, color: col,
    });
    s.addText(k, {
      x: x + 0.2, y: 3.32, w: cw - 0.4, h: 0.55, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: 'AFC0CC',
    });
  });

  s.addText('Negative control: two consecutive official 2024 versions where only a HCPCS descriptor changed.', {
    x: M, y: 4.4, w: W - 2 * M, h: 0.35, margin: 0, fontFace: SANS, fontSize: 14, color: PAPER,
  });
  s.addText('Zero findings, and it reached that conclusion before spending a single model call.', {
    x: M, y: 4.78, w: W - 2 * M, h: 0.35, margin: 0,
    fontFace: SANS, fontSize: 14, color: '8FA3B2',
  });
  s.addText('Scored against the revision history CMS publishes inside the document.', {
    x: M, y: 5.55, w: W - 2 * M, h: 0.35, margin: 0,
    fontFace: MONO, fontSize: 11, color: '6E8798',
  });
  s.addNotes('These are the numbers to say out loud. Three of three, zero false alarms, and a negative control that cost nothing.');
}

// ------------------------------------------------------------------ 6. impact chart
{
  const s = pres.addSlide();
  tag(s, 'IMPACT');
  title(s, 'Stale rules cost real decisions');

  s.addChart(pres.ChartType.bar, [
    { name: 'Paid', labels: ['Before correction', 'After correction'], values: [7, 13] },
    { name: 'Denied', labels: ['Before correction', 'After correction'], values: [10, 5] },
    { name: 'Manual review', labels: ['Before correction', 'After correction'], values: [3, 2] },
  ], {
    x: M, y: 1.85, w: 7.4, h: 3.9,
    barDir: 'bar', barGrouping: 'stacked',
    chartColors: [GREEN, RED, AMBER],
    showTitle: false, showLegend: true, legendPos: 'b', legendFontSize: 12,
    showValue: true, dataLabelPosition: 'ctr', dataLabelColor: 'FFFFFF',
    dataLabelFontSize: 13, dataLabelFontBold: true,
    catAxisLabelColor: INK, catAxisLabelFontSize: 13,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 11,
    valGridLine: { color: LINE, size: 0.75 }, catGridLine: { style: 'none' },
  });

  card(s, { x: 8.35, y: 1.85, w: W - M - 8.35, h: 3.9 });
  s.addText('Six of twenty claims changed', {
    x: 8.6, y: 2.1, w: 3.7, h: 0.4, margin: 0,
    fontFace: SANS, fontSize: 17, bold: true, color: INK,
  });
  s.addText([
    { text: 'C-003, C-004, C-007  ', options: { fontFace: MONO, fontSize: 12, color: INK, breakLine: true } },
    { text: 'denied for a testing requirement CMS deleted', options: { fontSize: 12.5, color: MUTED, breakLine: true } },
    { text: '', options: { fontSize: 7, breakLine: true } },
    { text: 'C-008  ', options: { fontFace: MONO, fontSize: 12, color: INK, breakLine: true } },
    { text: 'sat in manual review for a rule that no longer exists', options: { fontSize: 12.5, color: MUTED, breakLine: true } },
    { text: '', options: { fontSize: 7, breakLine: true } },
    { text: 'C-011, C-016  ', options: { fontFace: MONO, fontSize: 12, color: INK, breakLine: true } },
    { text: 'insulin pump and non-injection routes, both newly eligible', options: { fontSize: 12.5, color: MUTED } },
  ], { x: 8.6, y: 2.55, w: 3.7, h: 2.6, margin: 0, fontFace: SANS, valign: 'top' });

  s.addText('Twenty claims is a demonstration. In production this replays ninety days of real claims and returns a worklist ranked by dollars.', {
    x: M, y: 5.95, w: W - 2 * M, h: 0.4, margin: 0,
    fontFace: SANS, fontSize: 13, italic: true, color: MUTED,
  });
  s.addNotes('C-007 is the one to point at. Denied for testing once a day, under a requirement Medicare removed in July 2021.');
}

// ------------------------------------------------------------------ 7. how it is trustworthy
{
  const s = pres.addSlide();
  tag(s, 'WHY TRUST IT');
  title(s, 'The model authors. It never decides.');

  const items = [
    ['Citations are verified, not trusted', 'The model quotes a sentence; the code goes and finds it. An unfindable quote is a fabricated citation and the rule is discarded.'],
    ['The schema is the validator', 'Type and range checks against the claim schema caught rules that referenced real fields and were still nonsense, at zero cost.'],
    ['Facts from the model, verdicts from a table', 'The drift detector reports three observations. Python derives the verdict. Deterministic, inspectable, identical every time.'],
    ['Missing data never denies', 'Three-valued logic. Absence of evidence routes to a human, not to a denial.'],
  ];
  const cw = (W - 2 * M - 0.35) / 2;
  items.forEach(([head, body], i) => {
    const x = M + (i % 2) * (cw + 0.35);
    const y = 1.9 + Math.floor(i / 2) * 1.95;
    card(s, { x, y, w: cw, h: 1.7 });
    s.addText(head, {
      x: x + 0.25, y: y + 0.22, w: cw - 0.5, h: 0.45, margin: 0,
      fontFace: SANS, fontSize: 16, bold: true, color: INK,
    });
    s.addText(body, {
      x: x + 0.25, y: y + 0.72, w: cw - 0.5, h: 0.85, margin: 0,
      fontFace: SANS, fontSize: 13, color: MUTED,
    });
  });
  s.addText('A denial has to be reproducible three years later, on appeal. That rules a model out of the decision path.', {
    x: M, y: 5.95, w: W - 2 * M, h: 0.4, margin: 0,
    fontFace: SERIF, fontSize: 16, italic: true, color: INK,
  });
  s.addNotes('This is the slide that separates the project from a chatbot demo. Say the appeal line out loud.');
}

// ------------------------------------------------------------------ 8. what broke
{
  const s = pres.addSlide();
  tag(s, 'WHAT BROKE', RED);
  title(s, 'Three things broke. The tests caught each one.');

  const fails = [
    ['Two rules were type-valid nonsense',
      'The extractor produced claim_id contains_any ["K0554"]. Validation only checked that fields existed. Twelve claims became manual review.',
      'Fix: type and enum checks against the schema I already had.'],
    ['The detector missed two of three changes',
      'It read the insulin criterion in both versions and called it unchanged, never registering that "injections" had become "administrations".',
      'Fix: stop asking for a verdict. Ask for facts, derive the verdict.'],
    ['Majority voting picked the wrong answer',
      'Five extraction runs disagreed. The two-vote plurality dropped an alternative that would have denied every pump user.',
      'Fix: round-trip verification arbitrates. It recovered the one-vote correct answer.'],
  ];
  const cw = (W - 2 * M - 0.5) / 3;
  fails.forEach(([head, body, fix], i) => {
    const x = M + i * (cw + 0.25);
    card(s, { x, y: 1.9, w: cw, h: 3.5, fill: 'F7EDEC' });
    s.addText(head, {
      x: x + 0.24, y: 2.12, w: cw - 0.48, h: 0.75, margin: 0,
      fontFace: SANS, fontSize: 15.5, bold: true, color: RED,
    });
    s.addText(body, {
      x: x + 0.24, y: 2.92, w: cw - 0.48, h: 1.5, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK,
    });
    s.addText(fix, {
      x: x + 0.24, y: 4.45, w: cw - 0.48, h: 0.85, margin: 0,
      fontFace: SANS, fontSize: 12.5, bold: true, color: INK2,
    });
  });
  s.addText('The two largest improvements came from giving the model less to do, not more.', {
    x: M, y: 5.7, w: W - 2 * M, h: 0.4, margin: 0,
    fontFace: SERIF, fontSize: 17, italic: true, color: INK,
  });
  s.addNotes('Do not skip this slide. Being able to name your own failures is the strongest thing in the submission.');
}

// ------------------------------------------------------------------ 9. at scale
{
  const s = pres.addSlide();
  tag(s, 'AT SCALE');
  title(s, 'Five million documents, about $100 a day');

  s.addText('The whole architecture is a cost problem. Never ask the expensive question until the cheap ones say you must.', {
    x: M, y: 1.68, w: W - 2 * M, h: 0.4, margin: 0, fontFace: SANS, fontSize: 14, color: MUTED,
  });

  const tiers = [
    ['TIER 0', 'Content hash', '5M → 25k', 'free', INK2],
    ['TIER 1', 'Canonical form', '25k → 25k', 'free', INK2],
    ['TIER 2', 'Substantive or cosmetic?', '25k → 5k', 'cents', AMBER],
    ['TIER 3', 'Does it break a rule?', '~15k questions', 'dollars', RED],
  ];
  const cw = (W - 2 * M - 0.45) / 4;
  tiers.forEach(([t, what, vol, cost, col], i) => {
    const x = M + i * (cw + 0.15);
    card(s, { x, y: 2.25, w: cw, h: 1.95 });
    s.addText(t, {
      x: x + 0.22, y: 2.45, w: cw - 0.44, h: 0.3, margin: 0,
      fontFace: MONO, fontSize: 11, bold: true, color: col,
    });
    s.addText(what, {
      x: x + 0.22, y: 2.8, w: cw - 0.44, h: 0.6, margin: 0,
      fontFace: SANS, fontSize: 14, bold: true, color: INK,
    });
    s.addText(vol, {
      x: x + 0.22, y: 3.42, w: cw - 0.44, h: 0.32, margin: 0,
      fontFace: MONO, fontSize: 12, color: INK,
    });
    s.addText(cost, {
      x: x + 0.22, y: 3.76, w: cw - 0.44, h: 0.3, margin: 0,
      fontFace: SANS, fontSize: 12, italic: true, color: MUTED,
    });
  });

  s.addText('Proven on the real 2024 pair: hashing failed, whitespace normalisation failed, the canonical form settled it. Zero model calls.', {
    x: M, y: 4.45, w: W - 2 * M, h: 0.4, margin: 0, fontFace: SANS, fontSize: 13.5, color: INK,
  });
  s.addText('Also required: a provenance graph from any document version to every rule derived from it, immutable versioned rules for point-in-time appeal defence, and promotion through shadow mode before an edit affects payment.', {
    x: M, y: 5.0, w: W - 2 * M, h: 0.75, margin: 0, fontFace: SANS, fontSize: 13, color: MUTED,
  });
  s.addNotes('Tier 2 is the rung I did not build. Say so.');
}

// ------------------------------------------------------------------ 10. recommendations
{
  const s = pres.addSlide();
  tag(s, 'RECOMMENDATIONS');
  title(s, 'What I would have Cotiviti do');

  const recs = [
    ['01', 'Monitor the edit library you already have',
      'Not an authoring product. A service that watches source documents and returns a ranked worklist of edits a revision has invalidated, priced by replaying recent claims. It replaces nothing and fails safe.'],
    ['02', 'Treat rules as code',
      'Immutable versioned rules, point-in-time adjudication, promotion through shadow and canary before an edit affects payment. This is what makes automation defensible to a regulator and an appeals board.'],
    ['03', 'Invest in the claim vocabulary, not the model',
      'The pipeline generalised across documents unchanged. The schema was the only part that needed authoring and the only part that limited what could be encoded. Models are rented. A vocabulary tied to an installed base is not.'],
  ];
  recs.forEach(([n, head, body], i) => {
    const y = 1.85 + i * 1.42;
    s.addText(n, {
      x: M, y: y + 0.05, w: 0.8, h: 0.6, margin: 0,
      fontFace: SERIF, fontSize: 28, bold: true, color: i === 0 ? RED : LINE,
    });
    s.addText(head, {
      x: M + 0.95, y: y, w: 4.3, h: 0.85, margin: 0,
      fontFace: SANS, fontSize: 16.5, bold: true, color: INK,
    });
    s.addText(body, {
      x: M + 5.4, y: y - 0.02, w: W - M - 6.05, h: 1.2, margin: 0,
      fontFace: SANS, fontSize: 13, color: MUTED,
    });
  });
  s.addNotes('Lead with recommendation one. It is the one that could ship next quarter without changing how anyone works.');
}

// ------------------------------------------------------------------ 11. limitations
{
  const s = pres.addSlide();
  tag(s, 'LIMITATIONS');
  title(s, 'What this does not prove');

  const lims = [
    'n is tiny. Three documented edits, twenty synthetic claims, one document pair. This demonstrates behaviour; it is not statistically meaningful.',
    'One clinical area, one document format, one payer. Nothing here shows it generalises.',
    'The gold ruleset and the claims were authored by the same person who built the extractor. Only the CMS revision history is genuinely external, which is why it carries the most weight.',
    'The prototype still fails its own quality gate on two rules. One encodes a per-30-day limit the claim schema cannot express.',
    'No OCR, no database, no promotion pipeline, and payer-provider contracts are not covered at all because no public corpus exists.',
  ];
  lims.forEach((t, i) => {
    const y = 1.9 + i * 0.82;
    s.addShape(pres.ShapeType.rect, { x: M, y: y + 0.16, w: 0.07, h: 0.07, fill: { color: MUTED } });
    s.addText(t, {
      x: M + 0.3, y, w: W - 2 * M - 0.3, h: 0.72, margin: 0,
      fontFace: SANS, fontSize: 14, color: INK,
    });
  });
  s.addText('Reporting the gate failure is the point. A tool that hides its own defects is worse than no tool.', {
    x: M, y: 6.15, w: W - 2 * M, h: 0.4, margin: 0,
    fontFace: SERIF, fontSize: 16, italic: true, color: INK,
  });
  s.addNotes('Say this section confidently, not apologetically. It is a strength.');
}

// ------------------------------------------------------------------ 12. close
{
  const s = pres.addSlide();
  s.background = { color: INK };
  s.addText('What this proves', {
    x: M, y: 1.9, w: 10, h: 0.7, margin: 0,
    fontFace: SERIF, fontSize: 34, bold: true, color: PAPER,
  });
  s.addText('Rules can be derived from policy prose with a citation trail you can verify, and when the prose changes, the rules that broke can be found and priced.', {
    x: M, y: 2.8, w: 11.2, h: 1.0, margin: 0,
    fontFace: SANS, fontSize: 19, color: 'CFDBE4',
  });
  s.addShape(pres.ShapeType.rect, { x: M, y: 4.05, w: 1.1, h: 0.03, fill: { color: RED } });
  s.addText('It does not prove it generalises. I have written down what would have to be true for that.', {
    x: M, y: 4.4, w: 11.2, h: 0.5, margin: 0,
    fontFace: SANS, fontSize: 15, italic: true, color: '8FA3B2',
  });
  s.addText('github.com/<your-handle>/cotiviti-assessment   ·   run it with:  python -m cli', {
    x: M, y: 5.6, w: 11.2, h: 0.35, margin: 0,
    fontFace: MONO, fontSize: 12, color: '6E8798',
  });
  s.addNotes('Close on the honest line. Do not oversell. Then stop talking.');
}

pres.writeFile({ fileName: __dirname + '/Presentation.pptx' })
  .then((f) => console.log('wrote', f));
