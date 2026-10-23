import { useState } from 'react'
import { deleteDocument } from '../api'
import type { DocumentInfo } from '../types'
import type { Upload } from '../useUploads'
import { DropZone } from './DropZone'
import { UploadList } from './UploadList'

interface Props {
  documents: DocumentInfo[]
  onChanged: () => void
  uploads: Upload[]
  onFiles: (files: File[]) => void
  onDismissUpload: (id: number) => void
}

export function DocumentPanel({ documents, onChanged, uploads, onFiles, onDismissUpload }: Props) {
  const [error, setError] = useState<string | null>(null)

  async function handleDelete(document: DocumentInfo) {
    if (!window.confirm(`Remove ${document.filename}?`)) return
    setError(null)
    try {
      await deleteDocument(document.id)
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  return (
    <aside className="library">
      <h2 className="library__title">Your documents</h2>

      <DropZone onFiles={onFiles} size="compact" />
      <UploadList uploads={uploads} onDismiss={onDismissUpload} />

      {error && (
        <p className="library__error" role="alert">
          {error}
        </p>
      )}

      {documents.length === 0 ? (
        <p className="library__empty">No documents yet.</p>
      ) : (
        <ul className="doc-list">
          {documents.map((document) => (
            <li key={document.id} className={`doc doc--${document.status}`}>
              <div className="doc__main">
                <span className="doc__name" title={document.filename}>
                  {document.filename}
                </span>
                <span className="doc__meta">
                  {document.status === 'ready' &&
                    `${document.page_count} ${document.page_count === 1 ? 'page' : 'pages'}, ${document.chunk_count} passages`}
                  {document.status === 'processing' && 'Processing…'}
                  {document.status === 'failed' && (document.error ?? 'Could not be read')}
                </span>
              </div>
              <button
                type="button"
                className="doc__remove"
                onClick={() => handleDelete(document)}
                aria-label={`Remove ${document.filename}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
