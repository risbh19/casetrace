import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, json, saveOriginal } from './api'
import type { Answer, AuditEvent, Case, Document, DocumentDetail, Notice, PlanStep, Reminder, Session, Trail } from './api'
import { Chip, CitationLink, Empty, ErrorLine, Panel, errorMessage, field, formValues, inr, shortDate, today, useTask } from './ui'

function useLoad<T>(path: string, token: string) {
  const [value, setValue] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const abort = new AbortController()
    api<T>(path, token, { signal: abort.signal }).then((data) => { setValue(data); setError('') })
      .catch((reason: unknown) => { if (!abort.signal.aborted) setError(errorMessage(reason)) })
    return () => abort.abort()
  }, [path, token, revision])
  return { value, setValue, error, refresh: () => setRevision(n => n + 1) }
}

type CaseProps = { path: string; token: string; canEdit: boolean }

function Evidence({ path, token, canEdit }: CaseProps) {
  const list = useLoad<Document[]>(path, token)
  const task = useTask()
  const [selected, setSelected] = useState<DocumentDetail | null>(null)
  function upload(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    const values = formValues(event)
    const file = values.get('evidence')
    if (!(file instanceof File)) return
    void task.run(async () => {
      if (file.size > 8 * 1024 * 1024) throw new Error('Evidence files are limited to 8 MiB.')
      const detail = await api<DocumentDetail>(path, token, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream', 'X-Filename': encodeURIComponent(file.name) },
        body: file,
      })
      setSelected(detail)
      list.refresh()
      form.reset()
      task.setNote('Evidence saved.')
    })
  }
  return <div className="stack">
    <Panel title="Evidence register" hint="Original files, extracted text and SHA-256 hashes.">
      {canEdit && <form className="inline-form" onSubmit={upload}>
        <label>Evidence file<input name="evidence" type="file" accept=".txt,.csv,.pdf,.png,.jpg,.jpeg" required /></label>
        <button className="primary" disabled={task.pending}>{task.pending ? 'Processing…' : 'Upload evidence'}</button>
      </form>}
      <ErrorLine message={list.error || task.error} />
      {task.note && <p className="feedback" role="status">{task.note}</p>}
      {!list.value?.length && <Empty>{list.value ? 'No evidence uploaded.' : 'Loading evidence…'}</Empty>}
      {!!list.value?.length && <div className="rows">{list.value.map(doc =>
        <button key={doc.id} className={`row-button ${selected?.id === doc.id ? 'row-selected' : ''}`}
          disabled={task.pending} onClick={() => void task.run(async () => {
            setSelected(await api<DocumentDetail>(`${path}/${doc.id}`, token))
          })}>
          <span><strong>{doc.filename}</strong><small>{shortDate(doc.created_at)} · {Math.ceil(doc.size / 1024)} KB</small></span>
          <span className="muted">Review →</span>
        </button>)}</div>}
    </Panel>
    {selected && <Panel title={selected.filename}
      hint={`Extraction: ${selected.extraction_method.replaceAll('-', ' ')}`}
      action={<button className="secondary" disabled={task.pending} onClick={() => void task.run(
        () => saveOriginal(`${path}/${selected.id}/original`, token, selected.filename),
      )}>Download original</button>}>
      <div className="hash"><span>SHA-256</span><code>{selected.sha256}</code></div>
      {selected.entities.length > 0 && <ul className="entities">{selected.entities.map(entity =>
        <li key={`${entity.kind}:${entity.value}`}><span>{entity.kind}</span> {entity.value}</li>)}</ul>}
      {selected.text ? <pre className="document-text">{selected.text}</pre>
        : <Empty>No text was extracted. Review the original file.</Empty>}
    </Panel>}
  </div>
}

