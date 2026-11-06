import { Laptop, LogOut } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { logout } from '@/api/client'
import type { WarmStatus } from '@/api/types'
import avatar from '@/assets/avatar.jpg'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy'
import { save } from '@/warmup/queue'
import { StatusRegion, type Announcement } from '@/warmup/StatusRegion'
import { useQueuedMessage } from '@/warmup/useQueuedMessage'
import { useWarmStatus } from '@/warmup/useWarmStatus'
import { WarmupStatus } from '@/warmup/WarmupStatus'
import { Composer } from './Composer'
import { TypingIndicator } from './TypingIndicator'
import { Transcript } from './Transcript'
import { useChatStream } from './useChatStream'

const READY_LINGER_MS = 800 // the all-done list stays this long
const READY_FOCUS_MS = 2000 // "Pronto pra conversar." is spoken before any focus move

interface Props {
  warm: WarmStatus | null
  fromLogin: boolean
  onSignedOut: () => void
}

export function ChatShell({ warm, fromLogin, onSignedOut }: Props) {
  const { exchanges, busy, send } = useChatStream(onSignedOut)
  const { status, elapsed, networkError, retry } = useWarmStatus(warm, onSignedOut)
  const [said, setSaid] = useState<Announcement | null>(null)
  const announce = useCallback((text: string) => setSaid((s) => ({ n: (s?.n ?? 0) + 1, text })), [])

  // A reload after ready is ready on the first frame: no panel at all.
  const [readyOnArrival] = useState(warm?.stage === 'ready')
  const [panelGone, setPanelGone] = useState(readyOnArrival)
  const ready = status?.stage === 'ready'
  useEffect(() => {
    if (!ready || readyOnArrival) return
    const close = setTimeout(() => setPanelGone(true), READY_LINGER_MS)
    // Focus moves only if it was on the body or in the removed panel (now the body);
    // to the composer with a fine pointer, to the log on touch (no soft keyboard).
    const focus = setTimeout(() => {
      if (document.activeElement && document.activeElement !== document.body) return
      const fine = matchMedia('(pointer: fine)').matches
      document.getElementById(fine ? 'composer-input' : 'chat-log')?.focus()
    }, READY_FOCUS_MS)
    return () => {
      clearTimeout(close)
      clearTimeout(focus)
    }
  }, [ready, readyOnArrival])

  // provider_api never warms, whatever the seed said.
  const warming = !panelGone && status?.mode !== 'provider_api'
  const queue = useQueuedMessage(!warming, send, fromLogin)
  const [text, setText] = useState(queue.restored)

  const undo = () => {
    const back = queue.take()
    setText(text ? `${back}\n${text}` : back)
    announce(copy.warmup.undone)
    document.getElementById('composer-input')?.focus()
  }

  // Back to login even if the logout request fails (offline, 5xx). Sair drops a queued message;
  // an expired session keeps it for the next login.
  const signOut = () => {
    save(null)
    logout()
      .catch(() => {})
      .finally(onSignedOut)
  }

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
      {!warming && status?.mode === 'local_cpu' && (
        <p className="border-b border-border">
          <span className="mx-auto flex w-full max-w-2xl gap-2 px-4 py-2 text-sm text-muted-foreground">
            <Laptop size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden className="mt-0.5 shrink-0" />
            {copy.chat.localNotice}
          </span>
        </p>
      )}
      <main className="flex min-h-0 flex-1 flex-col">
        {warming && (
          <WarmupStatus
            status={status}
            elapsed={elapsed}
            networkError={networkError}
            compact={!!queue.queued}
            onRetry={retry}
            announce={announce}
          />
        )}
        <Transcript exchanges={exchanges} queued={queue.queued?.lines} onUndo={undo} />
        <StatusRegion said={said}>
          <TypingIndicator typing={exchanges.at(-1)?.turn.typing ?? false} />
        </StatusRegion>
        <Composer
          busy={busy}
          onSend={warming ? queue.add : send}
          text={text}
          setText={setText}
          placeholder={warming ? copy.warmup.placeholder : copy.chat.composerPlaceholder}
        />
      </main>
    </div>
  )
}
