import { FlaskConical } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { customers as fetchCustomers, setIdentity } from '@/client/shared/lib/api'
import type { DemoCustomer } from '@/client/shared/lib/apiTypes'
import { Label } from '@/client/shared/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/client/shared/components/ui/select'
import { copy } from '@/client/shared/lib/copy'

const ANON = 'anon'
const TRIGGER_ID = 'conversar-como'

interface Props {
  customerId: number | null
  /** After PUT /api/identity succeeded (the server rotated the session): the shell adds the divider. */
  onSwitched: (customerId: number | null, divider: string) => void
  children: ReactNode
}

function Item({ value, name, note }: { value: string; name: string; note: string }) {
  return (
    <SelectItem
      value={value}
      className="min-h-11 rounded-sm py-2 pr-8 pl-3 text-base data-[state=checked]:font-semibold data-[state=checked]:ring-1 data-[state=checked]:ring-ring data-[state=checked]:ring-inset data-[state=checked]:shadow-[inset_4px_0_0_var(--brand)]"
    >
      <span className="flex flex-col items-start">
        <span>{name}</span>
        {/* The comma keeps name and note apart in the option's accessible name; hidden with the note in the trigger. */}
        <span data-note className="text-sm font-normal text-muted-foreground">
          <span className="sr-only">, </span>
          {note}
        </span>
      </span>
    </SelectItem>
  )
}

/** `<aside aria-label="Demonstração">`: demo tools kept apart from store content. Children: the Métricas toggle and the Catálogo dialog. */
export function DemoStrip({ customerId, onSwitched, children }: Props) {
  const [list, setList] = useState<DemoCustomer[]>([])
  useEffect(() => {
    void fetchCustomers().then((res) => res.ok && setList(res.data))
  }, [])

  // Selection follows the server: it changes only after the PUT succeeds. Focus never moves (SC 3.2.2).
  const change = async (value: string) => {
    const id = value === ANON ? null : Number(value)
    if (!(await setIdentity(id)).ok) return
    const name = list.find((c) => c.id === id)?.name.split(' ')[0]
    onSwitched(id, name ? copy.demo.nowAs(name) : copy.demo.nowAnonymous)
  }

  return (
    <aside aria-label={copy.demo.tag} className="border-b border-border bg-background">
      <div className="relative mx-auto flex w-full max-w-2xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2 text-sm">
        <span className="inline-flex items-center gap-1.5 font-semibold text-muted-foreground">
          <FlaskConical size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
          {copy.demo.tag}
        </span>
        <Label htmlFor={TRIGGER_ID} className="text-sm text-muted-foreground">
          {copy.demo.selectorLabel}
        </Label>
        <Select value={customerId === null ? ANON : String(customerId)} onValueChange={change}>
          <SelectTrigger
            id={TRIGGER_ID}
            className="h-11 max-w-80 min-w-48 flex-[1_1_12rem] rounded-md bg-popover px-3 text-base text-foreground focus-visible:border-input focus-visible:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring data-[size=default]:h-11 [&_[data-note]]:hidden"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent position="popper" className="rounded-lg border border-border shadow-md ring-0">
            <Item value={ANON} name={copy.demo.anonymous} note={copy.demo.anonymousNote} />
            {list.map((c) => (
              <Item key={c.id} value={String(c.id)} name={c.name} note={c.city} />
            ))}
          </SelectContent>
        </Select>
        {children}
      </div>
    </aside>
  )
}
