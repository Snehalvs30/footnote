import { useEffect, useId, useRef, useState } from 'react'

interface Props {
  email: string
  onSignOut: () => void
}

/** "snehal.shinde@x.com" -> "SS"; "snehalshinde3028@x.com" -> "SN". */
function initials(email: string): string {
  const name = email.split('@')[0]
  const parts = name.split(/[._+\-\d]+/).filter(Boolean)
  const letters = parts.length >= 2 ? parts[0][0] + parts[1][0] : (parts[0] ?? '').slice(0, 2)
  return (letters || '?').toUpperCase()
}

/**
 * The account button in the top bar: your initials, which open a small panel
 * with your email and "Sign out".
 *
 * Behaves like menus people already know: closes on Escape (returning focus to
 * the button), on a click anywhere outside, and after signing out. Built as a
 * disclosure (a button that shows and hides a panel), which screen readers
 * announce as "expanded" or "collapsed".
 */
export function AccountMenu({ email, onSignOut }: Props) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const signOutRef = useRef<HTMLButtonElement>(null)
  const panelId = useId()

  // While open: move focus into the panel, and listen for Escape and outside clicks.
  // The listeners only exist while the panel is open, and are removed when it closes.
  useEffect(() => {
    if (!open) return
    signOutRef.current?.focus()

    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  return (
    <div className="account-menu" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="account-button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((isOpen) => !isOpen)}
      >
        <span className="avatar" aria-hidden="true">
          {initials(email)}
        </span>
        <span className="visually-hidden">Account: {email}</span>
        <span className="account-button__chevron" aria-hidden="true" />
      </button>

      {open && (
        <div id={panelId} className="account-panel">
          <p className="account-panel__label">Signed in as</p>
          <p className="account-panel__email" title={email}>
            {email}
          </p>
          <button
            ref={signOutRef}
            type="button"
            className="account-panel__item"
            onClick={() => {
              setOpen(false)
              onSignOut()
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}
