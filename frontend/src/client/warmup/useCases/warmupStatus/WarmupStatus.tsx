import { Circle, CircleAlert, CircleCheck, Cpu, Server, WifiOff } from 'lucide-react'
import avatar from '@/client/shared/assets/avatar.jpg'
import { Button } from '@/client/shared/components/ui/button'
import { copy } from '@/client/shared/lib/copy'
import { cn } from '@/client/shared/lib/utils'
import { ceil10, firstReplyNote, formatDuration, formatElapsed } from '@/client/warmup/domain/format'
import { PegsDrawing } from '@/client/warmup/ui/PegsDrawing'
import { useWarmupStatus, type WarmupStatusProps } from './useWarmupStatus'

const t = copy.warmup
const icon = { size: 20, strokeWidth: 1.75, absoluteStrokeWidth: true, 'aria-hidden': true } as const
const small = { ...icon, size: 16 }

/**
 * Screen 02. Renders only what the server reports: one waiting stage per mode (GPU "Ligando o
 * modelo", local "Carregando o modelo"), then "Pronto pra conversar". Never a countdown.
 */
export function WarmupStatus(props: WarmupStatusProps) {
  const { state, status, elapsed, networkError, compact, waiting, local, steps, titleRef, retryRef, retry } =
    useWarmupStatus(props)
  const StageIcon = local ? Cpu : Server

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
          {state === 'ready' ? t.stages.ready : waiting} · {formatDuration(elapsed)}
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
            {steps.map(({ label, step }) => (
              <li
                key={label}
                aria-current={step === 'current' ? 'step' : undefined}
                className={cn(
                  'flex min-h-8 items-center gap-2.5 border-l-4 border-transparent pl-2.5',
                  step === 'current' && 'border-brand-text font-semibold',
                  step === 'pending' && 'text-muted-foreground',
                )}
              >
                {step === 'done' ? (
                  <CircleCheck {...icon} className="text-success" />
                ) : step === 'current' ? (
                  <StageIcon {...icon} />
                ) : (
                  <Circle {...icon} />
                )}
                <span>
                  {label}
                  <span className="sr-only">, {t.stageState[step]}</span>
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
      {state === 'long' && <p className="mt-3">{t.longWait(waiting)}</p>}
      {state === 'failed' && (
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
