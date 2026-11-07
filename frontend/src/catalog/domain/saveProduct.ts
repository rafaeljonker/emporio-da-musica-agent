import { createProduct, updateProduct } from '@/api/client'
import type { Product, ProductBody } from '@/api/types'

/** Updates `editing` when given, else creates a product. */
export const saveProduct = (body: ProductBody, editing: Product | null) =>
  editing ? updateProduct(editing.id, body) : createProduct(body)
