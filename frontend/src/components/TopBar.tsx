import { AccountMenu } from './AccountMenu'

interface Props {
  email: string
  onSignOut: () => void
}

export function TopBar({ email, onSignOut }: Props) {
  return (
    <header className="topbar">
      <p className="topbar__wordmark">Footnote</p>
      <AccountMenu email={email} onSignOut={onSignOut} />
    </header>
  )
}
