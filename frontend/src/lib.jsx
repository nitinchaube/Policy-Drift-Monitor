import React, { useEffect, useRef } from 'react'

export const money = (n) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const Badge = ({ kind, children }) => (
  <span className={`badge ${String(kind || 'neutral').toLowerCase()}`}>{children}</span>
)

export const Panel = ({ title, sub, right, children, bodyClass = 'body' }) => (
  <section className="panel">
    {(title || right) && (
      <header>
        {title && <h2>{title}</h2>}
        {sub && <span className="sub">{sub}</span>}
        <span className="spacer" />
        {right}
      </header>
    )}
    <div className={bodyClass}>{children}</div>
  </section>
)

export const Stat = ({ k, v, d, tone }) => (
  <div className="stat">
    <div className="k">{k}</div>
    <div className={`v ${tone || ''}`}>{v}</div>
    {d && <div className="d">{d}</div>}
  </div>
)

/**
 * Renders a document with one span highlighted, and scrolls it into view.
 *
 * The span comes from locate() on the backend, which finds the model's quoted
 * sentence in the document rather than trusting the model to count characters.
 * That is why this can be a plain substring slice and still land correctly.
 */
export function DocText({ text, span, variant = '' }) {
  const preRef = useRef(null)
  const markRef = useRef(null)

  useEffect(() => {
    const pre = preRef.current
    const mark = markRef.current
    if (!pre || !mark) return
    // scrollIntoView moved the outer page, not this pane, so scroll it directly
    // (.doctext is position:relative, making it the offsetParent). behavior:'smooth'
    // is a no-op here too, hence the plain assignment.
    pre.scrollTop = Math.max(0, mark.offsetTop - pre.clientHeight / 2 + mark.offsetHeight / 2)
  }, [span?.[0], span?.[1], text])

  if (!span) return <pre className="doctext" ref={preRef}>{text}</pre>
  const [a, b] = span
  return (
    <pre className="doctext" ref={preRef}>
      {text.slice(0, a)}
      <mark ref={markRef} className={variant}>{text.slice(a, b)}</mark>
      {text.slice(b)}
    </pre>
  )
}

/** Human-readable form of one condition, e.g. bgm_testing_freq_per_day >= 4 */
export function condText(c) {
  if (c.op === 'is_true') return `${c.field} is true`
  if (c.op === 'is_false') return `${c.field} is false`
  const v = Array.isArray(c.value) ? `[${c.value.join(', ')}]` : String(c.value)
  return `${c.field} ${c.op} ${v}`
}

export const Chips = ({ conds, combinator }) => (
  <div className="chips">
    {conds.map((c, i) => (
      <React.Fragment key={i}>
        {i > 0 && <span className="chip"><b>{combinator === 'ANY' ? 'or' : 'and'}</b></span>}
        <span className="chip">{condText(c)}</span>
      </React.Fragment>
    ))}
  </div>
)
