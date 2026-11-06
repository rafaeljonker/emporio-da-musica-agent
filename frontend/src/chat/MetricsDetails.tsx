import { Gauge } from 'lucide-react'
import type { ReactNode } from 'react'
import { copy } from '@/copy'
import { formatBRL, formatSeconds, historyLine, summary, totalCost, type TurnRecord } from './metrics'

const int = new Intl.NumberFormat('pt-BR')
const secs = (ms: number, digits: number) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(ms / 1000)

interface Props {
  turns: TurnRecord[]
  /** The measured cold start in seconds, once warm-up reached ready (not provider_api). */
  warmupSeconds: number | null
  local: boolean
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <p className="mt-2 first:mt-0">
        <strong>{title}</strong>
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 [&_dd]:tnum [&_dt]:text-muted-foreground">
        {children}
      </dl>
    </>
  )
}

/** Design option A: a collapsed native disclosure; not a live region, the summary updates in place. */
export function MetricsDetails({ turns, warmupSeconds, local }: Props) {
  const last = turns.at(-1)?.metrics
  const lastScreen = turns.at(-1)?.screenMs ?? 0
  const m = copy.metrics
  return (
    <details className="open:basis-full">
      <summary className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 text-base font-semibold text-muted-foreground tnum">
        <Gauge size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
        {summary(turns)}
      </summary>
      <div className="max-h-[40dvh] overflow-y-auto rounded-md border border-border bg-popover px-3 py-2 text-sm shadow-sm md:max-h-none">
        {last && (
          <Block title={m.last}>
            <dt>{m.tokens}</dt>
            <dd>{m.tokensValue(int.format(last.input_tokens), int.format(last.output_tokens))}</dd>
            <dt>{m.time}</dt>
            <dd>
              {m.timeValue(formatSeconds(last.ms_model), formatSeconds(lastScreen))}
              <br />
              <span className="text-muted-foreground">
                {m.breakdown(secs(last.ms_guard, 2), secs(last.ms_llm, 1), secs(last.ms_tools, 2))}
              </span>
            </dd>
            <dt>{m.cost}</dt>
            <dd>
              {local ? (
                m.local
              ) : (
                <>
                  {formatBRL(last.cost_brl)}
                  <br />
                  <span className="text-muted-foreground">{last.cost_basis}</span>
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
    </details>
  )
}
