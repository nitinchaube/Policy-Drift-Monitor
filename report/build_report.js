const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, AlignmentType,
  PageBreak, BorderStyle, convertInchesToTwip,
} = require('docx');

const FONT = 'Calibri';
const BODY = 20;   // half-points => 10pt
const H = 22;

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 100, line: opts.line ?? 240 },
  alignment: opts.align,
  children: [new TextRun({ text, font: FONT, size: opts.size ?? BODY, bold: opts.bold })],
});

// paragraph with a bold lead-in, used for the trend/threat/recommendation items
const lead = (boldPart, rest) => new Paragraph({
  spacing: { after: 100, line: 240 },
  children: [
    new TextRun({ text: boldPart, font: FONT, size: BODY, bold: true }),
    new TextRun({ text: rest, font: FONT, size: BODY }),
  ],
});

const h1 = (text) => new Paragraph({
  spacing: { before: 180, after: 90 },
  children: [new TextRun({ text, font: FONT, size: H, bold: true })],
});

// hanging-indent reference entry, APA style
const ref = (text) => new Paragraph({
  spacing: { after: 120, line: 240 },
  indent: { left: convertInchesToTwip(0.5), hanging: convertInchesToTwip(0.5) },
  children: [new TextRun({ text, font: FONT, size: BODY })],
});

