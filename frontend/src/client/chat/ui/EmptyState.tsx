import { copy } from '@/client/shared/lib/copy'

/** Before the first message: a soundhole rosette (walnut lines, one honey fill) and what to ask. */
export function EmptyState() {
  return (
    <div className="mx-auto w-full max-w-2xl px-6 pt-12 text-center text-muted-foreground short:pt-4">
      <svg
        viewBox="0 0 160 160"
        width="96"
        height="96"
        aria-hidden
        className="mx-auto text-foreground"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      >
        <circle cx="80" cy="80" r="30" />
        <circle cx="80" cy="80" r="44" />
        <circle cx="80" cy="80" r="52" strokeDasharray="3 9" />
        <circle cx="80" cy="80" r="62" />
        <circle cx="80" cy="80" r="22" fill="var(--brand)" fillOpacity=".2" stroke="none" />
      </svg>
      <p className="mx-auto mt-4 max-w-[30ch]">{copy.chat.empty}</p>
      <p className="mx-auto mt-2 max-w-[36ch] text-sm">{copy.chat.emptyNote}</p>
    </div>
  )
}