function InvestigationPlan({ path, token, canEdit }: CaseProps) {
  const data = useLoad<PlanStep[]>(path, token)
  const task = useTask()
  return <Panel title="Investigation plan" hint="Checklist suggestions and legal references for this case."
    action={canEdit && <button className="primary" disabled={task.pending} onClick={() => void task.run(async () => {
      data.setValue(await api<PlanStep[]>(path, token, { method: 'POST' }))
      task.setNote('Plan reviewed against the case checklist.')
    })}>{task.pending ? 'Updating…' : data.value?.length ? 'Refresh plan' : 'Generate plan'}</button>}>
    <ErrorLine message={data.error || task.error} />
    {task.note && <p className="feedback" role="status">{task.note}</p>}
    {!data.value?.length && <Empty>{data.value ? 'Generate a checklist for this case to get started.' : 'Loading plan…'}</Empty>}
    {!!data.value?.length && <ol className="steps">{data.value.map(step => <li key={step.id}>
      <div className="step-title"><strong>{step.title}</strong><Chip tone={step.status === 'DONE' ? 'green' : 'slate'}>
        {step.status === 'DONE' ? 'Done' : 'Open'}</Chip></div>
      <p>{step.instructions}</p>
      <div className="step-meta">
        {step.legal_basis === 'unsure' ? <Chip tone="amber">Legal basis unsure</Chip> : <CitationLink item={step.legal_basis} />}
        <span>Target {shortDate(step.due_date)}</span>
        {canEdit && <button className="table-link" disabled={task.pending} onClick={() => void task.run(async () => {
          const updated = await api<PlanStep>(`${path}/${step.id}`, token, json('PATCH', {
            status: step.status === 'DONE' ? 'OPEN' : 'DONE',
          }))
          data.setValue(data.value!.map(item => item.id === updated.id ? updated : item))
        })}>{step.status === 'DONE' ? 'Reopen' : 'Mark done'}</button>}
      </div>
    </li>)}</ol>}
  </Panel>
}

const noticeTitles: Record<string, string> = {
  bank_statement: 'Bank statement', bank_freeze: 'Funds preservation review', telecom_cdr: 'Telecom records',
}

function Notices({ path, token, canEdit, session }: CaseProps & { session: Session }) {
  const data = useLoad<Notice[]>(path, token)
  const task = useTask()
  const [expanded, setExpanded] = useState<number | null>(null)
  const canReview = session.officer.role !== 'IO'
  function createNotice(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    const values = formValues(event)
    void task.run(async () => {
      const notice = await api<Notice>(path, token, json('POST', {
        kind: field(values, 'kind'), recipient: field(values, 'recipient'), facts: field(values, 'facts'),
      }))
      setExpanded(notice.id)
      data.refresh()
      form.reset()
      task.setNote('Draft saved for officer review.')
    })
  }

  function review(notice: Notice, action: 'approve' | 'send') {
    void task.run(async () => {
      const updated = await api<Notice>(`${path}/${notice.id}/${action}`, token, { method: 'POST' })
      data.setValue(data.value!.map(item => item.id === updated.id ? updated : item))
      task.setNote(action === 'send' ? 'Simulated send recorded.' : 'Officer approval recorded.')
    })
  }

  return <div className="stack">
    {canEdit && <Panel title="Draft a notice" hint="Drafts require a separate supervisor’s approval.">
      <form className="form-grid" onSubmit={createNotice}>
        <label>Notice type<select name="kind">{Object.entries(noticeTitles).map(([key, title]) =>
          <option key={key} value={key}>{title}</option>)}</select></label>
        <label>Training recipient<input name="recipient" placeholder="Demo Bank" maxLength={120} required /></label>
        <label className="full">Case facts<textarea name="facts" required rows={3} maxLength={1200} /></label>
        <div className="full"><button className="primary" disabled={task.pending}>Save draft</button></div>
      </form>
    </Panel>}
    <Panel title="Notice register" hint="Delivery for this workspace is simulated.">
      <ErrorLine message={data.error || task.error} />
      {task.note && <p className="feedback" role="status">{task.note}</p>}
      {!data.value?.length && <Empty>{data.value ? 'No notices drafted.' : 'Loading notices…'}</Empty>}
      {!!data.value?.length && <div className="rows">{data.value.map(notice => <div className="notice" key={notice.id}>
        <button className="row-button" aria-expanded={expanded === notice.id}
          onClick={() => setExpanded(expanded === notice.id ? null : notice.id)}>
          <span><strong>{noticeTitles[notice.kind]}</strong><small>{notice.recipient}</small></span>
          <Chip tone={notice.status === 'DRAFT' ? 'amber' : 'green'}>{notice.status}</Chip>
        </button>
        {expanded === notice.id && <div className="notice-detail">
          <pre className="document-text">{notice.body}</pre>
          {canReview && notice.status === 'DRAFT' && notice.created_by !== session.officer.id &&
            <button className="primary" disabled={task.pending} onClick={() => review(notice, 'approve')}>Approve draft</button>}
          {canReview && notice.status === 'APPROVED' &&
            <button className="primary" disabled={task.pending} onClick={() => review(notice, 'send')}>Record simulated send</button>}
          {canReview && notice.status === 'DRAFT' && notice.created_by === session.officer.id &&
            <p className="muted">A different supervisor must approve this draft.</p>}
        </div>}
      </div>)}</div>}
    </Panel>
  </div>
}

