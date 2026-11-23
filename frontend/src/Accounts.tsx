import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, json } from './api'
import type { Officer, Session } from './api'
import { ErrorLine, Panel, field, formValues, useTask } from './ui'

export function PasswordPage({ session, onSave }: { session: Session; onSave: (session: Session) => void }) {
  const task = useTask()
  function change(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    const values = formValues(event)
    void task.run(async () => {
      if (field(values, 'new') !== field(values, 'confirm')) throw new Error('New passwords must match.')
      const result = await api<Session>('/auth/password', session.access_token, json('POST', {
        current_password: field(values, 'current'), new_password: field(values, 'new'),
      }))
      onSave(result)
      form.reset()
      task.setNote('Password changed. Your other sessions have been signed out.')
    })
  }
  return <Panel title="Account security" hint={session.officer.must_change_password ? 'Change your temporary password before opening case records.' : 'Changing your password signs out your other sessions.'}>
    <form className="form-grid" onSubmit={change}>
      <label className="full">Current password<input name="current" type="password" autoComplete="current-password" maxLength={128} required /></label>
      <label>New password<input name="new" type="password" autoComplete="new-password" minLength={14} maxLength={128} required /></label>
      <label>Confirm new password<input name="confirm" type="password" autoComplete="new-password" minLength={14} maxLength={128} required /></label>
      <button className="primary" disabled={task.pending}>Change password</button>
      <ErrorLine message={task.error} />
      {task.note && <p role="status">{task.note}</p>}
    </form>
  </Panel>
}

export function OfficerAccounts({ session }: { session: Session }) {
  const [officers, setOfficers] = useState<Officer[]>([])
  const [loadError, setLoadError] = useState('')
  const task = useTask()
  useEffect(() => {
    const abort = new AbortController()
    void api<Officer[]>('/officers', session.access_token, { signal: abort.signal }).then(setOfficers)
      .catch(() => { if (!abort.signal.aborted) setLoadError('Unable to load officer accounts.') })
    return () => abort.abort()
  }, [session.access_token])
  function create(event: FormEvent<HTMLFormElement>) {
    const form = event.currentTarget
    const values = formValues(event)
    void task.run(async () => {
      const officer = await api<Officer>('/officers', session.access_token, json('POST', {
        username: field(values, 'username'), name: field(values, 'name'), role: field(values, 'role'),
        temporary_password: field(values, 'temporary_password'),
      }))
      setOfficers(current => [...current, officer])
      form.reset()
      task.setNote('Officer created. Share the temporary password through your approved channel.')
    })
  }
  function update(event: FormEvent<HTMLFormElement>, officer: Officer) {
    const values = formValues(event)
    void task.run(async () => {
      const changed = await api<Officer>(`/officers/${officer.id}`, session.access_token, json('PATCH', {
        is_active: field(values, 'active') === 'yes', role: field(values, 'role'),
        temporary_password: field(values, 'password') || null,
      }))
      setOfficers(current => current.map(item => item.id === changed.id ? changed : item))
      task.setNote('Officer updated. Existing sessions have been invalidated.')
    })
  }
  return <div className="stack">
    <Panel title="Add officer" hint={`Accounts are restricted to ${session.officer.station}. New officers must change their temporary password.`}>
      <form className="form-grid" onSubmit={create}>
        <label>Username<input name="username" required pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,39}" /></label>
        <label>Name<input name="name" maxLength={100} required /></label>
        <label>Role<select name="role">{['IO', 'SHO', 'CO', 'SP'].map(role => <option key={role}>{role}</option>)}</select></label>
        <label>Temporary password<input name="temporary_password" type="password" autoComplete="new-password" minLength={14} maxLength={128} required /></label>
        <button className="primary" disabled={task.pending}>Add officer</button>
      </form>
      <ErrorLine message={loadError || task.error} />{task.note && <p role="status">{task.note}</p>}
    </Panel>
    <Panel title="Station officers">
      {officers.map(officer => <article key={officer.id}>
        <h3>{officer.name} · {officer.username}</h3>
        <p>{officer.role} · {officer.is_active ? 'Active' : 'Disabled'}{officer.must_change_password ? ' · Password change required' : ''}</p>
        {!officer.is_admin && <form key={`${officer.is_active}:${officer.role}`} className="form-grid" onSubmit={event => update(event, officer)}>
          <label>Access<select name="active" defaultValue={officer.is_active ? 'yes' : 'no'}><option value="yes">Active</option><option value="no">Disabled</option></select></label>
          <label>Role<select name="role" defaultValue={officer.role}>{['IO', 'SHO', 'CO', 'SP'].map(role => <option key={role}>{role}</option>)}</select></label>
          <label>Reset temporary password <small>Optional</small><input name="password" type="password" autoComplete="new-password" minLength={14} maxLength={128} /></label>
          <button className="secondary" disabled={task.pending}>Save officer changes</button>
        </form>}
      </article>)}
    </Panel>
  </div>
}
