import { LoginScreen } from '@/auth/LoginScreen'
import { useSession } from '@/auth/useSession'
import { ChatShell } from '@/chat/ChatShell'

export default function App() {
  const { session, signedIn, signedOut } = useSession()
  if (session.status === 'checking') return null
  if (session.status === 'signedOut') return <LoginScreen onSignedIn={signedIn} />
  return <ChatShell onSignedOut={signedOut} />
}
