import { PackagePlus } from 'lucide-react'
import { MyProducts } from '@/client/catalog/ui/MyProducts'
import { SavedPanel } from '@/client/catalog/ui/SavedPanel'
import { ProductForm } from '@/client/catalog/useCases/productForm/ProductForm'
import { Button } from '@/client/shared/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/client/shared/components/ui/dialog'
import { copy } from '@/client/shared/lib/copy'
import { useCatalogDialog, type CatalogDialogProps } from './useCatalogDialog'

const c = copy.catalog

/** "Catálogo" in the demo strip: a dialog where a signed-in visitor adds and edits own products. */
export function CatalogDialog(props: CatalogDialogProps) {
  const {
    open,
    editing,
    panel,
    mine,
    alert,
    categories,
    onOpenChange,
    onCloseAutoFocus,
    retry,
    ask,
    newProduct,
    onEdit,
    onSaved,
  } = useCatalogDialog(props)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" className="gap-1.5 rounded-md px-2 text-muted-foreground">
          <PackagePlus size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
          {c.trigger}
        </Button>
      </DialogTrigger>
      <DialogContent closeLabel={c.close} onCloseAutoFocus={onCloseAutoFocus}>
        <div className="flex shrink-0 flex-col gap-1 border-b border-border px-5 pt-5 pr-14 pb-4">
          <DialogTitle>{editing ? c.editTitle : c.title}</DialogTitle>
          <DialogDescription>{c.description}</DialogDescription>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto short:flex-none short:overflow-visible px-5 pt-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
          {alert && (
            <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg bg-card p-3 text-sm font-semibold">
              <span className="flex-1">{alert}</span>
              <Button variant="secondary" onClick={retry}>
                {c.retry}
              </Button>
            </div>
          )}
          {panel.state === 'saved' ? (
            <SavedPanel name={panel.name} edited={panel.edited} onAsk={ask} onAnother={newProduct} />
          ) : (
            <ProductForm
              key={panel.formKey}
              editing={editing}
              categories={categories}
              onSaved={onSaved}
              onCancelEdit={newProduct}
            />
          )}

          <MyProducts mine={mine} onEdit={onEdit} />
        </div>
      </DialogContent>
    </Dialog>
  )
}
