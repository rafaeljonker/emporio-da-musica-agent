import { createParser } from 'eventsource-parser'
import type { Category, ChatEvent, DemoCustomer, Me, Product, ProductBody, WarmExpected, WarmStatus } from './apiTypes'
import { notifySessionExpired } from './session'
import { err, ok, type Result } from '@/shared/result'

/** The API's `detail` codes (emporio.api), byte-identical. */
const CODES = [
  'unauthenticated',
  'invalid_credentials',
  'too_many_attempts',
  'json_required',
  'too_many_messages',
  'turn_in_progress',
  'too_many_switches',
  'unknown_customer',
  'unknown_category',
  'not_found',
  'catalog_full',
  'catalog_unavailable',
  'name_taken_by_store',
  'promo_claim',
  'too_many_writes',
] as const

/** A backend code, or: `invalid_fields` (FastAPI's 422 list), `network` (no response), `unknown`. */
export type ApiErrorCode = (typeof CODES)[number] | 'invalid_fields' | 'network' | 'unknown'

/** `status` is null when no response arrived (offline, aborted). */
export interface ApiError {
  code: ApiErrorCode
  status: number | null
}

const LOGIN = '/api/auth/login'
const NETWORK: ApiError = { code: 'network', status: null }
const KNOWN: ReadonlySet<string> = new Set(CODES)
const isCode = (detail: unknown): detail is (typeof CODES)[number] => typeof detail === 'string' && KNOWN.has(detail)

function send(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<Response> {
  // Bodiless requests send no JSON content type (the backend 415s only bodies that are not JSON).
  return fetch(path, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
}

async function failure(res: Response, path: string): Promise<ApiError> {
  // A 401 on login is wrong credentials; anywhere else the session cookie is gone or expired.
  if (res.status === 401) {
    if (path === LOGIN) return { code: 'invalid_credentials', status: 401 }
    notifySessionExpired()
    return { code: 'unauthenticated', status: 401 }
  }
  const json: unknown = await res.json().catch(() => null)
  const detail = typeof json === 'object' && json !== null && 'detail' in json ? json.detail : undefined
  const code = Array.isArray(detail) ? 'invalid_fields' : isCode(detail) ? detail : 'unknown'
  return { code, status: res.status }
}

/** Never throws: a network failure, an error status or an unreadable body come back as an ApiError. */
async function exchange(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<Result<Response, ApiError>> {
  let res: Response
  try {
    res = await send(method, path, body, signal)
  } catch {
    return err(NETWORK)
  }
  return res.ok ? ok(res) : err(await failure(res, path))
}

async function call<T>(method: string, path: string, body?: unknown): Promise<Result<T, ApiError>> {
  const res = await exchange(method, path, body)
  if (!res.ok) return res
  try {
    return ok((await res.data.json()) as T)
  } catch {
    return err({ code: 'unknown', status: res.data.status })
  }
}

export async function login(email: string, password: string): Promise<Result<WarmStatus, ApiError>> {
  const res = await call<{ warm: WarmStatus }>('POST', LOGIN, { email, password })
  return res.ok ? ok(res.data.warm) : res
}

export async function logout(): Promise<Result<void, ApiError>> {
  const res = await exchange('POST', '/api/auth/logout')
  return res.ok ? ok(undefined) : res
}

export const me = () => call<Me>('GET', '/api/auth/me')
export const customers = () => call<DemoCustomer[]>('GET', '/api/customers')
export const setIdentity = (customerId: number | null) =>
  call<{ customer_id: number | null }>('PUT', '/api/identity', { customer_id: customerId })
export const warmStatus = () => call<WarmStatus>('GET', '/api/warm/status')
export const startWarm = () => call<WarmStatus>('POST', '/api/warm')
export const warmExpected = () => call<WarmExpected>('GET', '/api/warm/expected')
export const catalogCategories = () => call<Category[]>('GET', '/api/catalog/categories')
export const myProducts = () => call<Product[]>('GET', '/api/catalog/products/mine')
export const createProduct = (body: ProductBody) => call<Product>('POST', '/api/catalog/products', body)
export const updateProduct = (id: number, body: ProductBody) =>
  call<Product>('PUT', `/api/catalog/products/${id}`, body)

/**
 * POSTs one message and reports each SSE event; no reconnect. A refused request (409, 429), a
 * dropped stream or a bad frame is an error value; the caller checks `signal.aborted` first.
 */
export async function streamChat(
  text: string,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<Result<void, ApiError>> {
  const res = await exchange('POST', '/api/chat', { text }, signal)
  if (!res.ok) return res
  const stream = res.data.body
  if (!stream) return err({ code: 'unknown', status: res.data.status })
  const parser = createParser({
    onEvent: (m) => onEvent({ type: m.event, ...JSON.parse(m.data) } as ChatEvent),
  })
  try {
    const reader = stream.pipeThrough(new TextDecoderStream()).getReader()
    for (;;) {
      const { done, value } = await reader.read()
      if (done) return ok(undefined)
      parser.feed(value)
    }
  } catch {
    return err(NETWORK)
  }
}
