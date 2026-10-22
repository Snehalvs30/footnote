import type { DocumentInfo, Source } from './types'

const BASE = '/api'

/** FastAPI errors look like {"detail": "..."}; fall back to the status code. */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // not JSON
  }
  return `Request failed (${response.status})`
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const response = await fetch(`${BASE}/documents`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${BASE}/documents`, { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`${BASE}/documents/${id}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(await errorMessage(response))
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