function FlowView({ trail }: { trail: Trail }) {
  const rows = new Map<number, number>()
  const positions = new Map(trail.nodes.map(node => {
    const row = rows.get(node.tier) ?? 0
    rows.set(node.tier, row + 1)
    return [node.id, { x: 28 + node.tier * 203, y: 46 + row * 86 }]
  }))
  const width = Math.max(400, 90 + rows.size * 203)
  const height = Math.max(180, 97 + Math.max(...rows.values()) * 86)
  return <div className="flow-wrap" tabIndex={0} aria-label="Scrollable transaction diagram">
    <svg role="img" aria-label="Directed graph of synthetic account transfers" viewBox={`0 0 ${width} ${height}`}
      width={width} height={height}>
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#8295a3" />
      </marker></defs>
      {trail.edges.map(edge => {
        const a = positions.get(edge.source)!
        const b = positions.get(edge.target)!
        const forward = a.x < b.x
        const start = a.x + (forward ? 124 : 0)
        const finish = b.x + (forward ? 0 : 124)
        const bend = forward ? (start + finish) / 2 : Math.min(start, finish) - 26
        const line = `M${start} ${a.y + 26} C${bend} ${a.y + 26} ${bend} ${b.y + 26} ${finish} ${b.y + 26}`
        return <path key={`${edge.source}:${edge.target}`} d={line} fill="none" stroke="#8295a3" strokeWidth="1.5" markerEnd="url(#arrow)">
          <title>{edge.source} to {edge.target}: {inr(edge.amount)}</title>
        </path>
      })}
      {trail.nodes.map(node => {
        const point = positions.get(node.id)!
        return <g key={node.id} transform={`translate(${point.x}, ${point.y})`}>
          <title>{node.id}</title>
          <rect width="124" height="52" rx="9" fill={node.freeze_priority ? '#fcf1db' : '#ffffff'}
            stroke={node.freeze_priority ? '#cf9342' : '#cad8db'} />
          <text x="10" y="22" className="flow-id">{node.id.length > 15 ? node.id.slice(0, 13) + '…' : node.id}</text>
          <text x="10" y="39" className="flow-label">{node.freeze_priority ? 'Review balance' : 'Account'}</text>
        </g>
      })}
    </svg>
  </div>
}

function MoneyTrail({ path, token, canEdit }: CaseProps) {
  const data = useLoad<Trail>(path + '/graph', token)
  const task = useTask()
  function importCsv(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    const file = formValues(event).get('statement')
    if (!(file instanceof File)) return
    void task.run(async () => {
      if (file.size > 150_000) throw new Error('CSV files are limited to 150 KB.')
      const report = await api<{ added: number; repeated: number }>(path + '/transactions/import', token,
        json('POST', { csv: await file.text() }))
      task.setNote(`Imported ${report.added} transfers. ${report.repeated} already present.`)
      data.refresh()
      form.reset()
    })
  }
  return <div className="stack">
    <Panel title="Money trail" hint={data.value ? `${data.value.nodes.length} accounts · ${data.value.edges.length} transfer routes` : undefined}>
      {canEdit && <form className="inline-form" onSubmit={importCsv}>
        <label>Bank statement CSV<input name="statement" type="file" accept=".csv" required /></label>
        <button className="primary" disabled={task.pending}>Import transfers</button>
      </form>}
      <ErrorLine message={data.error || task.error} />
      {task.note && <p className="feedback" role="status">{task.note}</p>}
      {data.value?.nodes.length ? <FlowView trail={data.value} />
        : <Empty>{data.value ? 'Import a synthetic bank statement to trace transfers.' : 'Loading money trail…'}</Empty>}
    </Panel>
    {!!data.value?.nodes.length && <Panel title="Accounts for review" hint="Terminal accounts with a positive recorded balance.">
      {data.value.priorities.length ? <div className="rows">{data.value.priorities.map(node =>
        <div className="static-row" key={node.id}><code>{node.id}</code><strong>{inr(node.balance_remaining!)}</strong></div>)}</div>
        : <Empty>No terminal account has a positive recorded balance.</Empty>}
    </Panel>}
    {!!data.value?.edges.length && <Panel title="Transfer routes">
      <div className="table-scroll"><table><thead><tr><th>From</th><th>To</th><th>Transfers</th><th>Amount</th></tr></thead>
        <tbody>{data.value.edges.map(edge => <tr key={`${edge.source}:${edge.target}`}>
          <td className="mono">{edge.source}</td><td className="mono">{edge.target}</td>
          <td>{edge.transfers}</td><td>{inr(edge.amount)}</td>
        </tr>)}</tbody>
      </table></div>
    </Panel>}
  </div>
}

