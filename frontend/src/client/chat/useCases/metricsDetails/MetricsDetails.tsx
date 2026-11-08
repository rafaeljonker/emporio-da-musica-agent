import { Gauge } from 'lucide-react'
import type { ReactNode } from 'react'
import { copy } from '@/client/shared/lib/copy'
import { formatBRL, formatSeconds, historyLine, summary, totalCost } from '@/client/chat/domain/metrics'
import { useMetricsDetails, type MetricsDetailsProps } from './useMetricsDetails'

const int = new Intl.NumberFormat('pt-BR')
const secs = (ms: number, digits: number) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(ms / 1000)

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <p className="mt-2 first:mt-0">
        <strong>{title}</strong>
      </p>
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-0.5 [&_dd]:[overflow-wrap:anywhere] [&_dd]:tnum [&_dt]:text-muted-foreground">
        {children}
      </dl>
    </>
  )
}

/**
 * A toggle in the demo strip that opens a floating panel: it never pushes the strip or the
 * transcript (owner request, replacing the design's inline <details>). From md a popover under the
 * strip, at the column start (where the toggle sits once totals wrap it); a bottom sheet below md. Closes on Escape, outside click and the toggle; Escape returns
 * focus to the toggle. Not a live region: the toggle text updates in place.
 */
export function MetricsDetails(props: MetricsDetailsProps) {
  const { state, rootRef, toggleRef, toggle, last } = useMetricsDetails(props)
  const { turns, warmupSeconds, local } = props
  const open = state === 'open'
  const m = copy.metrics
  return (
    <span ref={rootRef}>
      <button
        ref={toggleRef}
        type="button"
        aria-expanded={open}
        aria-controls="metrics-panel"
        onClick={toggle}
        className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-md text-base font-semibold text-muted-foreground tnum"
      >
        <Gauge size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
        {summary(turns)}
      </button>
      <div
        id="metrics-panel"
        role="region"
        aria-label={m.title}
        tabIndex={0}
        hidden={!open}
        className="fixed inset-x-0 bottom-0 z-20 max-h-[70dvh] animate-arrive overflow-y-auto rounded-t-lg border border-border bg-popover px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] text-sm shadow-xl md:absolute md:inset-x-auto md:top-full md:left-4 md:bottom-auto md:mt-1 md:max-h-[min(32rem,70dvh)] md:w-96 md:max-w-[calc(100vw-2rem)] md:rounded-lg md:px-3 md:py-2 md:shadow-lg"
      >
        {last.state === 'some' && (
          <Block title={m.last}>
            <dt>{m.tokens}</dt>
            <dd>{m.tokensValue(int.format(last.metrics.input_tokens), int.format(last.metrics.output_tokens))}</dd>
            <dt>{m.time}</dt>
            <dd>
              {m.timeValue(formatSeconds(last.metrics.ms_model), formatSeconds(last.screenMs))}
              <br />
              <span className="text-muted-foreground">
                {m.breakdown(secs(last.metrics.ms_guard, 2), secs(last.metrics.ms_llm, 1), secs(last.metrics.ms_tools, 2))}
              </span>
            </dd>
            <dt>{m.cost}</dt>
            <dd>
              {local ? (
                m.local
              ) : (
                <>
                  {formatBRL(last.metrics.cost_brl)}
                  <br />
                  <span className="text-muted-foreground">{last.metrics.cost_basis}</span>
                </>
              )}
            </dd>
          </Block>
        )}
        <Block title={m.session}>
          <dt>{m.replies}</dt>
          <dd>{turns.length}</dd>
          <dt>{m.tokens}</dt>
          <dd>{int.format(turns.reduce((n, t) => n + t.metrics.input_tokens + t.metrics.output_tokens, 0))}</dd>
          <dt>{m.cost}</dt>
          <dd>{local ? m.local : formatBRL(totalCost(turns))}</dd>
          {warmupSeconds !== null && (
            <>
              <dt>{m.warmup}</dt>
              <dd>{warmupSeconds} s</dd>
            </>
          )}
        </Block>
        {turns.length > 0 && (
          <>
            <p className="mt-2">
              <strong>{m.history}</strong>
            </p>
            <ol className="tnum">
              {turns
                .map((t, i) => <li key={i}>{historyLine(i + 1, t)}</li>)
                .reverse()}
            </ol>
          </>
        )}
      </div>
    </span>
  )
}
