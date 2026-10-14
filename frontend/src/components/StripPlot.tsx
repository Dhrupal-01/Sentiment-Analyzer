import { useEffect, useMemo, useState } from 'react';
import { formatScore, type Label } from '../lib/sentiment';
import { useElementWidth } from './primitives';

export interface StripPoint {
  id: number;
  score: number;
  label: Label;
  title: string;
  outlet: string;
}

const RADIUS = 5;
const MAX_STACK = 7;

function scaleX(score: number, width: number, pad: number): number {
  const clamped = Math.max(-1, Math.min(1, score));
  return pad + ((clamped + 1) / 2) * (width - pad * 2);
}

/**
 * Every headline as a dot on the line from −1 to +1. Dots that would overlap are stacked
 * outward from the axis (a simple beeswarm), so dense regions grow taller instead of hiding
 * headlines behind each other.
 */
export function StripPlot({
  points,
  activeId,
  onSelect,
}: {
  points: StripPoint[];
  activeId?: number | null;
  onSelect: (id: number) => void;
}) {
  const { ref, width } = useElementWidth<HTMLDivElement>();
  const [settled, setSettled] = useState(false);
  const [hover, setHover] = useState<{ point: StripPoint; x: number; y: number } | null>(null);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setSettled(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const pad = 18;
  const x = (score: number) => scaleX(score, width, pad);

  const placed = useMemo(() => {
    const sorted = [...points].sort((a, b) => a.score - b.score);
    const result: { point: StripPoint; cx: number; offset: number }[] = [];
    const step = RADIUS * 2 + 1;
    // Stacks stop growing past MAX_STACK rows each side; further dots in the same spot overlap
    // inside the band so one very common score cannot stretch the whole plot.
    const limit = MAX_STACK * step;
    for (const point of sorted) {
      const cx = scaleX(point.score, width, pad);
      let offset: number | null = null;
      for (let k = 0; k <= MAX_STACK * 2; k += 1) {
        const candidate = k === 0 ? 0 : Math.ceil(k / 2) * step * (k % 2 === 1 ? -1 : 1);
        const clash = result.some(
          (other) => Math.abs(other.cx - cx) < step && Math.abs(other.offset - candidate) < step
        );
        if (!clash) {
          offset = candidate;
          break;
        }
      }
      if (offset === null) {
        const crowd = result.filter((other) => Math.abs(other.cx - cx) < step).length;
        offset = ((crowd * 7.3) % (limit * 2)) - limit;
      }
      result.push({ point, cx, offset });
    }
    return result;
  }, [points, width]);

  const spread = placed.reduce((max, p) => Math.max(max, Math.abs(p.offset)), 0);
  const half = Math.max(36, spread + RADIUS + 6);
  const top = 26;
  const axisY = top + half;
  const height = axisY + half + 28;
  const ticks = [-1, -0.5, 0, 0.5, 1];

  return (
    <div className="strip" ref={ref}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${points.length} headlines plotted by sentiment score from −1 to +1. Use the list below to open a headline.`}
      >
        <defs>
          <linearGradient id="strip-band" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="var(--band-cold)" stopOpacity="0.16" />
            <stop offset="50%" stopColor="var(--band-neutral)" stopOpacity="0.04" />
            <stop offset="100%" stopColor="var(--band-warm)" stopOpacity="0.16" />
          </linearGradient>
        </defs>
        <rect
          x={pad}
          y={axisY - half}
          width={width - pad * 2}
          height={half * 2}
          rx={8}
          fill="url(#strip-band)"
        />
        <line className="strip__axis" x1={pad} x2={width - pad} y1={axisY} y2={axisY} />
        <line className="strip__zero" x1={x(0)} x2={x(0)} y1={axisY - half} y2={axisY + half} />
        {placed.map(({ point, cx, offset }) => (
          <circle
            key={point.id}
            className="strip__dot"
            data-active={point.id === activeId}
            r={RADIUS}
            cx={0}
            cy={0}
            style={{
              transform: settled
                ? `translate(${cx}px, ${axisY + offset}px)`
                : `translate(${x(0)}px, ${axisY}px)`,
            }}
            fill={
              point.label === 'negative'
                ? 'var(--band-cold)'
                : point.label === 'positive'
                  ? 'var(--band-warm)'
                  : 'var(--band-neutral)'
            }
            onMouseEnter={() => setHover({ point, x: cx, y: axisY + offset })}
            onMouseLeave={() => setHover(null)}
            onClick={() => onSelect(point.id)}
          />
        ))}
        {ticks.map((tick) => (
          <text
            key={tick}
            className="strip__tick"
            x={x(tick)}
            y={axisY + half + 18}
            textAnchor={tick === -1 ? 'start' : tick === 1 ? 'end' : 'middle'}
          >
            {tick === 0 ? '0' : formatScore(tick, tick % 1 === 0 ? 0 : 1)}
          </text>
        ))}
        <text className="strip__end" x={pad} y={top - 10} fill="var(--band-cold)">
          Negative
        </text>
        <text
          className="strip__end"
          x={width - pad}
          y={top - 10}
          textAnchor="end"
          fill="var(--band-warm)"
        >
          Positive
        </text>
      </svg>
      {hover ? (
        <div className="strip__tooltip" style={{ left: hover.x, top: hover.y }}>
          {hover.point.title}
          <div className="strip__tooltip-meta">
            <span>{hover.point.outlet}</span>
            <span className="num">{formatScore(hover.point.score)}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
