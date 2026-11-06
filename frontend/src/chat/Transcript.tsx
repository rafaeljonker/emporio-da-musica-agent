import { Clock } from 'lucide-react'
import { useEffect, useRef } from 'react'
import avatar from '@/assets/avatar.jpg'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy'
import { cn } from '@/lib/utils'
import type { Exchange } from './useChatStream'

const time = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })
const NEAR_BOTTOM_PX = 80

const bubble = 'max-w-[80%] rounded-2xl px-4 py-2.5 text-base whitespace-pre-line [overflow-wrap:anywhere] animate-arrive'

function Stamp({ at, className }: { at: Date; className?: string }) {
  return <p className={cn('text-[0.8125rem] text-muted-foreground tnum', className)}>{time.format(at)}</p>
}

interface Props {
  exchanges: Exchange[]
  /** Lines typed during warm-up, shown as one pending group until the model is ready. */
  queued?: string[]
  onUndo: () => void
}

/** role="log": bubbles enter the DOM only when complete, so each is announced once. */
export function Transcript({ exchanges, queued, onUndo }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const last = exchanges.at(-1)
  const contentKey = `${exchanges.length}:${last?.turn.bubbles.length}:${last?.turn.status}:${queued?.length}`

  // Follow new content only when the reader is already near the bottom; focus never moves.
  const nearBottom = useRef(true)
  useEffect(() => {
    const el = ref.current
    if (el && nearBottom.current) el.scrollTop = el.scrollHeight
  }, [contentKey])

  return (
    <div
      ref={ref}
      id="chat-log"
      role="log"
      aria-label={copy.chat.logLabel}
      aria-relevant="additions"
      tabIndex={0}
      onScroll={(e) => {
        const el = e.currentTarget
        nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX
      }}
      // An empty log needs no 12rem floor: during warm-up the panel gets that room.
      className={cn(
        'flex-1 overflow-y-auto focus-visible:-outline-offset-2',
        exchanges.length || queued ? 'min-h-48' : 'min-h-0',
      )}
    >
      <div className="mx-auto flex w-full max-w-2xl flex-col px-4 py-4">
        {exchanges.map(({ id, text, sentAt, repliedAt, turn }) => (
          <div key={id} className="flex flex-col">
            <div className="mt-4 flex flex-col items-end gap-1 first:mt-0">
              <p className={cn(bubble, 'rounded-br-md bg-user-bubble text-user-bubble-foreground')}>
                <span className="sr-only">{copy.chat.userPrefix}</span>
                {text}
              </p>
              <Stamp at={sentAt} />
            </div>
            {turn.bubbles.length > 0 && (
              <div className="mt-4 flex flex-col gap-2">
                {turn.bubbles.map((b, i) => {
                  const isLast = i === turn.bubbles.length - 1
                  return (
                    <div key={i} className="flex items-end gap-2">
                      {isLast ? (
                        <img src={avatar} alt="" className="size-8 shrink-0 rounded-full" />
                      ) : (
                        <span className="size-8 shrink-0" aria-hidden />
                      )}
                      <p
                        className={cn(
                          bubble,
                          'bg-card text-card-foreground',
                          i === 0 ? 'rounded-bl-md' : 'rounded-tl-md rounded-bl-md',
                        )}
                      >
                        <span className="sr-only">{copy.chat.agentPrefix}</span>
                        {b}
                      </p>
                    </div>
                  )
                })}
                {repliedAt && <Stamp at={repliedAt} className="pl-10" />}
              </div>
            )}
            {turn.status === 'failed' && (
              <p className={cn('mt-2 text-sm text-muted-foreground', turn.bubbles.length ? 'pl-10' : 'text-right')}>
                {turn.partial ? copy.chat.errorPartial : copy.chat.errorNoReply}
              </p>
            )}
          </div>
        ))}
        {queued && (
          <div className="mt-4 flex flex-col items-end gap-1 first:mt-0">
            {queued.map((line, i) => (
              <p key={i} className={cn(bubble, 'rounded-br-md bg-user-bubble text-user-bubble-foreground')}>
                <span className="sr-only">{copy.chat.userPrefix}</span>
                {line}
              </p>
            ))}
            <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Clock size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
              {copy.warmup.queued}
            </p>
            <Button variant="link" onClick={onUndo} className="h-auto min-h-6 px-0 text-base">
              {copy.warmup.undo}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
