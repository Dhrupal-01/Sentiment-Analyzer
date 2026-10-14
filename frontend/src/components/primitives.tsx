import { useEffect, useRef, useState, type ReactNode } from 'react';
import { LABEL_TEXT, LABELS, formatPercent, formatScore, type Label } from '../lib/sentiment';

export function SentimentLabel({ label }: { label: Label }) {
  return (
    <span className="label" data-label={label}>
      {LABEL_TEXT[label]}
    </span>
  );
}

/**
 * A score drawn as a position on the −1 … +1 line. The filled stretch runs from zero to the
 * score, so direction and strength read at a glance without relying on colour alone.
 */
export function ValenceMarker({
  score,
  label,
  width = 140,
}: {
  score: number;
  label: Label;
  width?: number;
}) {
  const pad = 6;
  const clamped = Math.max(-1, Math.min(1, score));
  const x = (value: number) => pad + ((value + 1) / 2) * (width - pad * 2);
  return (
    <svg
      className="valence"
      width={width}
      height={14}
      viewBox={`0 0 ${width} 14`}
      role="img"
      aria-label={`Score ${formatScore(score)} on a scale from −1 to +1`}
    >
      <line className="valence__track" x1={x(-1)} x2={x(1)} y1={7} y2={7} />
      <line className="valence__zero" x1={x(0)} x2={x(0)} y1={2} y2={12} />
      <line
        className="valence__fill"
        data-label={label}
        x1={x(0)}
        x2={x(clamped)}
        y1={7}
        y2={7}
        strokeWidth={3}
        strokeLinecap="round"
      />
      <circle className="valence__dot" data-label={label} cx={x(clamped)} cy={7} r={5} />
    </svg>
  );
}

export interface DistributionCounts {
  negative: number;
  neutral: number;
  positive: number;
}

export function DistributionBar({
  counts,
  tone = 'band',
}: {
  counts: DistributionCounts;
  tone?: 'band' | 'light';
}) {
  const total = counts.negative + counts.neutral + counts.positive;
  return (
    <div className={tone === 'light' ? 'dist dist--light' : 'dist'}>
      <div className="dist__bar" role="img" aria-label={describeCounts(counts)}>
        {LABELS.map((label) =>
          counts[label] > 0 ? (
            <span
              key={label}
              className="dist__seg"
              data-label={label}
              style={{ flexGrow: counts[label] }}
            />
          ) : null
        )}
      </div>
      <div className="dist__legend num">
        {LABELS.map((label) => (
          <span key={label}>
            <strong>{total > 0 ? formatPercent((counts[label] / total) * 100) : '0%'}</strong>{' '}
            {LABEL_TEXT[label].toLowerCase()} ({counts[label]})
          </span>
        ))}
      </div>
    </div>
  );
}

function describeCounts(counts: DistributionCounts): string {
  return `${counts.negative} negative, ${counts.neutral} neutral, ${counts.positive} positive`;
}

export function Notice({
  title,
  children,
  tone = 'info',
  actions,
}: {
  title: string;
  children?: ReactNode;
  tone?: 'info' | 'error';
  actions?: ReactNode;
}) {
  return (
    <div
      className={tone === 'error' ? 'notice notice--error' : 'notice'}
      role={tone === 'error' ? 'alert' : undefined}
    >
      <h3>{title}</h3>
      {children ? <p>{children}</p> : null}
      {actions ? <div className="notice__actions">{actions}</div> : null}
    </div>
  );
}

export function Skeleton({ height, width = '100%' }: { height: number; width?: number | string }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/** Width of an element, kept current with a ResizeObserver, for SVG charts. */
export function useElementWidth<T extends HTMLElement>(fallback = 720) {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => {
      const next = Math.round(element.getBoundingClientRect().width);
      if (next > 0) setWidth(next);
    };
    update();
    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}