const reminderTitles: Record<string, string> = {
  victim_progress: 'Victim progress update', custody_review: 'Custody limit review', report_target: 'Police report target',
}

function Deadlines({ path, token, canEdit }: CaseProps) {
  const data = useLoad<Reminder[]>(path, token)
  const task = useTask()
  function calculate(event: FormEvent<HTMLFormElement>) {
    const values = formValues(event)
    void task.run(async () => {
      data.setValue(await api<Reminder[]>(path, token, json('POST', {
        custody_on: field(values, 'custody_on') || null,
        custody_band: field(values, 'custody_band') || null,
        supervisor_report_due: field(values, 'supervisor_report_due') || null,
      })))
      task.setNote('Reminders updated.')
    })
  }
  return <div className="stack">
    {canEdit && <Panel title="Set reminders" hint="Enter dates confirmed for the training scenario.">
      <form className="form-grid" onSubmit={calculate}>
        <label>Custody date <small>Optional</small><input type="date" name="custody_on" max={today()} /></label>
        <label>Reviewed offence band<select name="custody_band"><option value="">Select if applicable</option>
          <option value="other_offence">Other offence · 60 days</option>
          <option value="death_life_or_ten_years_or_more">Death, life or 10+ years · 90 days</option>
        </select></label>
        <label>Officer-set report target <small>Optional</small><input type="date" name="supervisor_report_due" /></label>
        <div className="form-submit"><button className="primary" disabled={task.pending}>Calculate reminders</button></div>
      </form>
    </Panel>}
    <Panel title="Deadline tracker">
      <ErrorLine message={data.error || task.error} />
      {task.note && <p className="feedback" role="status">{task.note}</p>}
      {!data.value?.length && <Empty>{data.value ? 'No reminders calculated.' : 'Loading deadlines…'}</Empty>}
      {!!data.value?.length && <div className="steps">{data.value.map(row => <div key={row.id}>
        <div className="step-title"><strong>{reminderTitles[row.kind] || row.kind}</strong>
          <Chip tone={row.completed ? 'green' : row.due_date <= today() ? 'amber' : 'slate'}>
            {row.completed ? 'Done' : row.due_date < today() ? 'Overdue' : row.due_date === today() ? 'Due today' : 'Upcoming'}
          </Chip>
        </div>
        <p>{row.note}</p>
        <div className="step-meta"><span>{row.basis}</span><span>Due {shortDate(row.due_date)}</span>
          {canEdit && <button className="table-link" disabled={task.pending} onClick={() => void task.run(async () => {
            const updated = await api<Reminder>(`${path}/${row.id}`, token, json('PATCH', { completed: !row.completed }))
            data.setValue(data.value!.map(item => item.id === updated.id ? updated : item))
          })}>{row.completed ? 'Reopen' : 'Mark done'}</button>}
        </div>
      </div>)}</div>}
    </Panel>
  </div>
}

