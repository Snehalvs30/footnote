import type { DocumentInfo, Source, User } from './types'

const BASE = '/api'

/** Thrown when the session is missing or expired, so the app can show the sign-in screen. */
export class UnauthorizedError extends Error {}

/** Throws UnauthorizedError for 401, or an Error with the API's message for other failures. */
async function check(response: Response): Promise<Response> {
  if (response.status === 401) throw new UnauthorizedError(await errorMessage(response))
  if (!response.ok) throw new Error(await errorMessage(response))
  return response
}

/**
 * FastAPI errors look like {"detail": "..."}. Validation errors (422) carry a list
 * of problems instead; show the first one. Fall back to the status code.
 */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      const field = body.detail[0].loc?.at(-1)
      return field ? `${field}: ${body.detail[0].msg}` : body.detail[0].msg
    }
  } catch {
    // not JSON
  }
  return `Request failed (${response.status})`
}

// ---- Accounts ----
// The session lives in an HttpOnly cookie that the browser sends automatically,
// so these functions never see or store a token.

/** The signed-in user, or null if there's no valid session. */
export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch(`${BASE}/auth/me`)
  if (response.status === 401) return null
  return (await check(response)).json()
}

export async function signIn(email: string, password: string): Promise<User> {
  const response = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  // A wrong password is a 401 too, but here it should show as a form error.
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export async function createAccount(email: string, password: string): Promise<User> {
  const response = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export async function signOut(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, { method: 'POST' })
}

// ---- Documents ----

export async function listDocuments(): Promise<DocumentInfo[]> {
  return (await check(await fetch(`${BASE}/documents`))).json()
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData()
  form.append('file', file)
  return (await check(await fetch(`${BASE}/documents`, { method: 'POST', body: form }))).json()
}

export async function deleteDocument(id: string): Promise<void> {
  await check(await fetch(`${BASE}/documents/${id}`, { method: 'DELETE' }))
}

export interface AnswerHandlers {
  onSources: (sources: Source[]) => void
  onToken: (text: string) => void
  onDone: () => void
  onError: (message: string) => void
}

/**
 * Streams an answer from POST /ask.
 *
 * The browser's EventSource only supports GET, so we read the response body
 * ourselves and split it into events. Each event ends with a blank line:
 *   event: token
 *   data: {"text": "Hello"}
 */
export async function streamAnswer(
  question: string,
  handlers: AnswerHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal,
  })
  if (!response.ok || !response.body) {
    handlers.onError(await errorMessage(response))
    return
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    // A network chunk can hold several events, or half of one: keep the remainder.
    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      dispatchEvent(buffer.slice(0, boundary), handlers)
      buffer = buffer.slice(boundary + 2)
      boundary = buffer.indexOf('\n\n')
    }
  }
}

function dispatchEvent(raw: string, handlers: AnswerHandlers): void {
  let event = 'message'
  let data = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice('event: '.length)
    else if (line.startsWith('data: ')) data += line.slice('data: '.length)
  }
  const payload = data ? JSON.parse(data) : {}

  switch (event) {
    case 'sources':
      handlers.onSources(payload as Source[])
      break
    case 'token':
      handlers.onToken(payload.text as string)
      break
    case 'done':
      handlers.onDone()
      break
    case 'error':
      handlers.onError(payload.message as string)
      break
  }
}