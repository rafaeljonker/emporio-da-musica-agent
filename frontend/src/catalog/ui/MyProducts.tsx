import { Pencil } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import type { Product } from '@/api/types'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy'
import { productSummary } from '../domain/catalog'

const c = copy.catalog

interface Props {
  /** null until this opening's list arrives. */
  products: Product[] | null
  /** Reads the product from the button's data-id. */
  onEdit: MouseEventHandler<HTMLButtonElement>
}

/** "Meus produtos": the visitor's products, each with "Editar". */
export function MyProducts({ products, onEdit }: Props) {
  return (
    <section aria-labelledby="catalog-mine" className="flex flex-col gap-2 border-t border-border pt-4">
      <h3 id="catalog-mine" className="text-base font-semibold">
        {c.mine}
      </h3>
      {products === null ? null : products.length === 0 ? (
        <p className="text-sm text-muted-foreground">{c.mineEmpty}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-border">
          {products.map((p) => (
            <li key={p.id} className="flex items-center gap-3 py-2">
              <div className="min-w-0 flex-1">
                <p className="font-semibold [overflow-wrap:anywhere]">{p.name}</p>
                <p className="text-sm text-muted-foreground tnum">{productSummary(p)}</p>
              </div>
              <Button
                variant="ghost"
                aria-label={c.editName(p.name)}
                data-id={p.id}
                onClick={onEdit}
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
