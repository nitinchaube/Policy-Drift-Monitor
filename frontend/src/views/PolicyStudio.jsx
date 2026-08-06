import React, { useMemo, useState } from 'react'
import { Badge, Chips, DocText, Panel } from '../lib.jsx'

export default function PolicyStudio({ data }) {
  const [version, setVersion] = useState('v1')
  const [source, setSource] = useState('model')
  const [activeId, setActiveId] = useState(null)

  const doc = data.documents[version]
  const stability = data.stability

  const modelRules = data.extraction.accepted
  const rtByRule = Object.fromEntries((data.roundtrip || []).map((f) => [f.rule_id, f]))
  const refRules = data.reference_ruleset
  const showingModel = source === 'model'
  const rules = showingModel ? modelRules : refRules

  const downstreamIsModel = data.gate.passed

  // keyed on the cited sentence, matching how the backend tracks stability
  const agreement = useMemo(() => {
    const m = {}
    if (stability) for (const r of stability.rules) m[r.cite] = r
    return m
  }, [stability])

  const active = rules.find((r) => r.rule_id === activeId) || null

  // a rule's span indexes into the version it came from; re-locate for v2 instead
  // of reusing the v1 offset
  const span = useMemo(() => {
    if (!active) return null
    if (version === 'v1') return active.source_span
    const idx = doc.text
      .replace(/\s+/g, ' ')
      .indexOf(active.source_sentence.replace(/\s+/g, ' ').trim())
    return idx === -1 ? null : null
  }, [active, version, doc.text])

  const missingInV2 = version === 'v2' && active && !span

  return (
    <div className="stack">
      <p className="note">
        The policy on the left goes to the model, which returns rules in a fixed schema. Each
        rule quotes the sentence it came from and that quote is verified by exact search, so a
        fabricated citation is thrown away rather than trusted. <strong>Select a rule</strong> to
        highlight its source. Switch to v2 to see which cited sentences survived the 07/18/2021
        revision.
      </p>

      <div className={data.gate.passed ? 'banner info' : 'banner'}>
        <strong>
          The model extracted {modelRules.length} rule{modelRules.length === 1 ? '' : 's'} from the{' '}
          {data.extraction.section.name} section
          {data.extraction.rejected.length > 0 &&
            `, and ${data.extraction.rejected.length} more were rejected by validation`}
          .
        </strong>{' '}
        {downstreamIsModel ? (
          <>The extraction gate passed, so these rules are the ones used for drift detection.</>
        ) : (
          <>
            The extraction gate <b>failed</b> ({data.gate.reasons.join('; ')}), so the
            hand-authored reference ruleset is what feeds drift detection instead. Both sets are
            below. In production this gate is a human reviewer approving rules before they are
            promoted.
          </>
        )}
      </div>

      <div className="studio">
        <Panel
          title="Source document"
          sub={`${doc.pdf} · effective ${doc.effective}${doc.ends ? ` to ${doc.ends}` : ''} · ${doc.text.length.toLocaleString()} chars`}
          bodyClass=""
          right={
            <span className="btngroup">
              <button className="btn" aria-pressed={version === 'v1'} onClick={() => setVersion('v1')}>v1 · 2020</button>
              <button className="btn" aria-pressed={version === 'v2'} onClick={() => setVersion('v2')}>v2 · 2021</button>
            </span>
          }
        >
          {missingInV2 && (
            <div style={{ padding: '10px 12px 0' }}>
              <div className="banner">
                The sentence behind <span className="mono">{active.rule_id}</span> does not appear in
                this version. That is either a deleted requirement or a reworded one, and it is
                exactly what the Drift tab resolves.
              </div>
            </div>
          )}
          <DocText text={doc.text} span={span} />
        </Panel>

        <Panel
          title="Derived rules"
          sub={showingModel
            ? `${rules.length} produced by ${data.model}${downstreamIsModel ? ', used downstream' : ', not used downstream'}`
            : `${rules.length} hand-authored${downstreamIsModel ? ', gold standard only' : ', used downstream'}`}
          bodyClass="rulelist"
          right={
            <span className="row" style={{ gap: 6 }}>
              <span className="btngroup">
                <button
                  className="btn"
                  aria-pressed={showingModel}
                  onClick={() => { setSource('model'); setActiveId(null) }}
                >
                  Model · {modelRules.length}
                </button>
                <button
                  className="btn"
                  aria-pressed={!showingModel}
                  onClick={() => { setSource('reference'); setActiveId(null) }}
                >
                  Reference · {refRules.length}
                </button>
              </span>
              <a className="btn" href="/api/export/python?which=corrected" download="policy_rules.py">
                Export as Python
              </a>
            </span>
          }
        >
          {rules.length === 0 && (
            <div className="empty">
              The extractor returned nothing. That happens when there is no API key and no cached
              response for this document, in which case only the reference ruleset is available.
            </div>
          )}
          {rules.map((r) => {
            const key = r.source_sentence.replace(/\s+/g, ' ').trim().toLowerCase()
              .replace(/^\s*\(?\d{1,2}[.)]\s+/, '')
            const ag = agreement[key]
            return (
              <div
                key={r.rule_id}
                className={`rulecard ${activeId === r.rule_id ? 'active' : ''}`}
                onClick={() => setActiveId(activeId === r.rule_id ? null : r.rule_id)}
              >
                <div className="row" style={{ gap: 8 }}>
                  <span className="rid">{r.rule_id}</span>
                  <span className="spacer" style={{ flex: 1 }} />
                  {r.codifiable === false && <Badge kind="review">human judgment</Badge>}
                  {showingModel && ag && !ag.unanimous && (
                    <Badge kind="review">{ag.agreement}/{stability.runs} runs</Badge>
                  )}
                  {showingModel && rtByRule[r.rule_id]?.severity === 'material' && (
                    <Badge kind="deny">round-trip: omission</Badge>
                  )}
                  <Badge kind={r.logic.on_fail === 'DENY' ? 'deny' : 'review'}>
                    on fail: {r.logic.on_fail}
                  </Badge>
                </div>
                <div className="rtitle">{r.title}</div>
                <div className="rsum">{r.summary}</div>
                <Chips conds={r.logic.requires} combinator={r.logic.combinator} />
                {activeId === r.rule_id && (
                  <div className="rcite">“{r.source_sentence}”</div>
                )}
              </div>
            )
          })}
        </Panel>
      </div>
    </div>
  )
}