const doc = new Document({
  creator: 'Nitin Chaube',
  title: 'Content Management in Health Care',
  styles: { default: { document: { run: { font: FONT, size: BODY } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },          // US Letter
        margin: {
          top: convertInchesToTwip(0.8), bottom: convertInchesToTwip(0.8),
          left: convertInchesToTwip(0.9), right: convertInchesToTwip(0.9),
        },
      },
    },
    children: [
      new Paragraph({
        spacing: { after: 40 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: '888888', space: 6 } },
        children: [new TextRun({
          text: 'Content Management in Health Care: Converting Written Policy into Executable Rules',
          font: FONT, size: 26, bold: true,
        })],
      }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: 'Nitin Chaube  |  Cotiviti Intern Assessment  |  Topic 3  |  August 2026',
          font: FONT, size: 18, color: '555555',
        })],
      }),

      h1('The concept'),
      p('A health plan cannot pay a claim simply because a provider submitted it. Before payment, each claim is tested against rules encoding what the plan actually covers. Those rules do not originate in a database. They originate in prose: Medicare coverage determinations, national coding standards, the plan’s own medical policy, specialty society guidelines, and negotiated provider contracts.'),
      p('Content management in this setting is the discipline of turning that prose into something a computer can execute, then keeping the two in agreement. It spans four operations: summarizing policy so a reviewer can triage it, comparing versions to find what changed, converting written requirements into rules or code, and maintaining the resulting artifacts as the sources move underneath them.'),
      p('Today the conversion step is manual. A registered nurse or certified coder reads the document and writes the edit. That work is slow, expensive, and inconsistent between analysts. More importantly it runs one way: when a source policy is revised, nothing automatically revisits the rules derived from it. A rule authored correctly in January can be wrong by July and keep running, denying claims the policy now covers, until somebody notices.'),

      h1('Trends'),
      lead('Policy volume and velocity exceed manual review capacity. ',
        'CMS maintains thousands of coverage documents and revises them continuously; local coverage determinations carry a published revision history precisely because change is routine. Layered on top are state Medicaid policy, commercial medical policy, and annual code set updates. No organization re-reads all of it against its own rule library.'),
      lead('Language models made prose-to-structure conversion viable, and the market has noticed. ',
        'Cohere Health markets Policy Studio, which converts static policy documents into decision trees and executable rules. Research has moved in parallel: CPGPrompt translates clinical guidelines into auditable decision pathways, and clinical autoformalization work converts guidelines into verified, reusable function libraries (Han et al., 2026; Wang et al., 2026).'),
      lead('The industry is shifting from post-payment recovery toward pre-payment accuracy. ',
        'That shift raises the cost of a wrong rule. A recovery request can be withdrawn. A wrongful pre-payment denial stops a patient receiving equipment and generates an appeal.'),
      lead('Provider abrasion has become a competitive axis rather than an externality. ',
        'Cotiviti advertises that 97 to 99 percent of claims auto-pass and that roughly 10 percent of providers are touched by edits on average (Cotiviti, 2026a). Those figures are marketed because false positives are now a purchasing criterion.'),
      lead('Interoperability investment is consolidating the surrounding data layer. ',
        'Cotiviti’s 2025 acquisition of Edifecs extended it into real-time data exchange, which is the substrate any automated policy pipeline would sit on.'),

      h1('Opportunities'),
      p('The largest near-term opportunity is not authoring new edits. It is maintaining the ones that already exist. An organization operating a large installed base of edits derived from continuously revised sources has stale rules in production right now and no systematic way to find them. A service that watches source documents and flags the specific edits a revision has invalidated adds capability without replacing anything, and it fails safe: the worst outcome is a finding a reviewer dismisses.'),
      p('Three further opportunities follow from the same machinery. Drafting assistance shortens analyst time per edit while keeping a certified reviewer in the approval path. Provenance, meaning every rule traceable to a document version and a verbatim sentence, turns appeal defense from an archaeology exercise into a query. And the inverse of drift detection, finding requirements no edit currently enforces, surfaces recoverable spend rather than only protecting against error.'),

      h1('Threats'),
      lead('A wrong automated edit is worse than no edit. ',
        'A false positive denies a legitimate claim, triggers an appeal, consumes staff time on both sides, and damages the provider relationship. Any system that authors rules must be evaluated on false positives first and coverage second.'),
      lead('Models fabricate citations and drop conditions. ',
        'In my own prototype the extractor produced a rule that silently omitted an alternative qualifying criterion, which would have denied every insulin pump user. It was caught because verification was built in, not because the output looked wrong.'),
      lead('Regulation is tightening around automated denial. ',
        'Several states have restricted the use of artificial intelligence as the sole basis for utilization review decisions. A design placing a model in the decision path invites both regulatory and litigation exposure.'),
      lead('Code set licensing constrains what can be built and shared. ',
        'CPT descriptors are AMA-licensed, which shapes what may be redistributed, embedded in a model, or exposed to a subcontractor.'),
      lead('Competitors are already moving. ',
        'Policy-to-rules conversion is being marketed today. The defensible asset is not the model, which anyone can rent.'),

      h1('Recommendations for Cotiviti'),
      lead('1. Build policy-change regression monitoring over the existing edit library first. ',
        'Not an authoring product. A service that continuously watches source documents and returns a ranked worklist of edits a revision has invalidated, priced by replaying recent claims against the old and corrected rule. It sells as risk reduction, requires no change to how edits are written, and produces a number that makes a reviewer act.'),
      lead('2. Treat rules as code, and keep the model out of the decision path. ',
        'Immutable versioned rules with a bidirectional index from document version to derived edit; point-in-time adjudication so a three-year-old denial can be reproduced against the policy in force on the date of service; and promotion through shadow mode and canary before an edit affects payment. Models author upstream where a human reviews. Deterministic code executes. This is what makes automation defensible to a regulator, an auditor, and an appeals board.'),
      lead('3. Invest in the claim attribute vocabulary, not the model. ',
        'The transferable asset is the structured vocabulary policy requirements are expressed against, per clinical domain, mapped onto real claim data. Models are rented and replaced every few months; a curated vocabulary tied to an installed base is not. In my prototype the pipeline generalized across documents unchanged. The schema was the only part needing authoring, and the only part that limited what could be encoded.'),

      h1('Prototype and results'),
      p('To test these claims I built a working pipeline against genuine CMS documents: Medicare LCD L33822 in the version effective 01/01/2020 and the revision effective 07/18/2021. It converts policy prose into executable rules with citations verified by exact search, adjudicates claims deterministically, and classifies each existing rule against the revised policy.'),
      p('It caught all three coverage changes CMS documented for that revision with no false alarms, scored against the revision history CMS publishes inside the document rather than against labels I created. It correctly reported no change across a separate pair of consecutive 2024 versions, reaching that conclusion before spending any model calls. Six of twenty sample claims changed decision once stale rules were corrected. Round-trip verification, which decompiles a rule back into prose and compares it against its source, independently found the omitted pump criterion with no reference answer available; using it to resolve a disputed extraction raised agreement with a hand-authored ruleset from six of seven to seven of seven.'),
      p('The prototype still fails its own quality gate on two rules, one of which encodes a per-30-day limit the claim schema cannot express. That failure is reported rather than suppressed, and it is the clearest evidence for recommendation three.'),

      new Paragraph({ children: [new PageBreak()] }),
      new Paragraph({
        spacing: { after: 200 },
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: 'References', font: FONT, size: H, bold: true })],
      }),
      ref('American Diabetes Association Professional Practice Committee. (2026). 7. Diabetes technology: Standards of care in diabetes—2026. Diabetes Care, 49(Suppl. 1), S150–S165. https://doi.org/10.2337/dc26-S007'),
      ref('Centers for Medicare & Medicaid Services. (2021). Local coverage determination: Glucose monitors (L33822), revision effective July 18, 2021. Medicare Coverage Database. https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33822'),
      ref('Centers for Medicare & Medicaid Services. (2025). Local coverage article: Glucose monitor — Policy article (A52464). Medicare Coverage Database. https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId=52464'),
      ref('Centers for Medicare & Medicaid Services. (2026a). MCD archive search. https://localcoverage.cms.gov/mcd_archive'),
      ref('Centers for Medicare & Medicaid Services. (2026b). Coverage API documentation. https://api.coverage.cms.gov/docs/'),
      ref('Cohere Health. (2026). Policy Studio: Medical policy management for utilization management. https://www.coherehealth.com/utilization-management/policy-studio'),
      ref('Cotiviti. (2026a). Coding validation. https://www.cotiviti.com/solutions/payment-accuracy/coding-validation'),
      ref('Cotiviti. (2026b). The payment integrity guide for health plans. https://resources.cotiviti.com/payment-integrity/the-health-plan-guide-to-claims-payment-integrity'),
      ref('Cotiviti. (2026c). Inpatient claim review in 2026: 5 key trends and recommendations. https://resources.cotiviti.com/payment-integrity/inpatient-claim-review-in-2026'),
      ref('Han, J., Liu, Y., & Chen, W. (2026). CPGPrompt: Translating clinical guidelines into LLM-executable decision support. arXiv. https://arxiv.org/abs/2601.03475'),
      ref('Wang, L., Patel, R., & Osei, K. (2026). CodeClinic: Evaluating automation of coding skills for clinical reasoning agents. arXiv. https://arxiv.org/abs/2605.09675'),
      ref('Zelis. (2026). Payment integrity lessons from 2025 and what payers need for 2026. https://www.zelis.com/blog/payment-integrity-lessons-from-2025-and-what-payers-need-for-2026/'),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(__dirname + '/Report.docx', buf);
  console.log('wrote Report.docx');
});
