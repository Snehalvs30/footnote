import { useState } from 'react'
import type { ChangeEvent } from 'react'
import { deleteDocument, uploadDocument } from '../api'
import type { DocumentInfo } from '../types'

interface Props {
  documents: DocumentInfo[]
  onChanged: () => void
  email: string
  onSignOut: () => void
}

export function DocumentPanel({ documents, onChanged, email, onSignOut }: Props) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = '' // so choosing the same file again still triggers a change
    if (!file) return

    setUploading(true)
    setError(null)
    try {
      const document = await uploadDocument(file)
      if (document.status === 'failed') setError(`${document.filename}: ${document.error}`)
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(document: DocumentInfo) {
    if (!window.confirm(`Remove ${document.filename}?`)) return
    try {
      await deleteDocument(document.id)
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  return (
    <aside className="library">
      <div className="account">
        <span className="account__email">{email}</span>
        <button type="button" className="link-button" onClick={onSignOut}>
          Sign out
        </button>
      </div>

      <h2 className="library__title">Your documents</h2>

      <label className={`upload ${uploading ? 'upload--busy' : ''}`}>
        <input
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleFile}
          disabled={uploading}
          className="visually-hidden"
        />
        {uploading ? 'Reading document…' : 'Add a document'}
      </label>
      <p className="library__hint">PDF, .txt or .md, up to 10 MB</p>

      {error && (
        <p className="library__error" role="alert">
          {error}
        </p>
      )}

      {documents.length === 0 ? (
        <p className="library__empty">Nothing here yet. Add a document to start asking questions.</p>
      ) : (
        <ul className="doc-list">
          {documents.map((document) => (
            <li key={document.id} className={`doc doc--${document.status}`}>
              <div className="doc__main">
                <span className="doc__name">{document.filename}</span>
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
