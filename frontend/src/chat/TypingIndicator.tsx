import { copy } from '@/copy'

/** Mounted for the whole session, outside the log; only its content toggles. */
export function TypingIndicator({ typing }: { typing: boolean }) {
  return (
    <div role="status" className="mx-auto w-full max-w-2xl px-4">
      {typing && (
        <div className="flex items-end gap-2 pb-2">
          <span className="size-8 shrink-0" aria-hidden />
          <span className="sr-only">{copy.chat.typing}</span>
          <span aria-hidden className="flex gap-1 rounded-2xl rounded-bl-md bg-card px-4 py-3">
            <i className="typing-dot" />
            <i className="typing-dot" />
            <i className="typing-dot" />
          </span>
        </div>
      )}
    </div>
  )
}
