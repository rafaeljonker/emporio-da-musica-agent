import { Laptop, LogOut } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { logout } from '@/api/client'
import type { WarmStatus } from '@/api/types'
import avatar from '@/assets/avatar.jpg'
import { CatalogDialog } from '@/catalog/CatalogDialog'
import { appendQuestion } from '@/catalog/form'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy'
import { save } from '@/warmup/queue'
import { StatusRegion, type Announcement } from '@/warmup/StatusRegion'
import { useQueuedMessage } from '@/warmup/useQueuedMessage'
import { useWarmStatus } from '@/warmup/useWarmStatus'
import { WarmupStatus } from '@/warmup/WarmupStatus'
import { Composer } from './Composer'
import { DemoStrip } from './DemoStrip'
import { EmptyState } from './EmptyState'
import type { TurnRecord } from './metrics'
import { MetricsDetails } from './MetricsDetails'
import { Transcript } from './Transcript'
import { isExchange, useChatStream } from './useChatStream'

const READY_LINGER_MS = 800 // the all-done list stays this long
const READY_FOCUS_MS = 2000 // "Pronto pra conversar." is spoken before any focus move

interface Props {
  warm: WarmStatus | null
  fromLogin: boolean
  customerId: number | null
  onSignedOut: () => void
  onExpired: () => void
}

export function ChatShell({ warm, fromLogin, customerId: initialCustomer, onSignedOut, onExpired }: Props) {
  const { entries, busy, send, resend, addDivider } = useChatStream(onExpired)
  const { status, elapsed, networkError, retry } = useWarmStatus(warm, onExpired)
  const [customerId, setCustomerId] = useState(initialCustomer)
  const [said, setSaid] = useState<Announcement | null>(null)
  const announce = useCallback((text: string) => setSaid((s) => ({ n: (s?.n ?? 0) + 1, text })), [])

  // A reload after ready is ready on the first frame: no panel at all.
  const [readyOnArrival] = useState(warm?.stage === 'ready')
  const [panelGone, setPanelGone] = useState(readyOnArrival)
  const ready = status?.stage === 'ready'
  // Opened ready (provider_api, or the model was already warm): no panel, no announcement to wait
  // for. Focus would sit on the body after the login form unmounted; move it to the composer with
  // a fine pointer only (no soft keyboard on touch), never into the log.
  const [openedReady] = useState(readyOnArrival || warm?.mode === 'provider_api')
  useEffect(() => {
    if (!openedReady || (document.activeElement && document.activeElement !== document.body)) return
    if (matchMedia('(pointer: fine)').matches) document.getElementById('composer-input')?.focus()
  }, [openedReady])

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

  // Local mode runs on the user's machine: cost is R$ 0, the same as the panel says.
  const local = status?.mode === 'local_cpu'
  const turns = useMemo(
    () =>
      entries.flatMap((e): TurnRecord[] =>
        isExchange(e) && e.turn.metrics
          ? [{ metrics: local ? { ...e.turn.metrics, cost_brl: '0' } : e.turn.metrics, screenMs: e.screenMs ?? 0 }]
          : [],
      ),
    [entries, local],
  )
  // The measured cold start; provider_api never warms.
  const warmupSeconds = status?.stage === 'ready' && status.mode !== 'provider_api' ? Math.round(status.elapsed_seconds) : null
  const [text, setText] = useState(queue.restored)
  const typing = entries.some((e) => isExchange(e) && e.turn.typing)

  // "Perguntar ao assistente": the question waits in the composer after any draft, caret at the
  // end; never sent.
  const ask = useCallback((question: string) => {
    setText((draft) => appendQuestion(draft, question))
    requestAnimationFrame(() => {
      const input = document.getElementById('composer-input') as HTMLTextAreaElement | null
      input?.focus()
      input?.setSelectionRange(input.value.length, input.value.length)
    })
  }, [])

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
    // Short viewports (400% zoom ≈ 320 × 256): the page scrolls instead of squeezing the log to 0 (SC 1.4.10).
    <div className="flex h-dvh flex-col short:h-auto short:min-h-dvh">
      <header className="sticky top-0 z-10 short:static border-b-[3px] border-rail-rule bg-rail pt-[env(safe-area-inset-top)] text-rail-foreground [&_:focus-visible]:outline-rail-foreground">
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
      <DemoStrip
        customerId={customerId}
        onSwitched={(id, divider) => {
          setCustomerId(id)
          addDivider(divider)
        }}
        onSessionExpired={onExpired}
      >
        <MetricsDetails turns={turns} warmupSeconds={warmupSeconds} local={local} />
        <CatalogDialog onAsk={ask} onSessionExpired={onExpired} />
      </DemoStrip>
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
        {!warming && !entries.length && !queue.queued && <EmptyState />}
        <Transcript entries={entries} queued={queue.queued?.lines} typing={typing} onUndo={undo} onResend={resend} />
        {/* The visible dots live in the log (aria-hidden); this live region speaks them. */}
        <StatusRegion said={said}>{typing && <span className="sr-only">{copy.chat.typing}</span>}</StatusRegion>
        <Composer
          busy={busy}
          onSend={
            warming
              ? queue.add
              : (t) => {
                  void send(t)
                  return true
                }
          }
          text={text}
          setText={setText}
          placeholder={warming ? copy.warmup.placeholder : copy.chat.composerPlaceholder}
        />
      </main>
    </div>
  )
}
