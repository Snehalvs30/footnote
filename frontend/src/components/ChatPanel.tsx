import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { streamAnswer } from '../api'
import type { Source } from '../types'
import { AnswerText } from './AnswerText'
import { DropZone } from './DropZone'
import { SourcePanel } from './SourcePanel'

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
  hasDocuments: boolean
  onFiles: (files: File[]) => void
  onAddSamples: () => void
  addingSamples: boolean
  samplesError: string | null
}

/** The conversation (middle pane) and the source panel (right pane). */
export function ChatPanel({ canAsk, hasDocuments, onFiles, onAddSamples, addingSamples, samplesError }: Props) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [question, setQuestion] = useState('')
  // Which footnote is open in the source panel: the answer it belongs to, and its number.
  const [selected, setSelected] = useState<{ turnId: number; number: number } | null>(null)
  const nextId = useRef(1)
  const endRef = useRef<HTMLDivElement>(null)

  const busy = turns.some((turn) => turn.status === 'streaming')
  const selectedTurn = turns.find((turn) => turn.id === selected?.turnId)

  // Keep the newest question in view when one is asked.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [turns.length])

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

  return (
    <>
      <main className="reading">
        <div className="conversation" aria-live="polite">
          {turns.length === 0 && (
            <div className="welcome">
              <h1 className="welcome__title">Footnote</h1>
              <p className="welcome__lead">
                Every answer cites the passage it came from, so you can check it.
              </p>
              {!hasDocuments && (
                <div className="welcome__start">
                  <DropZone onFiles={onFiles} size="large" />
                  <button type="button" className="button-secondary" onClick={onAddSamples} disabled={addingSamples}>
                    {addingSamples ? 'Adding sample documents…' : 'Try with sample documents'}
                  </button>
                  {samplesError && (
                    <p className="welcome__error" role="alert">
                      {samplesError}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {turns.map((turn) => (
            <article key={turn.id} className="turn">
              <h2 className="turn__question">{turn.question}</h2>

              {turn.answer ? (
                <AnswerText
                  text={turn.answer}
                  sourceCount={turn.sources.length}
                  activeNumber={selected?.turnId === turn.id ? selected.number : null}
                  onCite={(number) => setSelected({ turnId: turn.id, number })}
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
                <ol className="source-chips" aria-label="Sources">
                  {turn.sources.map((source) => {
                    const active = selected?.turnId === turn.id && selected.number === source.number
                    return (
                      <li key={source.number}>
                        <button
                          type="button"
                          className="source-chip"
                          aria-pressed={active}
                          onClick={() => setSelected({ turnId: turn.id, number: source.number })}
                        >
                          <span className="source-chip__number">{source.number}</span>
                          <span className="source-chip__label">
                            {source.filename} · p. {source.page_number}
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ol>
              )}
            </article>
          ))}
          <div ref={endRef} />
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

      <SourcePanel
        sources={selectedTurn?.sources ?? []}
        selected={selected?.number ?? null}
        onSelect={(number) => selected && setSelected({ turnId: selected.turnId, number })}
        onClose={() => setSelected(null)}
      />
    </>
  )
}
