export type Role = 'IO' | 'SHO' | 'CO' | 'SP'
export type Officer = { id: number; username: string; name: string; role: Role; station: string }
export type Session = { access_token: string; officer: Officer }
export type Case = {
  id: number; reference: string; title: string; summary: string
  station: string; case_type: string; opened_on: string; assigned_to: number
}
export type Document = {
  id: number; filename: string; media_type: string; sha256: string; size: number
  extraction_method: string; created_at: string
}
export type DocumentDetail = Document & { text: string; entities: { kind: string; value: string; method: string }[] }
export type Citation = {
  act: string; section: string; summary: string; title: string; source_url: string; source_page: number | null
}
export type Answer = { status: 'grounded' | 'unsure'; answer: string; citations: Citation[] }
export type PlanStep = {
  id: number; title: string; instructions: string; due_date: string; status: 'OPEN' | 'DONE'
  legal_basis: Citation | 'unsure'
}
export type Notice = {
  id: number; kind: string; recipient: string; body: string; created_by: number
  status: 'DRAFT' | 'APPROVED' | 'SENT'; approved_by: number | null
}
export type Account = { id: string; balance_remaining: string | null; tier: number; freeze_priority: boolean }
export type Transfer = { source: string; target: string; amount: string; transfers: number }
export type Trail = { nodes: Account[]; edges: Transfer[]; priorities: Account[] }
export type Reminder = {
  id: number; kind: string; anchor_date: string; due_date: string; basis: string; note: string; completed: boolean
}
export type AuditEvent = { id: number; user_id: number | null; action: string; entity: string; timestamp: string }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

type ErrorResponse = { detail?: string | { field: string; message: string }[] }

async function response(path: string, token?: string, init?: RequestInit) {
  const headers = new Headers(init?.headers)
  if (token) headers.set('Authorization', 'Bearer ' + token)
  const result = await fetch('/api' + path, { ...init, headers, cache: 'no-store' })
  if (result.ok) return result
  const data = await result.json().catch(() => ({})) as ErrorResponse
  const detail = data.detail
  const message = typeof detail === 'string' ? detail : detail?.map(e => e.message).join('. ')
  throw new ApiError(result.status, message || `Request failed (${result.status})`)
}

export async function api<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  return (await response(path, token, init)).json() as Promise<T>
}

export function json(method: 'POST' | 'PATCH', value: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }
}

export async function saveOriginal(path: string, token: string, filename: string) {
  const blob = await (await response(path, token)).blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
