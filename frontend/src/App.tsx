import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, json } from './api'
import type { Case, Session } from './api'
import { CaseWorkspace, LawLibrary } from './Workspace'
import { Chip, Empty, ErrorLine, Panel, errorMessage, field, formValues, shortDate, today, useTask } from './ui'

function SignIn({ onSignIn }: { onSignIn: (value: Session) => void }) {
  const task = useTask()
  function handleSignIn(event: FormEvent<HTMLFormElement>) {
    const values = formValues(event)
    void task.run(async () => {
      try {
        onSignIn(await api<Session>('/auth/login', undefined, json('POST', {
          username: field(values, 'username'), password: field(values, 'password'),
        })))
      } catch (reason) {
        throw new Error(reason instanceof Error ? reason.message : 'Unable to sign in')
      }
    })
  }

  return <main className="signin">
    <section className="signin-brand">
      <div className="brand-mark" aria-hidden="true">IC</div>
      <span className="signin-eyebrow">FINANCIAL FRAUD INVESTIGATION</span>
      <h1>Investigation<br />Copilot</h1>
      <p>One workspace to review evidence, trace synthetic transfers and prepare an officer-reviewed investigation plan.</p>
      <div className="signin-trail" aria-hidden="true"><i /><span /><i /><span /><i /><span /><i /></div>
      <span className="signin-caption">SYNTHETIC TRAINING WORKSPACE</span>
    </section>
    <section className="signin-form">
      <form onSubmit={handleSignIn}>
        <h2>Officer sign-in</h2>
        <p>Use a seeded training account to open the workspace.</p>
        <label>Username<input name="username" autoComplete="username" placeholder="demo.io" required /></label>
        <label>Password<input type="password" name="password" autoComplete="current-password" required /></label>
        <button className="primary" disabled={task.pending}>{task.pending ? 'Signing in…' : 'Sign in'}</button>
        <ErrorLine message={task.error} />
      </form>
    </section>
  </main>
}

function CaseIndex({ session, selectCase }: { session: Session; selectCase: (item: Case) => void }) {
  const [cases, setCases] = useState<Case[] | null>(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const task = useTask()
  const token = session.access_token
  const mayCreate = ['IO', 'SHO'].includes(session.officer.role)

  useEffect(() => {
    const abort = new AbortController()
    api<Case[]>('/cases', token, { signal: abort.signal }).then(setCases).catch((reason: unknown) => {
      if (!abort.signal.aborted) setError(errorMessage(reason))
    })
    return () => abort.abort()
  }, [token])

  const filtered = cases?.filter((item) => `${item.reference} ${item.title}`.toLowerCase().includes(query.toLowerCase()))
  function addCase(event: FormEvent<HTMLFormElement>) {
    const values = formValues(event)
    void task.run(async () => {
      selectCase(await api<Case>('/cases', token, json('POST', {
        reference: field(values, 'reference'), title: field(values, 'title'),
        summary: field(values, 'summary'), opened_on: field(values, 'opened_on'),
      })))
    })
  }

  return <>
    <header className="pagehead">
      <div><span className="eyebrow">CASE MANAGEMENT</span><h1>Case register</h1>
        <p>Open an investigation to review evidence, next steps and officer approvals.</p></div>
      {mayCreate && <button className="primary" onClick={() => setShowForm(!showForm)}>{showForm ? 'Cancel' : '+ New case'}</button>}
    </header>
    {showForm && <Panel title="New training case">
      <form className="form-grid" onSubmit={addCase}>
        <label>Case reference<input name="reference" placeholder="DEMO-FIR-025" maxLength={40} required /></label>
        <label>Opened on<input name="opened_on" type="date" defaultValue={today()} max={today()} required /></label>
        <label className="full">Case title<input name="title" required maxLength={140} /></label>
        <label className="full">Summary<textarea name="summary" required rows={3} maxLength={4000} /></label>
        <div className="full"><button className="primary" disabled={task.pending}>Create case</button></div>
        <ErrorLine message={task.error} />
      </form>
    </Panel>}
    <div className="metrics">
      <div className="metric"><span>Accessible cases</span><strong>{cases?.length ?? '—'}</strong></div>
      <div className="metric"><span>Investigating unit</span><strong className="small-value">{session.officer.station}</strong></div>
      <div className="metric"><span>Case type</span><strong className="small-value">Online financial fraud</strong></div>
    </div>
    <Panel title="Investigations" hint={cases ? `${filtered?.length} of ${cases.length} cases` : undefined}
      action={<label className="search"><span className="sr-only">Search cases</span>
        <input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search cases…" />
      </label>}>
      <ErrorLine message={error} />
      {!cases && !error && <Empty>Loading cases…</Empty>}
      {filtered?.length === 0 && <Empty>{query ? 'No cases match your search.' : 'No cases assigned.'}</Empty>}
      {!!filtered?.length && <div className="table-scroll"><table>
        <thead><tr><th>Case reference</th><th>Investigation</th><th>Opened</th><th><span className="sr-only">Open</span></th></tr></thead>
        <tbody>{filtered.map(item => <tr key={item.id}>
          <td className="mono">{item.reference}</td><td className="row-emphasis">{item.title}</td>
          <td>{shortDate(item.opened_on)}</td><td><button className="table-link" onClick={() => selectCase(item)}>Open <span aria-hidden="true">→</span></button></td>
        </tr>)}</tbody>
      </table></div>}
    </Panel>
  </>
}

export function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [activeCase, setActiveCase] = useState<Case | null>(null)
  const [showLaw, setShowLaw] = useState(false)

  if (!session) return <SignIn onSignIn={setSession} />
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark" aria-hidden="true">IC</div><span>Investigation<br />Copilot</span></div>
      <span className="rail-title">WORKSPACE</span>
      <nav aria-label="Workspace">
        <button className={showLaw ? '' : 'nav-active'} onClick={() => { setActiveCase(null); setShowLaw(false) }}>
          <span aria-hidden="true">▤</span> Case register
        </button>
        <button className={showLaw ? 'nav-active' : ''} onClick={() => setShowLaw(true)}>
          <span aria-hidden="true">≡</span> Legal library
        </button>
      </nav>
      <div className="rail-bottom">
        <div className="rail-user"><div className="avatar" aria-hidden="true">{session.officer.name.slice(0, 1)}</div>
          <div><strong>{session.officer.name}</strong><small>{session.officer.role} · {session.officer.station}</small></div>
        </div>
        <button className="signout" onClick={() => { setSession(null); setActiveCase(null); setShowLaw(false) }}>Sign out</button>
      </div>
    </aside>
    <div className="workspace-shell">
      <header className="topbar">
        <span>{showLaw ? 'Legal library' : activeCase ? 'Case workspace' : 'Case register'}</span>
        <Chip tone="amber"><span className="status-dot" aria-hidden="true" /> Synthetic training data</Chip>
      </header>
      <main className="workspace">
        {showLaw ? <LawLibrary token={session.access_token} /> : activeCase
          ? <CaseWorkspace key={activeCase.id} item={activeCase} session={session} onBack={() => setActiveCase(null)} />
          : <CaseIndex session={session} selectCase={setActiveCase} />}
      </main>
    </div>
  </div>
}
