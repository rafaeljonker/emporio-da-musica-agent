import { CircleCheck, PackagePlus, Pencil } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { catalogCategories, createProduct, myProducts, updateProduct, type ApiError } from '@/client/shared/lib/api'
import { errorMessage, fieldFor } from '@/client/shared/lib/errorMessage'
import type { Category, Product, ProductStatus } from '@/client/shared/lib/apiTypes'
import { Button } from '@/client/shared/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/client/shared/components/ui/dialog'
import { Input } from '@/client/shared/components/ui/input'
import { Label } from '@/client/shared/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/client/shared/components/ui/select'
import { Textarea } from '@/client/shared/components/ui/textarea'
import { copy } from '@/client/shared/lib/copy'
import {
  EMPTY,
  formatPrice,
  mergeById,
  priceInput,
  toFields,
  toPrice,
  validate,
  type FieldErrors,
  type ProductFields,
} from '@/client/catalog/domain/form'

const c = copy.catalog
const ORDER: (keyof ProductFields)[] = ['name', 'categoryId', 'description', 'price', 'stock', 'status', 'specs']
const id = (field: keyof ProductFields) => `catalog-${field}`
const SELECT_CLASS =
  'h-11 w-full rounded-md bg-popover px-3 text-base text-foreground focus-visible:border-input focus-visible:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring data-[size=default]:h-11 aria-invalid:border-destructive'
const ITEM_CLASS = 'min-h-11 py-2 pl-3 text-base'

interface Props {
  /** "Perguntar ao assistente": the shell puts this text in the composer (not sent). */
  onAsk: (text: string) => void
}

interface FieldProps {
  field: keyof ProductFields
  label: string
  hint?: string
  error?: string
  children: (describedBy: string | undefined) => ReactNode
}

