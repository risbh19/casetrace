import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { ApiError } from './api'
import type { Citation } from './api'

export function shortDate(value: string) {
  const date = new Date(value.length === 10 ? value + 'T00:00:00+05:30' : value)
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata',
  }).format(date)
}

export function inr(value: string) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value))
}

export function today() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date())
}

export function errorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 401) return 'Your session has expired. Sign out, then sign in again.'
  return error instanceof Error ? error.message : 'Something went wrong'
}

export function Panel({ title, hint, action, children }: {
  title: string; hint?: string; action?: ReactNode; children: ReactNode
}) {
  return <section className="panel">
    <div className="panel-head"><div><h2>{title}</h2>{hint && <p>{hint}</p>}</div>{action}</div>
    {children}
  </section>
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>
}

export function ErrorLine({ message }: { message: string }) {
  return message ? <p className="error" role="alert">{message}</p> : null
}

export function CitationLink({ item }: { item: Citation }) {
  const source = item.source_page ? item.source_url + '#page=' + item.source_page : item.source_url
  return <a className="citation" href={source} target="_blank" rel="noreferrer">
    {item.act} § {item.section} <span aria-hidden="true">↗</span>
  </a>
}

export function useTask() {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [note, setNote] = useState('')
  async function run(task: () => Promise<void>) {
    setPending(true)
    setError('')
    setNote('')
    try { await task() } catch (reason) { setError(errorMessage(reason)) }
    finally { setPending(false) }
  }
  return { pending, error, note, setNote, run }
}

export function formValues(event: FormEvent<HTMLFormElement>) {
  event.preventDefault()
  return new FormData(event.currentTarget)
}

export function field(data: FormData, key: string) {
  return String(data.get(key) || '')
}

export function Chip({ tone = 'slate', children }: { tone?: 'slate' | 'green' | 'amber'; children: ReactNode }) {
  return <span className={`chip chip-${tone}`}>{children}</span>
}
