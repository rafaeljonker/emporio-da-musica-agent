import { Pencil } from 'lucide-react'
import { productSummary } from '@/client/catalog/domain/catalog'
import type { Product } from '@/client/shared/lib/apiTypes'
import { Button } from '@/client/shared/components/ui/button'
import { copy } from '@/client/shared/lib/copy'

const c = copy.catalog

interface Props {
  /** Nothing is listed until this opening's list arrives (or a save lands first). */
  mine: { state: 'pending' } | { state: 'ready'; products: Product[] }
  onEdit: (product: Product) => void
}

/** "Meus produtos": the visitor's products, each with "Editar". */
export function MyProducts({ mine, onEdit }: Props) {
  return (
    <section aria-labelledby="catalog-mine" className="flex flex-col gap-2 border-t border-border pt-4">
      <h3 id="catalog-mine" className="text-base font-semibold">
        {c.mine}
      </h3>
      {mine.state === 'pending' ? null : mine.products.length === 0 ? (
        <p className="text-sm text-muted-foreground">{c.mineEmpty}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-border">
          {mine.products.map((p) => (
            <li key={p.id} className="flex items-center gap-3 py-2">
              <div className="min-w-0 flex-1">
                <p className="font-semibold [overflow-wrap:anywhere]">{p.name}</p>
                <p className="text-sm text-muted-foreground tnum">{productSummary(p)}</p>
              </div>
              <Button
                variant="ghost"
                aria-label={c.editName(p.name)}
                onClick={() => onEdit(p)}
                className="gap-1.5 rounded-md px-3 text-muted-foreground"
              >
                <Pencil size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
                {c.edit}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