function Audit({ path, token }: Pick<CaseProps, 'path' | 'token'>) {
  const data = useLoad<AuditEvent[]>(path, token)
  return <Panel title="Case activity" hint="Recorded write actions and officer approvals.">
    <ErrorLine message={data.error} />
    {!data.value?.length && <Empty>{data.value ? 'No audited activity for this case.' : 'Loading activity…'}</Empty>}
    {!!data.value?.length && <div className="table-scroll"><table>
      <thead><tr><th>Action</th><th>Record</th><th>Officer ID</th><th>Date</th></tr></thead>
      <tbody>{data.value.map(row => <tr key={row.id}><td className="mono">{row.action}</td>
        <td>{row.entity}</td><td>{row.user_id || '—'}</td><td>{shortDate(row.timestamp)}</td></tr>)}</tbody>
    </table></div>}
  </Panel>
}

export function LawLibrary({ token }: { token: string }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const task = useTask()
  function ask(value: string) {
    setQuestion(value)
    setAnswer(null)
    void task.run(async () => setAnswer(await api<Answer>('/law/ask', token, json('POST', { question: value }))))
  }
  const examples = ['When is a victim progress update due?', 'Which section covers bank records?', 'What is required for an electronic record certificate?']
  return <>
    <header className="pagehead"><div><span className="eyebrow">LEGAL REFERENCE</span><h1>Legal library</h1>
      <p>Find relevant sections in the curated fraud corpus and open the official source.</p></div></header>
    <Panel title="Ask a legal question">
      <form className="inline-form" onSubmit={e => { e.preventDefault(); ask(question) }}>
        <label className="grow">Question<input value={question} onChange={e => setQuestion(e.target.value)}
          placeholder="Which section covers production of bank records?" minLength={3} maxLength={700} required /></label>
        <button className="primary" disabled={task.pending}>{task.pending ? 'Searching…' : 'Search sections'}</button>
      </form>
      <div className="examples">{examples.map(item => <button className="secondary" key={item} disabled={task.pending}
        onClick={() => ask(item)}>{item}</button>)}</div>
      <ErrorLine message={task.error} />
    </Panel>
    {answer && <Panel title={answer.status === 'grounded' ? 'Matching sections' : 'No reliable match'}>
      {answer.citations.length ? <div className="steps">{answer.citations.map(entry =>
        <article key={`${entry.act}:${entry.section}`}>
          <CitationLink item={entry} /><h3>{entry.title}</h3><p>{entry.summary}</p>
        </article>)}</div> : <Empty>{answer.answer}</Empty>}
    </Panel>}
  </>
}

const tabs = [
  ['evidence', 'Evidence'], ['plan', 'Investigation plan'], ['notices', 'Notices'],
  ['graph', 'Money trail'], ['deadlines', 'Deadlines'], ['audit', 'Activity'],
] as const

export function CaseWorkspace({ item, session, onBack }: { item: Case; session: Session; onBack: () => void }) {
  const [active, setActive] = useState<typeof tabs[number][0]>('evidence')
  const token = session.access_token
  const canEdit = session.officer.role === 'IO' || session.officer.role === 'SHO'
  const root = `/cases/${item.id}`
  const props = { token, canEdit, path: root + '/' + active }
  return <>
    <button className="back table-link" onClick={onBack}>← Case register</button>
    <header className="case-header">
      <div className="case-ref"><span className="mono">{item.reference}</span><Chip tone="green">Training case</Chip></div>
      <h1>{item.title}</h1><p>{item.summary}</p>
      <div className="case-meta"><span>Opened <strong>{shortDate(item.opened_on)}</strong></span>
        <span>Unit <strong>{item.station}</strong></span></div>
    </header>
    <nav className="tabs" aria-label="Case sections">
      {tabs.filter(([id]) => id !== 'audit' || session.officer.role !== 'IO').map(([id, title]) =>
        <button key={id} aria-current={active === id ? 'page' : undefined} onClick={() => setActive(id)}>{title}</button>)}
    </nav>
    {active === 'evidence' && <Evidence {...props} />}
    {active === 'plan' && <InvestigationPlan {...props} />}
    {active === 'notices' && <Notices {...props} session={session} />}
    {active === 'graph' && <MoneyTrail {...props} path={root} />}
    {active === 'deadlines' && <Deadlines {...props} />}
    {active === 'audit' && <Audit {...props} />}
  </>
}
