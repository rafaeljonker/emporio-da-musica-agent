import { LogOut } from 'lucide-react'
import { logout } from '@/api/client'
import avatar from '@/assets/avatar.jpg'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy'
import { Composer } from './Composer'
import { TypingIndicator } from './TypingIndicator'
import { Transcript } from './Transcript'
import { useChatStream } from './useChatStream'

export function ChatShell({ onSignedOut }: { onSignedOut: () => void }) {
  const { exchanges, busy, send } = useChatStream(onSignedOut)

  // Back to login even if the logout request fails (offline, 5xx).
  const signOut = () =>
    logout()
      .catch(() => {})
      .finally(onSignedOut)

  return (
    <div className="flex h-dvh flex-col">
      <header className="sticky top-0 z-10 border-b-[3px] border-rail-rule bg-rail pt-[env(safe-area-inset-top)] text-rail-foreground [&_:focus-visible]:outline-rail-foreground">
        <div className="mx-auto flex w-full max-w-2xl items-center gap-3 px-4 py-3">
          <img src={avatar} alt="" className="size-10 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1">
            <h1 className="text-base font-semibold">{copy.chat.title}</h1>
            <p className="text-sm text-rail-muted">{copy.chat.subline}</p>
          </div>
          <Button
            variant="ghost"
            onClick={signOut}
            className="px-4 text-rail-foreground hover:bg-rail-foreground/10 focus-visible:shadow-[0_0_0_2px_var(--rail)]"
          >
            <LogOut size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
            {copy.chat.signOut}
          </Button>
        </div>
      </header>
      <main className="flex min-h-0 flex-1 flex-col">
        <Transcript exchanges={exchanges} />
        <TypingIndicator typing={exchanges.at(-1)?.turn.typing ?? false} />
        <Composer busy={busy} onSend={send} />
      </main>
    </div>
  )
}
