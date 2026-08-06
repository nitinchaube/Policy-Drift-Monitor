import React, { useState } from 'react'
import { Badge, DocText, Panel, Stat, money } from '../lib.jsx'

const VERDICT_ORDER = { CONTRADICTED: 0, MODIFIED: 1, UNADDRESSED: 2, SUPPORTED: 3 }

export default function Drift({ data }) {
  const [open, setOpen] = useState(null)
  const v2 = data.documents.v2
  const adj = data.adjudication
  const neg = data.negative_control

  const verdicts = [...data.drift].sort(
    (a, b) => VERDICT_ORDER[a.verdict] - VERDICT_ORDER[b.verdict] || a.rule_id.localeCompare(b.rule_id)
  )
  const findings = verdicts.filter((v) => v.verdict !== 'SUPPORTED')
  const active = verdicts.find((v) => v.rule_id === open) || null

  return (
    <div className="stack">
      <p className="note">
        The ruleset is held fixed and each rule is classified against the revised policy, one at
        a time. <strong>Re-extracting from both versions and diffing would not work</strong>: the
        extractor is not perfectly stable, so the diff would fill with our own nondeterminism
        rather than actual policy change. The model reports observations; the verdict is computed
        from a decision table.
      </p>

      <div className="stats">
        <Stat k="Rules audited" v={verdicts.length} />
        <Stat k="Contradicted" v={verdicts.filter((v) => v.verdict === 'CONTRADICTED').length} tone="bad" d="retire now" />
        <Stat k="Modified" v={verdicts.filter((v) => v.verdict === 'MODIFIED').length} tone="warn" d="needs re-authoring" />
        <Stat k="Still supported" v={verdicts.filter((v) => v.verdict === 'SUPPORTED').length} tone="good" />
        <Stat k="Claims affected" v={adj.flips.length} d={money(adj.recovered) + ' wrongly withheld'} tone="bad" />
      </div>

      <div className="split">
        <Panel title="Verdicts" sub="model observations on the left, derived verdict on the right" bodyClass="">
          <table>
            <thead>
              <tr>
                <th>Rule</th>
                <th>Present?</th>
                <th>In criteria list?</th>
                <th>Alters eligibility?</th>
                <th>Verdict</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {verdicts.map((v) => (
                <tr
                  key={v.rule_id}
                  className={`clickable ${open === v.rule_id ? 'open' : ''}`}
                  onClick={() => setOpen(open === v.rule_id ? null : v.rule_id)}
                >
                  <td className="mono">{v.rule_id}</td>
                  <td className="mono dim">{String(v.requirement_still_present)}</td>
                  <td className="mono dim">{String(v.was_item_in_criteria_list)}</td>
                  <td className="mono dim">{String(v.changes_what_claims_qualify)}</td>
                  <td><Badge kind={v.verdict}>{v.verdict}</Badge></td>
                  <td className="mono muted">{v.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel
          title={active ? `Evidence for ${active.rule_id}` : 'Evidence'}
          sub={active ? `in ${v2.pdf}` : 'select a rule'}
          bodyClass=""
        >
          {!active && <div className="empty">Select a rule to see the sentence the verdict rests on.</div>}
          {active && (
            <>
              <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>
                <div className="label">Wording differences the model found</div>
                <p className="note" style={{ margin: '5px 0 10px' }}>{active.wording_differences}</p>
                <div className="label">Explanation</div>
                <p className="note" style={{ margin: '5px 0 0' }}>{active.explanation}</p>
                {!active.verified && (
                  <div className="banner" style={{ marginTop: 10 }}>
                    The quoted evidence could not be found in the revised document, so this finding
                    was downgraded to human review and will never act automatically.
                  </div>
                )}
              </div>
              <DocText text={v2.text} span={active.evidence_span} variant="evidence" />
            </>
          )}
        </Panel>
      </div>

      <Panel title="Claims that changed decision" sub="same twenty claims, before and after correction" bodyClass="">
        {adj.flips.length === 0 && <div className="empty">No claim decisions changed.</div>}
        {adj.flips.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Claim</th><th>Change</th><th className="num">Amount</th><th>Caused by</th>
              </tr>
            </thead>
            <tbody>
              {adj.flips.map((f) => (
                <tr key={f.claim_id}>
                  <td className="mono">{f.claim_id}</td>
                  <td>
                    <span className="flip">
                      <span className="was">{f.was}</span>
                      <span className="arrow">→</span>
                      <Badge kind={f.now.toLowerCase()}>{f.now}</Badge>
                    </span>
                  </td>
                  <td className="num">{f.amount.toFixed(2)}</td>
                  <td className="mono muted">{f.caused_by.join(', ') || 'ruleset changed'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <div className="split">
        <Panel title="Negative control" sub="two consecutive official versions, 04/2024 and 10/2024">
          <p className="note">
            CMS revised only a HCPCS long descriptor between these, which lives outside the
            coverage criteria. A detector that fires here is broken.
          </p>
          <table>
            <tbody>
              <tr>
                <td>Tier 0 · raw bytes identical</td>
                <td className="mono"><Badge kind={neg.tier0_bytes_identical ? 'pay' : 'deny'}>{String(neg.tier0_bytes_identical)}</Badge></td>
              </tr>
              <tr>
                <td>Tier 1 · whitespace runs collapsed</td>
                <td className="mono"><Badge kind={neg.tier1_whitespace_collapsed_identical ? 'pay' : 'deny'}>{String(neg.tier1_whitespace_collapsed_identical)}</Badge></td>
              </tr>
              <tr>
                <td>Tier 1b · canonical form</td>
                <td className="mono"><Badge kind={neg.tier1b_canonical_identical ? 'pay' : 'deny'}>{String(neg.tier1b_canonical_identical)}</Badge></td>
              </tr>
              <tr>
                <td>Model calls spent</td>
                <td className="mono"><Badge kind="accent">{neg.model_calls_needed}</Badge></td>
              </tr>
            </tbody>
          </table>
          <p className="note" style={{ marginTop: 10 }}>
            Hashing failed here, because the PDF re-typeset itself. Collapsing whitespace runs
            also failed, because the newer file wrapped a line inside <span className="mono">(1)-(2)</span> and
            left a stray space. Only the canonical form shows the criteria are byte-identical.
            Stopping at tier 1 would have meant paying a model to read a document that did not
            change.
          </p>
        </Panel>

        <Panel title="Coverage gaps" sub={`${data.gaps.length} requirements no rule covers`} bodyClass="">
          <div style={{ padding: '10px 12px 0' }}>
            <p className="note">
              Requirements the policy states that the current ruleset does not enforce. These are
              real exposure, but they measure how incomplete the ruleset is rather than how good
              the detector is: the extraction only ever covered the CGM section.
            </p>
          </div>
          <table>
            <thead><tr><th>Requirement</th><th>Cited</th></tr></thead>
            <tbody>
              {data.gaps.map((g, i) => (
                <tr key={i}>
                  <td>{g.requirement}</td>
                  <td><Badge kind={g.verified ? 'pay' : 'deny'}>{g.verified ? 'verified' : 'unverified'}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  )
}
