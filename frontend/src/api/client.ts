import { createParser } from 'eventsource-parser'
import type { Category, ChatEvent, DemoCustomer, Me, Product, ProductBody, WarmExpected, WarmStatus } from './types'

/** Any 401 on an authenticated route: the session cookie is gone or expired. */
export class SessionExpired extends Error {}
/** 401 on login itself: there is no session yet, the credentials are wrong. */
export class InvalidCredentials extends Error {}

export class HttpError extends Error {
  readonly status: number
  /** The API's `{"detail": "<code>"}`, when it is a string (e.g. `catalog_full`). */
  readonly detail?: string
  constructor(status: number, detail?: string) {
    super(`HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

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

function check(res: Response): Response {
  if (res.status === 401) throw new SessionExpired()
  if (!res.ok) throw new HttpError(res.status)
  return res
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await send(method, path, body)
  if (!res.ok && res.status !== 401) {
    const json: unknown = await res.json().catch(() => null)
    const detail = (json as { detail?: unknown } | null)?.detail
    throw new HttpError(res.status, typeof detail === 'string' ? detail : undefined)
  }
  return (await check(res).json()) as T
}

export async function login(email: string, password: string): Promise<WarmStatus> {
  const res = await send('POST', '/api/auth/login', { email, password })
  if (res.status === 401) throw new InvalidCredentials()
  const { warm } = (await check(res).json()) as { warm: WarmStatus }
  return warm
}

export async function logout(): Promise<void> {
  check(await send('POST', '/api/auth/logout'))
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

/** POSTs one message and reports each SSE event; no reconnect (a dropped turn is an error). */
export async function streamChat(
  text: string,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = check(await send('POST', '/api/chat', { text }, signal))
  const parser = createParser({
    onEvent: (m) => onEvent({ type: m.event, ...JSON.parse(m.data) } as ChatEvent),
  })
  const reader = res.body!.pipeThrough(new TextDecoderStream()).getReader()
  for (;;) {
    const { done, value } = await reader.read()
    if (done) return
    parser.feed(value)
  }
}
