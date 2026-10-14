import { useState } from 'react';
import type { DailyTrendItem } from '../api/types';
import { formatScore, formatShortDate } from '../lib/sentiment';
import { useElementWidth } from './primitives';

/**
 * Daily average score as a line over a strip of daily headline counts. The score axis is
 * symmetric around zero so a drift towards negative or positive is never exaggerated.
 */
export function TrendChart({ series }: { series: DailyTrendItem[] }) {
  const { ref, width } = useElementWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);

  const left = 44;
  const right = 12;
  const lineTop = 10;
  const lineHeight = 170;
  const gap = 18;
  const barHeight = 48;
  const height = lineTop + lineHeight + gap + barHeight + 26;
  const plotWidth = Math.max(10, width - left - right);

  // Symmetric domain in steps of 0.2 so the half-way gridlines land on one-decimal values.
  const extent = Math.max(0.2, ...series.map((d) => Math.abs(d.average_score)));
  const domain = Math.min(1, Math.ceil(extent * 5 - 1e-9) / 5);
  const maxVolume = Math.max(1, ...series.map((d) => d.headline_volume));

  const step = series.length > 1 ? plotWidth / (series.length - 1) : 0;
  const xAt = (i: number) => (series.length > 1 ? left + i * step : left + plotWidth / 2);
  const yAt = (score: number) => lineTop + ((domain - score) / (domain * 2)) * lineHeight;
  const barTop = lineTop + lineHeight + gap;
  const barWidth = Math.max(2, Math.min(18, (plotWidth / Math.max(1, series.length)) * 0.6));

  const path = series
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(1)},${yAt(d.average_score).toFixed(1)}`)
    .join(' ');
  const ticks = [domain, domain / 2, 0, -domain / 2, -domain];
  const labelEvery = Math.max(
    1,
    Math.ceil(series.length / Math.max(2, Math.floor(plotWidth / 70)))
  );
  const shown = active !== null ? series[active] : series[series.length - 1];

  const onMove = (clientX: number, target: SVGSVGElement) => {
    if (series.length === 0) return;
    const box = target.getBoundingClientRect();
    const relative = clientX - box.left;
    const index = series.length > 1 ? Math.round((relative - left) / step) : 0;
    setActive(Math.max(0, Math.min(series.length - 1, index)));
  };

  return (
    <div className="trend" ref={ref}>
      <div className="trend__readout num" aria-live="polite">
        {shown ? (
          <>
            <span>
              <strong>{formatShortDate(shown.date)}</strong>
            </span>
            <span>
              Average <strong>{formatScore(shown.average_score)}</strong>
            </span>
            <span>
              <strong>{shown.headline_volume}</strong>{' '}
              {shown.headline_volume === 1 ? 'headline' : 'headlines'}
            </span>
            <span>
              {shown.negative_count} negative, {shown.neutral_count} neutral, {shown.positive_count}{' '}
              positive
            </span>
          </>
        ) : null}
      </div>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Daily average sentiment over ${series.length} days`}
        onMouseMove={(e) => onMove(e.clientX, e.currentTarget)}
        onMouseLeave={() => setActive(null)}
      >
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              className={tick === 0 ? 'trend__zero' : 'trend__grid'}
              x1={left}
              x2={left + plotWidth}
              y1={yAt(tick)}
              y2={yAt(tick)}
            />
            <text className="trend__tick" x={left - 8} y={yAt(tick) + 4} textAnchor="end">
              {tick === 0 ? '0' : formatScore(tick, 1)}
            </text>
          </g>
        ))}
        {series.map((d, i) => {
          const h = (d.headline_volume / maxVolume) * barHeight;
          return (
            <rect
              key={d.date}
              className="trend__bar"
              data-active={i === active}
              x={xAt(i) - barWidth / 2}
              y={barTop + barHeight - h}
              width={barWidth}
              height={Math.max(1, h)}
              rx={2}
            />
          );
        })}
        <text className="trend__tick" x={left - 8} y={barTop + 12} textAnchor="end">
          {maxVolume}
        </text>
        {active !== null ? (
          <line
            className="trend__cross"
            x1={xAt(active)}
            x2={xAt(active)}
            y1={lineTop}
            y2={barTop + barHeight}
          />
        ) : null}
        {series.length > 1 ? <path className="trend__line" d={path} /> : null}
        {series.map((d, i) => (
          <circle
            key={d.date}
            cx={xAt(i)}
            cy={yAt(d.average_score)}
            r={i === active ? 5 : 3}
            fill={
              d.average_score > 0.05
                ? 'var(--warm)'
                : d.average_score < -0.05
                  ? 'var(--cold)'
                  : 'var(--neutral)'
            }
            stroke="var(--surface)"
            strokeWidth={1.5}
          />
        ))}
        {series.map((d, i) =>
          (i % labelEvery === 0 &&
            (i === series.length - 1 || series.length - 1 - i >= labelEvery)) ||
          i === series.length - 1 ? (
            <text
              key={d.date}
              className="trend__tick"
              x={xAt(i)}
              y={height - 6}
              textAnchor={
                series.length === 1
                  ? 'middle'
                  : i === 0
                    ? 'start'
                    : i === series.length - 1
                      ? 'end'
                      : 'middle'
              }
            >
              {formatShortDate(d.date)}
            </text>
          ) : null
        )}
      </svg>
    </div>
  );
}
