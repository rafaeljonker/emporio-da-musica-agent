import { CircleCheck } from 'lucide-react'
import { Button } from '@/client/shared/components/ui/button'
import { copy } from '@/client/shared/lib/copy'

const c = copy.catalog

interface Props {
  name: string
  edited: boolean
  onAsk: () => void
  onAnother: () => void
}

/** Replaces the form after a save; its heading takes focus (id catalog-saved). */
export function SavedPanel({ name, edited, onAsk, onAnother }: Props) {
  return (
    <section aria-labelledby="catalog-saved" className="flex flex-col items-start gap-4 rounded-lg bg-card p-4">
      <div className="flex items-start gap-2">
        <CircleCheck size={24} strokeWidth={1.75} absoluteStrokeWidth aria-hidden className="shrink-0 text-success" />
        <div>
          <h3 id="catalog-saved" tabIndex={-1} className="text-lg font-semibold">
            {edited ? c.updated : c.saved}
          </h3>
          <p className="text-sm">
            <strong>{name}</strong>. {c.savedNote}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button onClick={onAsk}>{c.ask}</Button>
        <Button variant="secondary" onClick={onAnother}>
          {c.another}
        </Button>
      </div>
    </section>
  )
}
