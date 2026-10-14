import type { CSSProperties } from 'react';
import type { TokenAttributionItem } from '../api/types';
import { formatScore } from '../lib/sentiment';
import { alignAttributions, maxAbsWeight, strongestTokens } from '../lib/tokens';

/**
 * The headline itself, with each word shaded by how much it pushed the model's score:
 * warm for words that pushed it up, cold for words that pulled it down. Shading is relative
 * to the strongest word in this headline.
 */
export function TokenMarkup({
  text,
  attributions,
  compact = false,
}: {
  text: string;
  attributions: TokenAttributionItem[];
  compact?: boolean;
}) {
  const segments = alignAttributions(text, attributions);
  const max = maxAbsWeight(attributions);
  return (
    <p className={compact ? 'markup markup--compact' : 'markup'}>
      {segments.map((segment, i) => {
        if (segment.weight === null || max === 0 || Math.abs(segment.weight) < 1e-4) {
          return <span key={i}>{segment.text}</span>;
        }
        const strength = Math.min(1, Math.abs(segment.weight) / max);
        const sign = segment.weight > 0 ? 'positive' : 'negative';
        return (
          <span
            key={i}
            className="markup__token"
            data-sign={sign}
            style={{ '--strength': strength.toFixed(3) } as CSSProperties}
            title={`${segment.text}: ${formatScore(segment.weight, 3)}`}
          >
            {segment.text}
            <span className="visually-hidden"> ({formatScore(segment.weight, 3)})</span>
          </span>
        );
      })}
    </p>
  );
}

/** The strongest words as signed bars, so the explanation does not depend on colour. */
export function WeightList({
  attributions,
  count = 5,
}: {
  attributions: TokenAttributionItem[];
  count?: number;
}) {
  const strongest = strongestTokens(attributions, count);
  if (strongest.length === 0) {
    return (
      <p className="method-note">
        No single word changed this score. The model treats the headline as a whole, or none of its
        words carry sentiment for this model.
      </p>
    );
  }
  const max = Math.max(...strongest.map((t) => Math.abs(t.weight)));
  return (
    <div className="weights num" aria-label="Words that moved the score most">
      {strongest.map((token, i) => {
        const share = (Math.abs(token.weight) / max) * 50;
        const sign = token.weight > 0 ? 'positive' : 'negative';
        return (
          <div key={`${token.token}-${i}`} style={{ display: 'contents' }}>
            <span className="weights__word">{token.token}</span>
            <span className="weights__track">
              <span className="weights__bar" data-sign={sign} style={{ width: `${share}%` }} />
            </span>
            <span className="weights__value">{formatScore(token.weight, 3)}</span>
          </div>
        );
      })}
    </div>
  );
}

export function MarkupLegend() {
  return (
    <div className="legend-line">
      <span>
        <span
          className="legend-line__swatch"
          style={{ background: 'color-mix(in srgb, var(--warm) 62%, transparent)' }}
        />
        Pushed the score up
      </span>
      <span>
        <span
          className="legend-line__swatch"
          style={{ background: 'color-mix(in srgb, var(--cold) 42%, transparent)' }}
        />
        Pulled the score down
      </span>
      <span>Stronger shading means a larger effect within this headline.</span>
    </div>
  );
}

export const METHOD_OPTIONS = [
  { value: 'occlusion', label: 'Word removal' },
  { value: 'integrated_gradients', label: 'Integrated gradients' },
  { value: 'shap', label: 'SHAP' },
] as const;

export type Method = (typeof METHOD_OPTIONS)[number]['value'];

export function methodNote(method: Method, model: string): string {
  if (method === 'occlusion') {
    return 'Each word is removed in turn and the headline is scored again. A word’s weight is how much the score changes without it.';
  }
  const name = method === 'shap' ? 'SHAP' : 'Integrated gradients';
  if (model === 'vader') {
    return `VADER is a word list with rules, not a neural network, so the server cannot run ${name} on it directly and returns its approximation built from word removal instead.`;
  }
  return method === 'shap'
    ? 'SHAP averages each word’s effect over many combinations of the other words. When the SHAP library is not installed on the server, an approximation is returned instead.'
    : 'Integrated gradients follows the model’s gradients from an empty input to the headline. When Captum is not installed on the server, an approximation is returned instead.';
}
