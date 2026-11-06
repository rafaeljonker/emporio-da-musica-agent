import { LoginScreen } from '@/auth/LoginScreen'
import { useSession } from '@/auth/useSession'
import { ChatShell } from '@/chat/ChatShell'

export default function App() {
  const { session, signedIn, signedOut, expired } = useSession()
  if (session.status === 'checking') return null
  if (session.status === 'signedOut') return <LoginScreen expired={session.expired} onSignedIn={signedIn} />
  return (
    <ChatShell
      warm={session.warm}
      fromLogin={session.fromLogin}
      customerId={session.customerId}
      onSignedOut={signedOut}
      onExpired={expired}
    />
  )
}
