import { Clock } from 'lucide-react'
import avatar from '@/client/shared/assets/avatar.jpg'
import { Button } from '@/client/shared/components/ui/button'
import { copy } from '@/client/shared/lib/copy'
import { cn } from '@/client/shared/lib/utils'
import { TypingIndicator } from '@/client/chat/ui/TypingIndicator'
import { isExchange } from '@/client/chat/domain/entries'
import { useTranscript, type TranscriptProps } from './useTranscript'

const time = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })

const bubble = 'max-w-[80%] rounded-2xl px-4 py-2.5 text-base whitespace-pre-line [overflow-wrap:anywhere] animate-arrive'

function Stamp({ at, className }: { at: Date; className?: string }) {
  return <p className={cn('text-[0.8125rem] text-muted-foreground tnum', className)}>{time.format(at)}</p>
}

/** role="log": bubbles enter the DOM only when complete, so each is announced once. */
export function Transcript(props: TranscriptProps) {
  const { state, logRef, onScroll, jumpToBottom, resend } = useTranscript(props)
  const { entries, queued, typing, onUndo } = props

  return (
    <div className={cn('relative flex flex-1 flex-col', entries.length || queued ? 'min-h-48' : 'min-h-0')}>
      <div
        ref={logRef}
        id="chat-log"
        role="log"
        aria-label={copy.chat.logLabel}
        aria-relevant="additions"
        tabIndex={0}
        onScroll={onScroll}
        // An empty log needs no 12rem floor (set on the wrapper): during warm-up the panel gets that room.
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain focus-visible:-outline-offset-2"
      >
        <div className="mx-auto flex w-full max-w-2xl flex-col px-4 pb-4">
          {entries.map((entry) => {
            if (!isExchange(entry))
              return (
                <p
                  key={entry.id}
                  className="mt-4 flex items-center gap-3 text-center text-sm text-muted-foreground before:flex-1 before:border-t before:border-border after:flex-1 after:border-t after:border-border"
                >
                  {entry.divider}
                </p>
              )
            const { id, text, sentAt, repliedAt, turn, resend: isResend, retried } = entry
            return (
              <div key={id} className="flex flex-col">
                {!isResend && (
                  <div className="mt-4 flex flex-col items-end gap-1">
                    <p className={cn(bubble, 'rounded-br-md bg-user-bubble text-user-bubble-foreground')}>
                      <span className="sr-only">{copy.chat.userPrefix}</span>
                      {text}
                    </p>
                    <Stamp at={sentAt} />
                  </div>
                )}
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
                {turn.status === 'failed' && !retried && (
                  <p
                    className={cn(
                      'mt-2 flex flex-wrap items-baseline gap-x-2 text-sm text-muted-foreground',
                      turn.bubbles.length ? 'pl-10' : 'justify-end',
                    )}
                  >
                    {turn.partial ? copy.chat.errorPartial : copy.chat.errorNoReply}
                    <Button variant="link" onClick={() => resend(id)} className="h-auto min-h-6 px-0 text-base">
                      {copy.chat.resend}
                    </Button>
                  </p>
                )}
              </div>
            )
          })}
          {queued && (
            <div className="mt-4 flex flex-col items-end gap-1">
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
          {typing && <TypingIndicator />}
        </div>
      </div>
      {state === 'unseen' && (
        <Button
          variant="secondary"
          onClick={jumpToBottom}
          className="absolute bottom-2 left-1/2 -translate-x-1/2 shadow-md"
        >
          {copy.chat.newMessages}
        </Button>
      )}
    </div>
  )
}
