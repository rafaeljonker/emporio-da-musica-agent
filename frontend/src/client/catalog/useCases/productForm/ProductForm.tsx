import { Controller } from 'react-hook-form'
import { fieldId } from '@/client/catalog/domain/catalog'
import { Field } from '@/client/catalog/ui/Field'
import type { Category, ProductStatus } from '@/client/shared/lib/apiTypes'
import { Button } from '@/client/shared/components/ui/button'
import { Input } from '@/client/shared/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/client/shared/components/ui/select'
import { Textarea } from '@/client/shared/components/ui/textarea'
import { copy } from '@/client/shared/lib/copy'
import { useProductForm, type ProductFormProps } from './useProductForm'

const c = copy.catalog
const STATUSES = Object.keys(c.statuses) as ProductStatus[]
const SELECT_CLASS =
  'h-11 w-full rounded-md bg-popover px-3 text-base text-foreground focus-visible:border-input focus-visible:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring data-[size=default]:h-11 aria-invalid:border-destructive'
const ITEM_CLASS = 'min-h-11 py-2 pl-3 text-base'

interface Props extends ProductFormProps {
  categories: Category[]
  onCancelEdit: () => void
}

/** The add/edit form of the Catálogo dialog. */
export function ProductForm({ categories, onCancelEdit, ...props }: Props) {
  const { state, fields, control, errors, describedBy: d, alert, onSubmit } = useProductForm(props)
  const { editing } = props

  return (
    <form noValidate onSubmit={onSubmit} aria-label={editing ? c.editTitle : c.title} className="flex flex-col gap-4">
      <Field field="name" label={c.name} error={errors.name}>
        <Input
          id={fieldId('name')}
          maxLength={120}
          autoComplete="off"
          aria-invalid={!!errors.name}
          aria-describedby={d.name}
          {...fields.name}
        />
      </Field>
      <Field field="categoryId" label={c.category} error={errors.categoryId}>
        <Controller
          control={control}
          name="categoryId"
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger
                id={fieldId('categoryId')}
                aria-invalid={!!errors.categoryId}
                aria-describedby={d.categoryId}
                className={SELECT_CLASS}
              >
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
        />
      </Field>
      <Field field="description" label={c.descriptionLabel} hint={c.descriptionHint} error={errors.description}>
        <Textarea
          id={fieldId('description')}
          rows={2}
          maxLength={2000}
          aria-invalid={!!errors.description}
          aria-describedby={d.description}
          className="min-h-20"
          {...fields.description}
        />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field field="price" label={c.price} error={errors.price}>
          <Input
            id={fieldId('price')}
            inputMode="decimal"
            placeholder="0,00"
            autoComplete="off"
            aria-invalid={!!errors.price}
            aria-describedby={d.price}
            className="tnum"
            {...fields.price}
          />
        </Field>
        <Field field="stock" label={c.stock} error={errors.stock}>
          <Input
            id={fieldId('stock')}
            type="number"
            min={0}
            max={100_000}
            step={1}
            inputMode="numeric"
            aria-invalid={!!errors.stock}
            aria-describedby={d.stock}
            className="tnum"
            {...fields.stock}
          />
        </Field>
      </div>
      <Field field="status" label={c.status}>
        <Controller
          control={control}
          name="status"
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger id={fieldId('status')} className={SELECT_CLASS}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent position="popper" className="rounded-lg border border-border shadow-md ring-0">
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s} className={ITEM_CLASS}>
                    {c.statuses[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </Field>
      <Field field="specs" label={c.specs} hint={c.specsHint} error={errors.specs}>
        <Textarea
          id={fieldId('specs')}
          rows={3}
          placeholder={c.specsPlaceholder}
          aria-invalid={!!errors.specs}
          aria-describedby={d.specs}
          className="min-h-24"
          {...fields.specs}
        />
      </Field>
      {alert && (
        <p role="alert" className="text-sm font-semibold text-destructive">
          {alert}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" aria-disabled={state === 'saving'}>
          {state === 'saving' ? c.saving : editing ? c.update : c.submit}
        </Button>
        {editing && (
          <Button type="button" variant="secondary" onClick={onCancelEdit}>
            {c.cancelEdit}
          </Button>
        )}
      </div>
    </form>
  )
}
