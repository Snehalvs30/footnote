import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { streamAnswer } from '../api'
import { stripMarkdown } from '../text'
import type { Source } from '../types'
import { AnswerText } from './AnswerText'

interface Turn {
  id: number
  question: string
  answer: string
  sources: Source[]
  status: 'streaming' | 'done' | 'error'
  error?: string
}

interface Props {
  canAsk: boolean
}

const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function ChatPanel({ canAsk }: Props) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [question, setQuestion] = useState('')
  const [highlighted, setHighlighted] = useState<string | null>(null)
  const nextId = useRef(1)

  const busy = turns.some((turn) => turn.status === 'streaming')

  // Updates one turn by id. Functional setState, because tokens arrive faster than renders.
  function update(id: number, change: (turn: Turn) => Partial<Turn>) {
    setTurns((all) => all.map((turn) => (turn.id === id ? { ...turn, ...change(turn) } : turn)))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (!text || busy) return

    const id = nextId.current++
    setTurns((all) => [...all, { id, question: text, answer: '', sources: [], status: 'streaming' }])
    setQuestion('')

    try {
      await streamAnswer(text, {
        onSources: (sources) => update(id, () => ({ sources })),
        onToken: (token) => update(id, (turn) => ({ answer: turn.answer + token })),
        onDone: () => update(id, () => ({ status: 'done' })),
        onError: (message) => update(id, () => ({ status: 'error', error: message })),
      })
    } catch {
      update(id, () => ({ status: 'error', error: 'Lost connection to the server. Is the API running?' }))
    }
  }

  function showSource(turnId: number, number: number) {
    const key = `${turnId}-${number}`
    setHighlighted(key)
    document.getElementById(`source-${key}`)?.scrollIntoView({
      block: 'nearest',
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    })
  }

  return (
    <main className="reading">
      <div className="conversation" aria-live="polite">
        {turns.length === 0 && (
          <div className="welcome">
            <h1 className="welcome__title">Footnote</h1>
            <p className="welcome__lead">
              Ask a question about your documents. Every answer cites the passages it came from, so you
              can check it.
            </p>
          </div>
        )}

        {turns.map((turn) => (
          <article key={turn.id} className="turn">
            <h2 className="turn__question">{turn.question}</h2>

            {turn.answer ? (
              <AnswerText
                text={turn.answer}
                sourceCount={turn.sources.length}
                onCite={(number) => showSource(turn.id, number)}
              />
            ) : (
              turn.status === 'streaming' && <p className="turn__pending">Reading your documents…</p>
            )}

            {turn.status === 'error' && (
              <p className="turn__error" role="alert">
                {turn.error}
              </p>
            )}

            {turn.sources.length > 0 && (
              <ol className="footnotes">
                {turn.sources.map((source) => {
                  const key = `${turn.id}-${source.number}`
                  return (
                    <li
                      key={key}
                      id={`source-${key}`}
                      value={source.number}
                      className={`footnote ${highlighted === key ? 'footnote--highlighted' : ''}`}
                    >
                      <span className="footnote__where">
                        {source.filename}, page {source.page_number}
                      </span>
                      <span className="footnote__excerpt">{stripMarkdown(source.excerpt)}…</span>
                    </li>
                  )
                })}
              </ol>
            )}
          </article>
        ))}
      </div>

      <form className="ask" onSubmit={handleSubmit}>
        <label htmlFor="question" className="visually-hidden">
          Your question
        </label>
        <input
          id="question"
          className="ask__input"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={canAsk ? 'Ask about your documents' : 'Add a document first'}
          disabled={!canAsk}
          maxLength={1000}
          autoComplete="off"
        />
        <button type="submit" className="ask__button" disabled={!canAsk || busy || !question.trim()}>
          {busy ? 'Answering…' : 'Ask'}
        </button>
      </form>
    </main>
  )
}
