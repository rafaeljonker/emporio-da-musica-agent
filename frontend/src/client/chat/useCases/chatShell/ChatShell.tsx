import { Laptop, LogOut } from 'lucide-react'
import avatar from '@/client/shared/assets/avatar.jpg'
import { CatalogDialog } from '@/client/catalog/useCases/catalogDialog/CatalogDialog'
import { Composer } from '@/client/chat/ui/Composer'
import { EmptyState } from '@/client/chat/ui/EmptyState'
import { DemoStrip } from '@/client/chat/useCases/demoStrip/DemoStrip'
import { MetricsDetails } from '@/client/chat/useCases/metricsDetails/MetricsDetails'
import { Transcript } from '@/client/chat/useCases/transcript/Transcript'
import { Button } from '@/client/shared/components/ui/button'
import { copy } from '@/client/shared/lib/copy'
import { StatusRegion } from '@/client/warmup/ui/StatusRegion'
import { WarmupStatus } from '@/client/warmup/useCases/warmupStatus/WarmupStatus'
import { useChatShell, type ChatShellProps } from './useChatShell'

export function ChatShell(props: ChatShellProps) {
  const {
    state,
    entries,
    typing,
    busy,
    text,
    setText,
    said,
    queued,
    customerId,
    turns,
    warmupSeconds,
    local,
    onSend,
    ask,
    undo,
    resend,
    signOut,
    onSwitched,
    warmup,
    localNotice,
    showEmpty,
  } = useChatShell(props)

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
      <DemoStrip customerId={customerId} onSwitched={onSwitched}>
        <MetricsDetails turns={turns} warmupSeconds={warmupSeconds} local={local} />
        <CatalogDialog onAsk={ask} />
      </DemoStrip>
      {localNotice && (
        <p className="border-b border-border">
          <span className="mx-auto flex w-full max-w-2xl gap-2 px-4 py-2 text-sm text-muted-foreground">
            <Laptop size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden className="mt-0.5 shrink-0" />
            {copy.chat.localNotice}
          </span>
        </p>
      )}
      <main className="flex min-h-0 flex-1 flex-col">
        {warmup && <WarmupStatus {...warmup} />}
        {showEmpty && <EmptyState />}
        <Transcript entries={entries} queued={queued} typing={typing} onUndo={undo} onResend={resend} />
        {/* The visible dots live in the log (aria-hidden); this live region speaks them. */}
        <StatusRegion said={said}>{typing && <span className="sr-only">{copy.chat.typing}</span>}</StatusRegion>
        <Composer
          busy={busy}
          onSend={onSend}
          text={text}
          setText={setText}
          placeholder={state === 'warming' ? copy.warmup.placeholder : copy.chat.composerPlaceholder}
        />
      </main>
    </div>
  )
}