/** Label, control, hint and error, tied with aria-describedby. */
function Field({ field, label, hint, error, children }: FieldProps) {
  const ids = [hint && `${id(field)}-hint`, error && `${id(field)}-error`].filter(Boolean).join(' ')
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id(field)}>{label}</Label>
      {children(ids || undefined)}
      {hint && (
        <p id={`${id(field)}-hint`} className="text-sm text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id(field)}-error`} className="text-sm font-semibold text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

/** "Catálogo" in the demo strip: a dialog where a signed-in visitor adds and edits own products. */
export function CatalogDialog({ onAsk }: Props) {
  const [open, setOpen] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  /** null until this opening's list arrives. */
  const [mine, setMine] = useState<Product[] | null>(null)
  const [loadFailure, setLoadFailure] = useState<string | null>(null)
  const [loads, setLoads] = useState(0)
  const [fields, setFields] = useState<ProductFields>(EMPTY)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [failure, setFailure] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState<Product | null>(null)
  const [saved, setSaved] = useState<{ name: string; edited: boolean } | null>(null)
  // After the re-render that shows the error, so the reader announces it with the field.
  const focusField = (field: keyof ProductFields) =>
    requestAnimationFrame(() => document.getElementById(id(field))?.focus())
  const savedHeading = useRef<HTMLHeadingElement>(null)
  const asking = useRef<string | null>(null)

  useEffect(() => {
    if (!open) return
    let live = true
    // An expired session signs out (the app listens); nothing to show here.
    const failed = (error: ApiError) => {
      if (error.code !== 'unauthenticated') setLoadFailure(errorMessage(error, 'catalogLoad'))
    }
    setLoadFailure(null)
    void catalogCategories().then((res) => {
      if (!live) return
      if (res.ok) setCategories(res.data)
      else failed(res.error)
    })
    // A save may land first: the rows it put on screen win over this (older) server list.
    void myProducts().then((res) => {
      if (!live) return
      if (res.ok) setMine((shown) => mergeById(shown ?? [], res.data))
      else failed(res.error)
    })
    return () => {
      live = false
    }
  }, [open, loads])

  useEffect(() => savedHeading.current?.focus(), [saved])

  const set = (field: keyof ProductFields) => (value: string) => setFields((f) => ({ ...f, [field]: value }))

  const reset = (next: ProductFields = EMPTY, product: Product | null = null) => {
    setFields(next)
    setErrors({})
    setFailure(null)
    setSaved(null)
    setEditing(product)
    // "Cadastrar outro" and "Cancelar edição" unmount the button that had focus.
    focusField('name')
  }

  const startEdit = (p: Product) => {
    reset(toFields(p), p)
    // After the form re-renders filled in.
    requestAnimationFrame(() => {
      const name = document.getElementById(id('name'))
      name?.scrollIntoView({ block: 'center' })
      name?.focus()
    })
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (saving) return
    const { body, errors: found } = validate(fields)
    setErrors(found)
    setFailure(null)
    if (!body) {
      const first = ORDER.find((f) => found[f])
      if (first) focusField(first)
      return
    }
    setSaving(true)
    const res = editing ? await updateProduct(editing.id, body) : await createProduct(body)
    setSaving(false)
    if (res.ok) {
      const product = res.data
      setMine((list) => [product, ...(list ?? []).filter((p) => p.id !== product.id)])
      setSaved({ name: product.name, edited: !!editing })
      setEditing(null)
      setFields(EMPTY)
      return
    }
    // An expired session signs out (the app listens).
    if (res.error.code === 'unauthenticated') return
    const message = errorMessage(res.error, 'catalogSave')
    const field = fieldFor(res.error.code)
    if (field) {
      setErrors({ [field]: message })
      focusField(field)
    } else setFailure(message)
  }

  const ask = () => {
    if (!saved) return
    asking.current = c.askPrompt(saved.name)
    setOpen(false)
  }

  const onOpenChange = (next: boolean) => {
    setOpen(next)
    if (next) {
      reset()
      setMine(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" className="gap-1.5 rounded-md px-2 text-muted-foreground">
          <PackagePlus size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
          {c.trigger}
        </Button>
      </DialogTrigger>
      <DialogContent
        closeLabel={c.close}
        onCloseAutoFocus={(e) => {
          // "Perguntar ao assistente": focus goes to the composer instead of back to the trigger.
          const text = asking.current
          asking.current = null
          if (text === null) return
          e.preventDefault()
          onAsk(text)
        }}
      >
        <div className="flex shrink-0 flex-col gap-1 border-b border-border px-5 pt-5 pr-14 pb-4">
          <DialogTitle>{editing ? c.editTitle : c.title}</DialogTitle>
          <DialogDescription>{c.description}</DialogDescription>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto short:flex-none short:overflow-visible px-5 pt-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
          {loadFailure && (
            <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg bg-card p-3 text-sm font-semibold">
              <span className="flex-1">{loadFailure}</span>
              <Button variant="secondary" onClick={() => setLoads((n) => n + 1)}>
                {c.retry}
              </Button>
            </div>
          )}
          {saved ? (
            <section aria-labelledby="catalog-saved" className="flex flex-col items-start gap-4 rounded-lg bg-card p-4">
              <div className="flex items-start gap-2">
                <CircleCheck size={24} strokeWidth={1.75} absoluteStrokeWidth aria-hidden className="shrink-0 text-success" />
                <div>
                  <h3 id="catalog-saved" ref={savedHeading} tabIndex={-1} className="text-lg font-semibold">
                    {saved.edited ? c.updated : c.saved}
                  </h3>
                  <p className="text-sm">
                    <strong>{saved.name}</strong>. {c.savedNote}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={ask}>{c.ask}</Button>
                <Button variant="secondary" onClick={() => reset()}>
                  {c.another}
                </Button>
              </div>
            </section>
          ) : (
            <form noValidate onSubmit={submit} aria-label={editing ? c.editTitle : c.title} className="flex flex-col gap-4">
              <Field field="name" label={c.name} error={errors.name}>
                {(d) => (
                  <Input
                    id={id('name')}
                    value={fields.name}
                    maxLength={120}
                    autoComplete="off"
                    aria-invalid={!!errors.name}
                    aria-describedby={d}
                    onChange={(e) => set('name')(e.target.value)}
                  />
                )}
              </Field>
              <Field field="categoryId" label={c.category} error={errors.categoryId}>
                {(d) => (
                  <Select value={fields.categoryId} onValueChange={set('categoryId')}>
                    <SelectTrigger id={id('categoryId')} aria-invalid={!!errors.categoryId} aria-describedby={d} className={SELECT_CLASS}>
                      <SelectValue placeholder={c.categoryPlaceholder} />
                    </SelectTrigger>
                    <SelectContent position="popper" className="max-h-72 rounded-lg border border-border shadow-md ring-0">
                      {categories.map((cat) => (
                        <SelectItem key={cat.id} value={String(cat.id)} className={ITEM_CLASS}>
                          {cat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </Field>
              <Field field="description" label={c.descriptionLabel} hint={c.descriptionHint} error={errors.description}>
                {(d) => (
                  <Textarea
                    id={id('description')}
                    value={fields.description}
                    rows={2}
                    maxLength={2000}
                    aria-invalid={!!errors.description}
                    aria-describedby={d}
                    onChange={(e) => set('description')(e.target.value)}
                    className="min-h-20"
                  />
                )}
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field field="price" label={c.price} error={errors.price}>
                  {(d) => (
                    <Input
                      id={id('price')}
                      inputMode="decimal"
                      placeholder="0,00"
                      autoComplete="off"
                      value={fields.price}
                      aria-invalid={!!errors.price}
                      aria-describedby={d}
                      onChange={(e) => set('price')(e.target.value)}
                      // Shown as BRL once it parses: "1234.5" becomes "1.234,50".
                      onBlur={() => {
                        const price = toPrice(fields.price)
                        if (price) set('price')(priceInput(price))
                      }}
                      className="tnum"
                    />
                  )}
                </Field>
                <Field field="stock" label={c.stock} error={errors.stock}>
                  {(d) => (
                    <Input
                      id={id('stock')}
                      type="number"
                      min={0}
                      max={100_000}
                      step={1}
                      inputMode="numeric"
                      value={fields.stock}
                      aria-invalid={!!errors.stock}
                      aria-describedby={d}
                      onChange={(e) => set('stock')(e.target.value)}
                      className="tnum"
                    />
                  )}
                </Field>
              </div>
              <Field field="status" label={c.status}>
                {() => (
                  <Select value={fields.status} onValueChange={set('status')}>
                    <SelectTrigger id={id('status')} className={SELECT_CLASS}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent position="popper" className="rounded-lg border border-border shadow-md ring-0">
                      {(Object.keys(c.statuses) as ProductStatus[]).map((s) => (
                        <SelectItem key={s} value={s} className={ITEM_CLASS}>
                          {c.statuses[s]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </Field>
              <Field field="specs" label={c.specs} hint={c.specsHint} error={errors.specs}>
                {(d) => (
                  <Textarea
                    id={id('specs')}
                    value={fields.specs}
                    rows={3}
                    placeholder={c.specsPlaceholder}
                    aria-invalid={!!errors.specs}
                    aria-describedby={d}
                    onChange={(e) => set('specs')(e.target.value)}
                    className="min-h-24"
                  />
                )}
              </Field>
              {failure && (
                <p role="alert" className="text-sm font-semibold text-destructive">
                  {failure}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" aria-disabled={saving}>
                  {saving ? c.saving : editing ? c.update : c.submit}
                </Button>
                {editing && (
                  <Button type="button" variant="secondary" onClick={() => reset()}>
                    {c.cancelEdit}
                  </Button>
                )}
              </div>
            </form>
          )}

          <section aria-labelledby="catalog-mine" className="flex flex-col gap-2 border-t border-border pt-4">
            <h3 id="catalog-mine" className="text-base font-semibold">
              {c.mine}
            </h3>
            {mine === null ? null : mine.length === 0 ? (
              <p className="text-sm text-muted-foreground">{c.mineEmpty}</p>
            ) : (
              <ul className="flex flex-col divide-y divide-border">
                {mine.map((p) => (
                  <li key={p.id} className="flex items-center gap-3 py-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold [overflow-wrap:anywhere]">{p.name}</p>
                      <p className="text-sm text-muted-foreground tnum">
                        {[p.category, formatPrice(p.price), c.stockValue(p.stock), p.status !== 'active' && c.statuses[p.status]]
                          .filter(Boolean)
                          .join(' · ')}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      aria-label={c.editName(p.name)}
                      onClick={() => startEdit(p)}
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
        </div>
      </DialogContent>
    </Dialog>
  )
}
