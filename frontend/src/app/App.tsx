import { useApp } from '@/app/useApp'
import { LoginScreen } from '@/client/auth/useCases/login/LoginScreen'
import { ChatShell } from '@/client/chat/useCases/chatShell/ChatShell'

export default function App() {
  const app = useApp()
  if (app.state === 'checking') return null
  if (app.state === 'signedOut') return <LoginScreen expired={app.expired} onSignedIn={app.signedIn} />
  return (
    <ChatShell warm={app.warm} fromLogin={app.fromLogin} customerId={app.customerId} onSignedOut={app.signedOut} />
  )
}
