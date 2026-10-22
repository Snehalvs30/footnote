import { useCallback, useEffect, useState } from 'react'
import { getCurrentUser, listDocuments, signOut, UnauthorizedError } from './api'
import { AuthScreen } from './components/AuthScreen'
import { ChatPanel } from './components/ChatPanel'
import { DocumentPanel } from './components/DocumentPanel'
import type { DocumentInfo, User } from './types'

// undefined = still checking the session; null = signed out.
type SessionState = User | null | undefined

export default function App() {
  const [user, setUser] = useState<SessionState>(undefined)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  // On load: is there a valid session cookie?
  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => {
        setUser(null)
        setLoadError("Can't reach the Footnote API. Start it with: uv run fastapi dev app/main.py")
      })
  }, [])

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments())
      setLoadError(null)
    } catch (err) {
      if (err instanceof UnauthorizedError) setUser(null) // session expired
      else setLoadError("Can't reach the Footnote API. Start it with: uv run fastapi dev app/main.py")
    }
  }, [])

  useEffect(() => {
    if (user) void refresh()
  }, [user, refresh])

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
        <AuthScreen onSignedIn={setUser} />
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
      <DocumentPanel documents={documents} onChanged={refresh} email={user.email} onSignOut={handleSignOut} />
      {/* key: a different user gets a fresh, empty conversation */}
      <ChatPanel key={user.id} canAsk={canAsk} />
    </div>
  )
}
