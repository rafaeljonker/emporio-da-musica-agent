// fetch stubs: an SSE stream and plain JSON responses, for vi.stubGlobal('fetch', ...).
import type { ChatEvent } from '@/client/shared/lib/apiTypes'

/** A 200 `text/event-stream` Response that emits `events` in order, then closes. */
export function sseResponse(events: ChatEvent[]): Response {
  const text = events.map(({ type, ...data }) => `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`).join('')
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

/** A JSON Response; `body` undefined sends no body (a proxy error page, say). */
export const jsonResponse = (status: number, body?: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
  })
