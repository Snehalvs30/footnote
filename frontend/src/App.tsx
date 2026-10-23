import { useCallback, useEffect, useState } from 'react'
import { getCurrentUser, listDocuments, signOut, UnauthorizedError } from './api'
import { AuthScreen } from './components/AuthScreen'
import { ChatPanel } from './components/ChatPanel'
import { DocumentPanel } from './components/DocumentPanel'
import { TopBar } from './components/TopBar'
import type { DocumentInfo, User } from './types'
import { useUploads } from './useUploads'

// undefined = still checking the session; null = signed out.
type SessionState = User | null | undefined

const API_DOWN = "Can't reach the Footnote API. Start it with: uv run fastapi dev app/main.py"

export default function App() {
  const [user, setUser] = useState<SessionState>(undefined)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments())
      setLoadError(null)
    } catch (err) {
      if (err instanceof UnauthorizedError) setUser(null) // session expired
      else setLoadError(API_DOWN)
    }
  }, [])

  // One upload queue, used by both the sidebar and the empty-state drop zone.
  const { uploads, uploadFiles, dismiss, addSamples, addingSamples, samplesError } = useUploads(refresh)

  // On load: is there a valid session cookie? If so, load that user's documents.
  // State is only set inside the promise callbacks (when the API answers), which is
  // what effects are for: syncing with something outside React.
  useEffect(() => {
    getCurrentUser()
      .then(async (current) => {
        setUser(current)
        if (current) await refresh()
      })
      .catch(() => {
        setUser(null)
        setLoadError(API_DOWN)
      })
  }, [refresh])

  // Loading documents is a reaction to an event (signing in), so it happens here,
  // not in an effect that watches `user`.
  function handleSignedIn(signedIn: User) {
    setUser(signedIn)
    void refresh()
  }

  async function handleSignOut() {
    await signOut()
    setDocuments([])
    setUser(null)
  }

  if (user === undefined) return null // brief check on load; avoids a flash of the sign-in screen

  if (user === null) {
    return (
      <>
        {loadError && (
          <p className="banner" role="alert">
            {loadError}
          </p>
        )}
        <AuthScreen onSignedIn={handleSignedIn} />
      </>
    )
  }

  const canAsk = documents.some((document) => document.status === 'ready')

  return (
    <div className="app">
      {loadError && (
        <p className="banner" role="alert">
          {loadError}
        </p>
      )}
      <TopBar email={user.email} onSignOut={handleSignOut} />
      <div className="workspace">
        <DocumentPanel
          documents={documents}
          onChanged={refresh}
          uploads={uploads}
          onFiles={uploadFiles}
          onDismissUpload={dismiss}
        />
        {/* key: a different user gets a fresh, empty conversation */}
        <ChatPanel
          key={user.id}
          canAsk={canAsk}
          hasDocuments={documents.length > 0}
          onFiles={uploadFiles}
          onAddSamples={addSamples}
          addingSamples={addingSamples}
          samplesError={samplesError}
        />
      </div>
    </div>
  )
}
