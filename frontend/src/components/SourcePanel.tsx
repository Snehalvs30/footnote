import { stripMarkdown } from '../text'
import type { Source } from '../types'

interface Props {
  /** The sources of the answer whose footnote was clicked (empty if none). */
  sources: Source[]
  selected: number | null
  onSelect: (sourceNumber: number) => void
  onClose: () => void
}

/**
 * The right-hand pane: the full passage behind a footnote. Tabs switch between
 * the sources of the same answer. On phones it slides up from the bottom.
 */
export function SourcePanel({ sources, selected, onSelect, onClose }: Props) {
  const source = sources.find((candidate) => candidate.number === selected)

  return (
    <aside className={`source-panel ${source ? 'source-panel--open' : ''}`} aria-label="Source">
      {!source ? (
        <div className="source-panel__empty">
          <p className="source-panel__empty-mark" aria-hidden="true">
            ¹
          </p>
          <p>Click a footnote in an answer to see the passage it came from.</p>
        </div>
      ) : (
        <>
          <div className="source-panel__header">
            <div>
              <p className="source-panel__eyebrow">Source {source.number}</p>
              <p className="source-panel__where" title={source.filename}>
                {source.filename} · page {source.page_number}
              </p>
            </div>
            <button type="button" className="source-panel__close" onClick={onClose} aria-label="Close source">
              ×
            </button>
          </div>

          {sources.length > 1 && (
            <nav className="source-tabs" aria-label="Sources for this answer">
              {sources.map((candidate) => (
                <button
                  key={candidate.number}
                  type="button"
                  className="source-tab"
                  aria-current={candidate.number === source.number ? 'true' : undefined}
                  onClick={() => onSelect(candidate.number)}
                >
                  {candidate.number}
                </button>
              ))}
            </nav>
          )}

          <article className="source-panel__page">
            {/* key: a new source remounts the passage, which replays the highlighter sweep */}
            <p key={`${source.document_id}-${source.chunk_index}`} className="source-panel__text">
              <mark className="highlight">{stripMarkdown(source.content)}</mark>
            </p>
          </article>
        </>
      )}
    </aside>
  )
}
