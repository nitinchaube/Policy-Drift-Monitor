import React, { useState } from 'react'
import { Badge, Panel, Stat, money } from '../lib.jsx'

const STATUS_TONE = { PAY: 'pay', DENY: 'deny', REVIEW: 'review' }

export default function Claims({ data }) {
  const [which, setWhich] = useState('before')
  const [open, setOpen] = useState(null)

  const adj = data.adjudication
  const results = adj[which]
  const tally = which === 'before' ? adj.tally_before : adj.tally_after
  const flipped = new Set(adj.flips.map((f) => f.claim_id))

  return (
    <div className="stack">
      <p className="note">
        The same twenty claims, adjudicated against the ruleset before and after drift
        correction. No model is involved in any of these decisions: rules compile to Python
        predicates and run deterministically. <strong>Select a claim</strong> to see every rule
        that was evaluated and the policy sentence behind each outcome.
      </p>

      <div className="stats">
        <Stat k="Paid" v={tally.PAY} tone="good" />
        <Stat k="Denied" v={tally.DENY} tone="bad" />
        <Stat k="Manual review" v={tally.REVIEW} tone="warn" />
        <Stat k="Changed" v={adj.flips.length} d={`of ${data.claims.length} claims`} />
        <Stat k="Wrongly withheld" v={money(adj.recovered)} d="across DENY to PAY flips" tone="bad" />
      </div>

      <Panel
        title="Claims"
        sub={`${data.claims.length} accepted, ${data.claims_rejected.length} rejected at load`}
        bodyClass=""
        right={
          <span className="btngroup">
            <button className="btn" aria-pressed={which === 'before'} onClick={() => setWhich('before')}>
              Before correction
            </button>
            <button className="btn" aria-pressed={which === 'after'} onClick={() => setWhich('after')}>
              After correction
            </button>
          </span>
        }
      >
        <table>
          <thead>
            <tr>
              <th>Claim</th>
              <th>Date of service</th>
              <th>HCPCS</th>
              <th>Diagnosis</th>
              <th className="num">Units</th>
              <th className="num">Billed</th>
              <th>Decision</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {data.claims.map((c) => {
              const res = results[c.claim_id]
              const isOpen = open === c.claim_id
              const fired = res.fired.filter((f) => f.outcome)
              return (
                <React.Fragment key={c.claim_id}>
                  <tr
                    className={`clickable ${isOpen ? 'open' : ''}`}
                    onClick={() => setOpen(isOpen ? null : c.claim_id)}
                  >
                    <td className="mono">
                      {c.claim_id}
                      {flipped.has(c.claim_id) && <> <Badge kind="accent">changed</Badge></>}
                    </td>
                    <td className="mono dim">{c.date_of_service}</td>
                    <td className="mono">{c.procedure_code}</td>
                    <td className="mono dim">{c.diagnosis_codes.join(', ')}</td>
                    <td className="num">{c.units}</td>
                    <td className="num">{c.billed_amount.toFixed(2)}</td>
                    <td><Badge kind={STATUS_TONE[res.decision]}>{res.decision}</Badge></td>
                    <td className="muted">
                      {fired.length
                        ? fired.map((f) => f.rule_id).join(', ')
                        : 'no rule objected'}
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="detail">
                      <td colSpan={8}>
                        <div className="inner">
                          {c._scenario && (
                            <p className="note" style={{ marginTop: 6 }}>{c._scenario}</p>
                          )}
                          {(() => {
                            const ex = data.explanations?.[which]?.[c.claim_id]
                            if (!ex) return null
                            return (
                              <div className="explain">
                                <div className="label">What the provider is told</div>
                                <div className="headline">{ex.headline}</div>
                                <p>{ex.explanation}</p>
                                <p className="todo"><b>Next step.</b> {ex.what_to_do}</p>
                              </div>
                            )
                          })()}
                          <div className="label" style={{ margin: '8px 0 4px' }}>
                            Every rule evaluated
                          </div>
                          {res.trace.map((t, i) => (
                            <div key={i}>
                              <div className="tracerow">
                                <span className="tid">{t.rule_id}</span>
                                <span className="tst">
                                  <Badge
                                    kind={
                                      t.status === 'PASS' ? 'pay'
                                        : t.status === 'FAIL' ? 'deny'
                                          : t.status === 'NOT_APPLICABLE' ? 'neutral' : 'review'
                                    }
                                  >
                                    {t.status}
                                  </Badge>
                                </span>
                                <span className="muted">{t.why || ''}</span>
                              </div>
                              {t.citation && (
                                <div className="cite">“{t.citation}”</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </Panel>

      {data.claims_rejected.length > 0 && (
        <Panel title="Rejected at load" sub="malformed records never reach the engine" bodyClass="">
          <table>
            <thead><tr><th>Claim</th><th>Reason</th></tr></thead>
            <tbody>
              {data.claims_rejected.map((r, i) => (
                <tr key={i}>
                  <td className="mono">{r.claim_id}</td>
                  <td className="muted">{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </div>
  )
}
