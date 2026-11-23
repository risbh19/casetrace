import { useEffect, useState } from 'react'
import { api } from './api'
import type { Case, Session } from './api'
import { ErrorLine, Panel, errorMessage } from './ui'

type Overview = { case_count: number; open_steps: number; pending_notices: number; overdue_reminders: number; recent_cases: Case[] }

export function Supervision({ session, onOpen }: { session: Session; onOpen: (item: Case) => void }) {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const abort = new AbortController()
    void api<Overview>('/dashboard', session.access_token, { signal: abort.signal }).then(setOverview)
      .catch((reason: unknown) => { if (!abort.signal.aborted) setError(errorMessage(reason)) })
    return () => abort.abort()
  }, [session.access_token])
  return <div className="stack">
    <h1>Supervision</h1><p>Current records in {session.officer.station}. Reminder dates require officer review.</p>
    <ErrorLine message={error} />
    <div className="metrics">{[
      ['Accessible cases', overview?.case_count], ['Open checklist steps', overview?.open_steps],
      ['Drafts awaiting review', overview?.pending_notices], ['Overdue reminders', overview?.overdue_reminders],
    ].map(([label, value]) => <div className="metric" key={label}><span>{label}</span><strong>{value ?? '—'}</strong></div>)}</div>
    <Panel title="Recent investigations">
      {overview?.recent_cases.map(item => <button className="row-button" key={item.id} onClick={() => onOpen(item)}>
        <span>{item.reference} · {item.title}</span><span>Open →</span>
      </button>)}
    </Panel>
  </div>
}
