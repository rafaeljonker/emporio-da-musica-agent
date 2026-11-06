import { Circle, CircleAlert, CircleCheck, Cpu, Server, WifiOff } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { WarmStatus } from '@/api/types'
import avatar from '@/assets/avatar.jpg'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy'
import { cn } from '@/lib/utils'
import { ceil10, firstReplyNote, formatDuration, formatElapsed, isLongWait } from './format'

const t = copy.warmup
const icon = { size: 20, strokeWidth: 1.75, absoluteStrokeWidth: true, 'aria-hidden': true } as const
const small = { ...icon, size: 16 }

interface Props {
  status: WarmStatus | null
  elapsed: number
  networkError: boolean
  /** A message is queued: below md the panel collapses to one pinned line. */
  compact: boolean
  onRetry: () => Promise<void>
  announce: (text: string) => void
}

/**
 * Screen 02. Renders only what the server reports: one waiting stage per mode (GPU "Ligando o
 * modelo", local "Carregando o modelo"), then "Pronto pra conversar". Never a countdown.
 */
export function WarmupStatus({ status, elapsed, networkError, compact, onRetry, announce }: Props) {
  const titleRef = useRef<HTMLHeadingElement>(null)
  const retryRef = useRef<HTMLButtonElement>(null)
  const stage = status?.stage
  const local = status?.mode === 'local_cpu'
  const waiting = local ? t.stages.model_loading : t.stages.server_starting
  const ready = stage === 'ready'
  const failed = stage === 'failed'
  const long = !!status && !ready && !failed && isLongWait(elapsed, status.expected_seconds)

  // Stage changes are spoken (not the first stage: the h2 and list are already on screen).
  const lastStage = useRef(stage)
  useEffect(() => {
    if (stage === lastStage.current) return
    lastStage.current = stage
    if (stage === 'ready') announce(t.ready)
    else if (stage && stage !== 'failed') announce(`${waiting}.`)
  }, [stage, waiting, announce])

  const longSaid = useRef(false)
  useEffect(() => {
    if (long && !longSaid.current) announce(t.longWait(waiting))
    longSaid.current ||= long
  }, [long, waiting, announce])

  useEffect(() => {
    if (networkError) announce(t.network)
  }, [networkError, announce])

  useEffect(() => {
    if (failed) retryRef.current?.focus()
  }, [failed])

  const retry = () => {
    longSaid.current = false
    titleRef.current?.focus()
    void onRetry()
  }

  const StageIcon = local ? Cpu : Server
  const items = [
    { label: waiting, state: ready ? 'done' : 'current' },
    { label: t.stages.ready, state: ready ? 'done' : 'pending' },
  ] as const

  return (
    <section
      id="warmup-panel"
      aria-labelledby="warmup-title"
      className={cn(
        'surface-paper mx-auto min-h-0 w-full max-w-md shrink overflow-y-auto px-6 py-6 md:pt-8',
        compact && 'max-md:max-w-none max-md:border-b max-md:px-4 max-md:py-2',
      )}
    >
      {compact && status && (
        <p aria-hidden className="flex items-center gap-2 font-semibold tnum md:hidden">
          <StageIcon {...small} />
          {ready ? t.stages.ready : waiting} · {formatDuration(elapsed)}
        </p>
      )}
      <div className={cn('flex items-start justify-between', compact && 'max-md:hidden')}>
        <img src={avatar} alt="" className="mb-3 size-12 rounded-full animate-breathe md:mb-4 md:size-[4.5rem]" />
        <PegsDrawing />
      </div>
      <h2
        id="warmup-title"
        ref={titleRef}
        tabIndex={-1}
        className={cn(
          'font-display text-[clamp(1.6rem,1.3rem+1.4vw,2.1rem)] leading-tight font-semibold focus:outline-none focus-visible:outline-2',
          compact && 'max-md:sr-only',
        )}
      >
        {t.title}
      </h2>

      {!status ? (
        <p className="mt-3">{t.checking}</p>
      ) : (
        <div className={cn(compact && 'max-md:hidden')}>
          <ol aria-label={t.stagesLabel} className="my-3 grid gap-2">
            {items.map(({ label, state }) => (
              <li
                key={label}
                aria-current={state === 'current' ? 'step' : undefined}
                className={cn(
                  'flex min-h-8 items-center gap-2.5 border-l-4 border-transparent pl-2.5',
                  state === 'current' && 'border-brand-text font-semibold',
                  state === 'pending' && 'text-muted-foreground',
                )}
              >
                {state === 'done' ? (
                  <CircleCheck {...icon} className="text-success" />
                ) : state === 'current' ? (
                  <StageIcon {...icon} />
                ) : (
                  <Circle {...icon} />
                )}
                <span>
                  {label}
                  <span className="sr-only">, {t.stageState[state]}</span>
                </span>
              </li>
            ))}
          </ol>
          <p className="mb-3 tnum">{formatElapsed(elapsed)}</p>
          <p className="mb-3 text-muted-foreground tnum">{t.expected(ceil10(status.expected_seconds))}</p>
          <p className="mb-3">{local ? t.explain.local_cpu : t.explain.modal_gpu}</p>
          <p className="text-sm text-muted-foreground">
            {local ? t.noteLocal : t.noteGpu(firstReplyNote(status.reply_p50_seconds))}
          </p>
        </div>
      )}

      {networkError && (
        <p className="mt-3 flex gap-2">
          <WifiOff {...small} className="mt-1 shrink-0" />
          {t.network}
        </p>
      )}
      {long && <p className="mt-3">{t.longWait(waiting)}</p>}
      {failed && (
        <div className="mt-3 flex flex-col items-start gap-3">
          <p role="alert" className="flex gap-2 text-destructive">
            <CircleAlert {...icon} className="mt-0.5 shrink-0" />
            {t.failed}
          </p>
          <Button ref={retryRef} onClick={retry}>
            {t.retry}
          </Button>
        </div>
      )}
    </section>
  )
}

/** Tuning pegs (imagery-style.md): decorative, md+ only. */
function PegsDrawing() {
  return (
    <svg
      viewBox="0 0 96 96"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className="hidden size-24 text-foreground md:block"
    >
      <path d="M34 92V30c0-14 6-24 14-26 8 2 14 12 14 26v62" />
      <path d="M42 92V20M54 92V20" />
      <circle cx="22" cy="36" r="6" />
      <path d="M28 36h6" />
      <circle cx="22" cy="58" r="6" />
      <path d="M28 58h6" />
      <circle cx="74" cy="36" r="6" fill="var(--brand)" fillOpacity=".2" />
      <path d="M68 36h-6" />
      <circle cx="74" cy="58" r="6" />
      <path d="M68 58h-6" />
    </svg>
  )
}
