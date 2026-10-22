import { useCallback, useEffect, useState } from 'react'
import { listDocuments } from './api'
import { ChatPanel } from './components/ChatPanel'
import { DocumentPanel } from './components/DocumentPanel'
import type { DocumentInfo } from './types'

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments())
      setLoadError(null)
    } catch {
      setLoadError("Can't reach the Footnote API. Start it with: uv run fastapi dev app/main.py")
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const canAsk = documents.some((document) => document.status === 'ready')

  return (
    <div className="app">
      {loadError && (
        <p className="banner" role="alert">
          {loadError}
        </p>
      )}
      <DocumentPanel documents={documents} onChanged={refresh} />
      <ChatPanel canAsk={canAsk} />
    </div>
  )
}
