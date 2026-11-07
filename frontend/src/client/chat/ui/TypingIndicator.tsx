/**
 * The visible dots, under the last bubble inside the log (like WhatsApp). aria-hidden: the log
 * only ever gains complete bubbles; "digitando" is spoken by the StatusRegion in <main>.
 */
export function TypingIndicator() {
  return (
    <div aria-hidden className="mt-4 flex items-end gap-2">
      <span className="size-8 shrink-0" />
      <span className="flex animate-arrive gap-1 rounded-2xl rounded-bl-md bg-card px-4 py-3">
        <i className="typing-dot" />
        <i className="typing-dot" />
        <i className="typing-dot" />
      </span>
    </div>
  )
}
