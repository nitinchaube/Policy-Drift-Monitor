import React from 'react'
import { Badge, Panel, Stat, money } from '../lib.jsx'

const LIMITATIONS = [
  'n is tiny: three documented edits across two affected criteria, twenty synthetic claims, one document pair. These demonstrate behaviour; they are not statistically meaningful.',
  'The gold ruleset and the claim set were authored by the same person who built the extractor, so this is not an independent evaluation. Only the revision history is genuinely external, which is why it carries the most weight.',
  'Treating a criterion deleted from a closed list as CONTRADICTED rather than UNADDRESSED is a definition written into the prompt, not something the model discovered.',
  'One clinical area (DME glucose monitors), one document format, one payer. Nothing here shows it generalises.',
  'No OCR. Every source PDF has an extractable text layer; scanned policy would need more.',
  'Payer-provider contracts are not covered at all. No public corpus exists, and fabricating inputs would make the demonstration worthless.',
]

export default function Scorecard({ data }) {
  const s = data.scorecard
  const sc = data.extraction_score
  const st = data.stability
  const adj = data.adjudication

  return (
    <div className="stack">
      <p className="note">
        Every number here, including the unflattering ones. The drift detector is scored against
        the revision history <strong>CMS published inside the LCD itself</strong>, which means the
        evaluation set required no hand-labelling and is the one piece of ground truth not
        authored by this project.
      </p>

      <div className="stats">
        <Stat k="Documented edits caught" v={`${s.caught} / ${s.total_changes}`} tone={s.caught === s.total_changes ? 'good' : 'bad'} />
        <Stat k="False alarms" v={s.false_alarms.length} tone={s.false_alarms.length ? 'bad' : 'good'} />
        <Stat
          k="Must-not-flag traps"
          v={`${s.must_not_flag.filter((m) => m.passed).length} / ${s.must_not_flag.length}`}
          tone={s.must_not_flag.every((m) => m.passed) ? 'good' : 'bad'}
        />
        <Stat k="Extraction stability" v={st ? `${st.unanimous} / ${st.distinct}` : '—'} d={st ? `unanimous across ${st.runs} runs` : ''} />
        <Stat k="Wrongly withheld" v={money(adj.recovered)} d={`${adj.flips.length} claims changed`} tone="bad" />
      </div>

      <Panel title="Drift accuracy" sub={`vs the revision history published with the ${s.revision_effective_date} revision`} bodyClass="">
        <table>
          <thead>
            <tr><th></th><th>CMS revision text</th><th>Rule</th><th>Expected</th><th>Got</th></tr>
          </thead>
          <tbody>
            {s.documented_changes.map((c) => (
              <tr key={c.change_id}>
                <td><Badge kind={c.hit ? 'pay' : 'deny'}>{c.hit ? 'HIT' : 'MISS'}</Badge></td>
                <td>{c.revision_text}</td>
                <td className="mono">{c.rule_id || '—'}</td>
                <td className="mono dim">{c.expected}</td>
                <td className="mono">{c.got || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ padding: '10px 12px' }}>
          <p className="note" style={{ margin: 0 }}><strong>Note on the denominator.</strong> {s.scoring_notes}</p>
        </div>
      </Panel>

      <Panel title="Must-not-flag cases" sub="real false-positive traps taken from the document pair" bodyClass="">
        <table>
          <thead><tr><th></th><th>Case</th><th>Rule</th><th>Expected</th><th>Got</th><th>Why it is a trap</th></tr></thead>
          <tbody>
            {s.must_not_flag.map((m) => (
              <tr key={m.case_id}>
                <td><Badge kind={m.passed ? 'pay' : 'deny'}>{m.passed ? 'PASS' : 'FAIL'}</Badge></td>
                <td className="mono">{m.case_id}</td>
                <td className="mono">{m.rule_id}</td>
                <td className="mono dim">{m.expected}</td>
                <td className="mono">{m.got}</td>
                <td className="muted">{m.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <div className="split">
        <Panel title="Extraction quality" sub={data.gate.passed ? 'gate passed' : 'gate failed'}>
          {sc ? (
            <>
              <table>
                <tbody>
                  <tr><td>Gold rules in the extracted section</td><td className="num">{sc.in_scope}</td></tr>
                  <tr><td>Found by the extractor</td><td className="num">{sc.found}</td></tr>
                  <tr><td>With identical requirements</td><td className="num">{sc.same_requirements}</td></tr>
                  <tr><td>Identical throughout (including gating)</td><td className="num">{sc.identical}</td></tr>
                  <tr><td>Missed</td><td className="num">{sc.missed.length}</td></tr>
                  <tr><td>Beyond gold (found, human missed)</td><td className="num">{(sc.beyond_gold || []).length}</td></tr>
                </tbody>
              </table>
              {sc.differences.map((d, i) => (
                <div key={i} style={{ marginTop: 10 }}>
                  <div className="label">Encoded differently: {d.title}</div>
                  <div className="cite" style={{ margin: '4px 0 0' }}>gold&nbsp;&nbsp;{d.gold.join('  ·  ')}</div>
                  <div className="cite" style={{ margin: '2px 0 0' }}>model&nbsp;{d.model.join('  ·  ')}</div>
                </div>
              ))}
              <div className="banner" style={{ marginTop: 12 }}>
                <strong>Gate {data.gate.passed ? 'passed' : 'failed'}.</strong>{' '}
                {data.gate.reasons.join('; ')}
                {!data.gate.passed && (
                  <> — so the hand-authored reference ruleset was carried into drift detection instead.
                    The sections above therefore measure the drift detector, not the extractor. In
                    production this gate is a human reviewer approving rules before promotion.</>
                )}
              </div>
            </>
          ) : (
            <div className="empty">Not measured. Needs an API key or a warm cache.</div>
          )}
        </Panel>

        <Panel title="Extraction stability" sub={st ? `${st.runs} independent runs at temperature 0` : ''} bodyClass="">
          {!st && <div className="empty">Not measured.</div>}
          {st && (
            <table>
              <thead><tr><th>Agreement</th><th>Rule</th></tr></thead>
              <tbody>
                {st.rules.map((r, i) => (
                  <tr key={i}>
                    <td>
                      <Badge kind={r.unanimous ? 'pay' : 'review'}>{r.agreement}/{st.runs}</Badge>
                    </td>
                    <td className={r.unanimous ? '' : 'muted'}>{r.title || r.cite}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      </div>

      <Panel title="Round-trip verification" sub="rule decompiled back to prose, then compared against its source, with no gold ruleset involved" bodyClass="">
        <div style={{ padding: '10px 12px 0' }}>
          <p className="note">
            Scoring against a hand-authored gold set only works on documents somebody already
            did by hand, which is none of the documents that matter. This check needs no labels:
            the source sentence is its own ground truth. It found the dropped CSII pump
            alternative independently, and it is what settled the disputed vote during extraction.
          </p>
        </div>
        <table>
          <thead><tr><th></th><th>Rule</th><th>What the logic actually says</th><th>Material omission</th></tr></thead>
          <tbody>
            {(data.roundtrip || []).map((f) => (
              <tr key={f.rule_id}>
                <td><Badge kind={f.severity === 'none' ? 'pay' : f.severity === 'minor' ? 'review' : 'deny'}>{f.severity === 'none' ? 'FAITHFUL' : f.severity.toUpperCase()}</Badge></td>
                <td className="mono">{f.rule_id}</td>
                <td className="muted">{f.decompiled}</td>
                <td className="muted">{f.severity === 'none' ? '\u2014' : f.missing_from_rule}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="Known limitations">
        <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-2)' }}>
          {LIMITATIONS.map((l, i) => (
            <li key={i} style={{ marginBottom: 6, maxWidth: '90ch' }}>{l}</li>
          ))}
        </ul>
      </Panel>
    </div>
  )
}
