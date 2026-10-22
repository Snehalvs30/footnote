import { useState } from 'react'
import type { FormEvent } from 'react'
import { createAccount, signIn } from '../api'
import type { User } from '../types'

interface Props {
  onSignedIn: (user: User) => void
}

export function AuthScreen({ onSignedIn }: Props) {
  const [mode, setMode] = useState<'sign-in' | 'create'>('sign-in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const creating = mode === 'create'

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = creating ? await createAccount(email, password) : await signIn(email, password)
      onSignedIn(user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  function switchMode() {
    setMode(creating ? 'sign-in' : 'create')
    setError(null)
  }

  return (
    <main className="auth">
      <h1 className="welcome__title">Footnote</h1>
      <p className="auth__lead">
        {creating
          ? 'Create an account to keep your documents private to you.'
          : 'Sign in to ask questions about your documents.'}
      </p>

      <form className="auth__form" onSubmit={handleSubmit}>
        <label className="auth__field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </label>

        <label className="auth__field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={creating ? 'new-password' : 'current-password'}
            minLength={8}
            required
          />
          {creating && <span className="auth__hint">At least 8 characters</span>}
        </label>

        {error && (
          <p className="auth__error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="ask__button auth__submit" disabled={busy}>
          {busy ? 'One moment…' : creating ? 'Create account' : 'Sign in'}
        </button>
      </form>

      <p className="auth__switch">
        {creating ? 'Already have an account?' : 'New to Footnote?'}{' '}
        <button type="button" className="link-button" onClick={switchMode}>
          {creating ? 'Sign in' : 'Create an account'}
        </button>
      </p>
    </main>
  )
}
