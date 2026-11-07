import { CircleCheck, PackagePlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { copy } from '@/copy'
import { MyProducts } from './MyProducts'
import { ProductForm } from './ProductForm'
import { useCatalogDialog, type CatalogDialogProps } from './useCatalogDialog'

const c = copy.catalog

/** "Catálogo" in the demo strip: a dialog where a signed-in visitor adds and edits own products. */
export function CatalogDialog(props: CatalogDialogProps) {
  const vm = useCatalogDialog(props)

  return (
    <Dialog open={vm.open} onOpenChange={vm.onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" className="gap-1.5 rounded-md px-2 text-muted-foreground">
          <PackagePlus size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
          {c.trigger}
        </Button>
      </DialogTrigger>
      <DialogContent closeLabel={c.close} onCloseAutoFocus={vm.onCloseAutoFocus}>
        <div className="flex shrink-0 flex-col gap-1 border-b border-border px-5 pt-5 pr-14 pb-4">
          <DialogTitle>{vm.editing ? c.editTitle : c.title}</DialogTitle>
          <DialogDescription>{c.description}</DialogDescription>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto short:flex-none short:overflow-visible px-5 pt-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
          {vm.loadFailure && (
            <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg bg-card p-3 text-sm font-semibold">
              <span className="flex-1">{vm.loadFailure}</span>
              <Button variant="secondary" onClick={vm.retry}>
                {c.retry}
              </Button>
            </div>
          )}
          {vm.saved ? (
            <section aria-labelledby="catalog-saved" className="flex flex-col items-start gap-4 rounded-lg bg-card p-4">
              <div className="flex items-start gap-2">
                <CircleCheck size={24} strokeWidth={1.75} absoluteStrokeWidth aria-hidden className="shrink-0 text-success" />
                <div>
                  <h3 id="catalog-saved" tabIndex={-1} className="text-lg font-semibold">
                    {vm.saved.edited ? c.updated : c.saved}
                  </h3>
                  <p className="text-sm">
                    <strong>{vm.saved.name}</strong>. {c.savedNote}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={vm.ask}>{c.ask}</Button>
                <Button variant="secondary" onClick={vm.newProduct}>
                  {c.another}
                </Button>
              </div>
            </section>
          ) : (
            <ProductForm
              key={vm.formKey}
              editing={vm.editing}
              categories={vm.categories}
              onSaved={vm.onSaved}
              onCancelEdit={vm.newProduct}
              onSessionExpired={props.onSessionExpired}
            />
          )}

          <MyProducts products={vm.mine} onEdit={vm.onEdit} />
        </div>
      </DialogContent>
    </Dialog>
  )
}
