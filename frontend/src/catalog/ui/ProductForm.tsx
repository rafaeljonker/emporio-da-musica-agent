import type { Category, ProductStatus } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { copy } from '@/copy'
import { fieldId } from '../domain/catalog'
import { Field } from './Field'
import { useProductForm, type ProductFormProps } from './useProductForm'

const c = copy.catalog
const STATUSES = Object.keys(c.statuses) as ProductStatus[]
const SELECT_CLASS =
  'h-11 w-full rounded-md bg-popover px-3 text-base text-foreground focus-visible:border-input focus-visible:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring data-[size=default]:h-11 aria-invalid:border-destructive'
const ITEM_CLASS = 'min-h-11 py-2 pl-3 text-base'

interface Props extends ProductFormProps {
  categories: Category[]
}

/** The add/edit form of the Catálogo dialog. */
export function ProductForm({ categories, ...props }: Props) {
  const vm = useProductForm(props)
  const d = vm.ariaDescribedBy

  return (
    <form noValidate onSubmit={vm.onSubmit} aria-label={props.editing ? c.editTitle : c.title} className="flex flex-col gap-4">
      <Field field="name" label={c.name} error={vm.errors.name}>
        <Input
          id={fieldId('name')}
          value={vm.fields.name}
          maxLength={120}
          autoComplete="off"
          aria-invalid={!!vm.errors.name}
          aria-describedby={d.name}
          onChange={vm.onChange.name}
        />
      </Field>
      <Field field="categoryId" label={c.category} error={vm.errors.categoryId}>
        <Select value={vm.fields.categoryId} onValueChange={vm.onChange.categoryId}>
          <SelectTrigger
            id={fieldId('categoryId')}
            aria-invalid={!!vm.errors.categoryId}
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
      </Field>
      <Field field="description" label={c.descriptionLabel} hint={c.descriptionHint} error={vm.errors.description}>
        <Textarea
          id={fieldId('description')}
          value={vm.fields.description}
          rows={2}
          maxLength={2000}
          aria-invalid={!!vm.errors.description}
          aria-describedby={d.description}
          onChange={vm.onChange.description}
          className="min-h-20"
        />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field field="price" label={c.price} error={vm.errors.price}>
          <Input
            id={fieldId('price')}
            inputMode="decimal"
            placeholder="0,00"
            autoComplete="off"
            value={vm.fields.price}
            aria-invalid={!!vm.errors.price}
            aria-describedby={d.price}
            onChange={vm.onChange.price}
            onBlur={vm.onPriceBlur}
            className="tnum"
          />
        </Field>
        <Field field="stock" label={c.stock} error={vm.errors.stock}>
          <Input
            id={fieldId('stock')}
            type="number"
            min={0}
            max={100_000}
            step={1}
            inputMode="numeric"
            value={vm.fields.stock}
            aria-invalid={!!vm.errors.stock}
            aria-describedby={d.stock}
            onChange={vm.onChange.stock}
            className="tnum"
          />
        </Field>
      </div>
      <Field field="status" label={c.status}>
        <Select value={vm.fields.status} onValueChange={vm.onChange.status}>
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
      </Field>
      <Field field="specs" label={c.specs} hint={c.specsHint} error={vm.errors.specs}>
        <Textarea
          id={fieldId('specs')}
          value={vm.fields.specs}
          rows={3}
          placeholder={c.specsPlaceholder}
          aria-invalid={!!vm.errors.specs}
          aria-describedby={d.specs}
          onChange={vm.onChange.specs}
          className="min-h-24"
        />
      </Field>
      {vm.failure && (
        <p role="alert" className="text-sm font-semibold text-destructive">
          {vm.failure}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" aria-disabled={vm.saving}>
          {vm.saving ? c.saving : props.editing ? c.update : c.submit}
        </Button>
        {props.editing && (
          <Button type="button" variant="secondary" onClick={props.onCancelEdit}>
            {c.cancelEdit}
          </Button>
        )}
      </div>
    </form>
  )
}
