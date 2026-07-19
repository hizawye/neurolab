import type { ReactNode } from 'react';

/* The vocabulary this interface is built from.

   Every number NeuroLab shows is one of two kinds of claim, and the platform's
   whole design rests on never letting them blur: a *measurement* somebody made
   in a laboratory, or a *prediction* a method produced and which can be wrong.
   These components are the only sanctioned way to render either, so the
   distinction cannot quietly be dropped in one table and kept in another. */

type Tone = 'measured' | 'predicted';

/** Filled square for measurement, hollow square for prediction. The fill is the
 *  secondary encoding that lets the pair survive colour-vision deficiency. */
export function EvidenceMark({ tone }: { tone: Tone }) {
  return (
    <span
      aria-hidden
      className={[
        'inline-block h-2 w-2 shrink-0 rounded-[1px]',
        tone === 'measured'
          ? 'bg-measured'
          : 'border-[1.5px] border-predicted bg-transparent',
      ].join(' ')}
    />
  );
}

export function EvidenceKey({ className = '' }: { className?: string }) {
  return (
    <dl className={`flex flex-wrap items-center gap-x-4 gap-y-1 text-xs ${className}`}>
      <div className="flex items-center gap-1.5">
        <EvidenceMark tone="measured" />
        <dt className="font-medium text-measured-ink">Measured</dt>
        <dd className="text-muted">observed in an assay</dd>
      </div>
      <div className="flex items-center gap-1.5">
        <EvidenceMark tone="predicted" />
        <dt className="font-medium text-predicted-ink">Predicted</dt>
        <dd className="text-muted">a method's estimate, can be wrong</dd>
      </div>
    </dl>
  );
}

/** A measured quantity: filled mark, blue ink, and its provenance beneath it. */
export function MeasuredValue({
  value,
  detail,
}: {
  value: ReactNode;
  detail?: ReactNode;
}) {
  return (
    <div>
      <span className="inline-flex items-baseline gap-1.5">
        <span className="translate-y-[-2px]">
          <EvidenceMark tone="measured" />
        </span>
        <span className="tnum font-semibold text-ink">{value}</span>
      </span>
      {detail ? <span className="mt-0.5 block text-xs text-muted">{detail}</span> : null}
    </div>
  );
}

/** A predicted quantity: hollow mark, magenta ink, and a band label so the
 *  reader is never asked to interpret a bare number as a probability. */
export function PredictedValue({
  value,
  band,
  detail,
}: {
  value: ReactNode;
  band?: string;
  detail?: ReactNode;
}) {
  return (
    <div>
      <span className="inline-flex items-baseline gap-1.5">
        <span className="translate-y-[-2px]">
          <EvidenceMark tone="predicted" />
        </span>
        <span className="tnum font-semibold text-ink">{value}</span>
        {band ? (
          <span className="rounded border border-predicted px-1.5 py-px text-[11px] font-medium text-predicted-ink">
            {band}
          </span>
        ) : null}
      </span>
      {detail ? <span className="mt-0.5 block text-xs text-muted">{detail}</span> : null}
    </div>
  );
}

export function NoValue({ label = 'none' }: { label?: string }) {
  return <span className="text-xs text-muted">{label}</span>;
}

/* An interval, drawn as an interval.

   A point estimate printed alone invites more confidence than the evidence
   supports. Each bar shows the span; `kind` states what the span actually is,
   because a 95% bootstrap interval and a spread across three targets are
   different claims and the old interface rendered both as "a–b". */
export function IntervalBar({
  label,
  kind,
  lo,
  hi,
  point,
  domainMin = 0,
  domainMax = 1,
  tone = 'predicted',
  format = (n: number) => n.toFixed(3),
}: {
  label: string;
  kind: string;
  lo: number;
  hi: number;
  point?: number;
  domainMin?: number;
  domainMax?: number;
  tone?: Tone;
  format?: (n: number) => string;
}) {
  const span = domainMax - domainMin || 1;
  const pct = (n: number) => ((n - domainMin) / span) * 100;
  const left = Math.max(0, Math.min(100, pct(lo)));
  const right = Math.max(0, Math.min(100, pct(hi)));
  const width = Math.max(1.5, right - left);
  const barColor = tone === 'measured' ? 'bg-measured' : 'bg-predicted';

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs font-medium text-ink-2">{label}</span>
        <span className="tnum text-xs font-semibold text-ink">
          {format(lo)}–{format(hi)}
        </span>
      </div>
      <div
        className="relative mt-1.5 h-2 rounded-full bg-line"
        role="img"
        aria-label={`${label}: ${kind} from ${format(lo)} to ${format(hi)}`}
      >
        <div
          className={`absolute inset-y-0 rounded-full ${barColor}`}
          style={{ left: `${left}%`, width: `${width}%` }}
        />
        {point !== undefined ? (
          <div
            className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink ring-2 ring-surface"
            style={{ left: `${Math.max(0, Math.min(100, pct(point)))}%` }}
          />
        ) : null}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-muted">
        <span>{kind}</span>
        <span className="tnum">
          {format(domainMin)}–{format(domainMax)}
        </span>
      </div>
    </div>
  );
}

/* Layout primitives, so every page frames its content the same way. */

export function Panel({
  title,
  hint,
  actions,
  children,
  flush = false,
}: {
  title?: ReactNode;
  hint?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  flush?: boolean;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-surface">
      {title ? (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-ink">{title}</h2>
            {hint ? <p className="mt-0.5 max-w-2xl text-xs text-muted">{hint}</p> : null}
          </div>
          {actions}
        </header>
      ) : null}
      <div className={flush ? '' : 'p-4'}>{children}</div>
    </section>
  );
}

/** A caveat, a failure, or a confirmation — status colour always with a label,
 *  never carrying the meaning on its own. */
export function Callout({
  tone,
  title,
  children,
}: {
  tone: 'warn' | 'critical' | 'good';
  title: string;
  children?: ReactNode;
}) {
  const styles = {
    warn: 'border-warn/50 bg-warn-wash text-warn-ink',
    critical: 'border-critical/50 bg-critical-wash text-critical-ink',
    good: 'border-good/50 bg-transparent text-good-ink',
  }[tone];

  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${styles}`} role="status">
      <p className="font-semibold">{title}</p>
      {children ? <div className="mt-1 text-ink-2">{children}</div> : null}
    </div>
  );
}

export function WarningList({
  warnings,
}: {
  warnings: { stage: string; message: string }[];
}) {
  if (!warnings.length) return null;
  return (
    <Callout tone="warn" title={`${warnings.length} warning${warnings.length > 1 ? 's' : ''}`}>
      <ul className="space-y-1">
        {warnings.map((warning) => (
          <li key={`${warning.stage}-${warning.message}`}>
            <span className="font-mono text-xs text-warn-ink">{warning.stage}</span>{' '}
            {warning.message}
          </li>
        ))}
      </ul>
    </Callout>
  );
}

/** Nothing is shown without a route back to where it came from. */
export function SourceLink({
  href,
  children,
}: {
  href?: string | null;
  children: ReactNode;
}) {
  if (!href) return <>{children}</>;
  return (
    <a
      className="underline decoration-line-strong underline-offset-2 transition-colors hover:decoration-current"
      href={href}
      rel="noreferrer"
      target="_blank"
    >
      {children}
    </a>
  );
}
