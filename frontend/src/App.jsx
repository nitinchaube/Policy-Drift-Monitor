import React, { useEffect, useState } from 'react'
import PolicyStudio from './views/PolicyStudio.jsx'
import Claims from './views/Claims.jsx'
import Drift from './views/Drift.jsx'
import Scorecard from './views/Scorecard.jsx'

const TABS = [
  { id: 'policy', label: 'Policy Studio', count: (a) => a.working_ruleset.length },
  { id: 'claims', label: 'Claims', count: (a) => a.claims.length },
  { id: 'drift', label: 'Drift', count: (a) => a.drift.filter((v) => v.verdict !== 'SUPPORTED').length },
  { id: 'scorecard', label: 'Scorecard', count: null },
]

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('policy')

  useEffect(() => {
    fetch('/api/analysis')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  if (error) {
    return (
      <div className="app">
        <div className="main">
          <div className="banner">
            Could not reach the API: {error}. Start it with the <span className="mono">api</span>{' '}
            configuration, or run <span className="mono">python -m cli</span> in{' '}
            <span className="mono">backend/</span> for the headless report.
          </div>
        </div>
      </div>
    )
  }
  if (!data) return <div className="app"><div className="main"><div className="empty">Loading analysis…</div></div></div>

  const v1 = data.documents.v1
  const v2 = data.documents.v2

  return (
    <div className="app">
      <div className="topbar">
        <h1>Policy Drift Monitor</h1>
        <span className="doc">
          <b>{v1.label}</b> · Glucose Monitors · {v1.effective} → {v2.effective}
        </span>
        <span className="spacer" />
        <span className="meta">
          {data.model} · {data.cache.entries} cached responses · 0 live calls
        </span>
      </div>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.count && <span className="count">{t.count(data)}</span>}
          </button>
        ))}
      </nav>

      <div className="main">
        {tab === 'policy' && <PolicyStudio data={data} />}
        {tab === 'claims' && <Claims data={data} />}
        {tab === 'drift' && <Drift data={data} />}
        {tab === 'scorecard' && <Scorecard data={data} />}
      </div>
    </div>
  )
}
