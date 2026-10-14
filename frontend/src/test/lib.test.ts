import { describe, expect, it } from 'vitest';
import type { HeadlineItem } from '../api/types';
import { disagreements, pairAgreement } from '../lib/agreement';
import { buildHash, parseHash } from '../lib/router';
import { formatScore, predictionFor } from '../lib/sentiment';
import { alignAttributions, strongestTokens } from '../lib/tokens';

function headline(id: number, preds: Record<string, [string, number]>): HeadlineItem {
  return {
    id,
    title: `Headline ${id}`,
    url: `https://example.com/${id}`,
    topic: 'markets',
    provider: 'gdelt',
    // The API returns predictions as a list, one entry per model.
    predictions: Object.entries(preds).map(([model_name, [label, score]]) => ({
      model_name,
      model_version: '1',
      label,
      score,
      probabilities: {},
      created_at: '2026-10-01T00:00:00Z',
    })),
  };
}

describe('predictionFor', () => {
  it('finds a model in the list-shaped predictions the API returns', () => {
    const h = headline(1, { vader: ['positive', 0.4], roberta: ['neutral', 0.02] });
    expect(predictionFor(h, 'roberta')?.label).toBe('neutral');
    expect(predictionFor(h, 'finbert')).toBeUndefined();
  });
});

describe('pairAgreement', () => {
  const items = [
    headline(1, { a: ['positive', 0.5], b: ['positive', 0.6] }),
    headline(2, { a: ['negative', -0.5], b: ['negative', -0.4] }),
    headline(3, { a: ['neutral', 0], b: ['positive', 0.3] }),
    headline(4, { a: ['neutral', 0], b: ['neutral', 0.01] }),
    headline(5, { a: ['positive', 0.2] }),
  ];

  it('counts only headlines both models scored', () => {
    const result = pairAgreement(items, 'a', 'b');
    expect(result.overlap).toBe(4);
    expect(result.agreed).toBe(3);
    expect(result.rate).toBeCloseTo(0.75);
  });

  it("computes Cohen's kappa from the label marginals", () => {
    // p_o = 0.75; p_e = (1/4*2/4) + (2/4*1/4) + (1/4*1/4) = 0.3125
    const result = pairAgreement(items, 'a', 'b');
    expect(result.kappa).toBeCloseTo((0.75 - 0.3125) / (1 - 0.3125), 5);
  });

  it('returns nulls when the models share no headlines', () => {
    const result = pairAgreement(items, 'a', 'missing');
    expect(result.rate).toBeNull();
    expect(result.kappa).toBeNull();
  });

  it('lists disagreements with the largest score gap first', () => {
    const extra = [...items, headline(6, { a: ['negative', -0.9], b: ['positive', 0.8] })];
    const rows = disagreements(extra, 'a', 'b');
    expect(rows.map((r) => r.headline.id)).toEqual([6, 3]);
  });
});

describe('alignAttributions', () => {
  it('keeps the original spacing and punctuation around scored tokens', () => {
    const text = 'Stocks fall, but recovery is near';
    const segments = alignAttributions(text, [
      { token: 'Stocks', weight: 0 },
      { token: 'fall', weight: -0.4 },
      { token: ',', weight: 0 },
      { token: 'recovery', weight: 0.3 },
    ]);
    expect(segments.map((s) => s.text).join('')).toBe(text);
    expect(segments.find((s) => s.text === 'fall')?.weight).toBe(-0.4);
  });

  it('appends tokens it cannot place instead of dropping them', () => {
    const segments = alignAttributions('Good news', [{ token: 'Ġnews', weight: 0.2 }]);
    expect(segments.some((s) => s.text === 'Ġnews' && s.weight === 0.2)).toBe(true);
  });

  it('ranks the strongest words and skips punctuation and zero weights', () => {
    const top = strongestTokens(
      [
        { token: 'a', weight: 0 },
        { token: '-', weight: 0.9 },
        { token: 'bad', weight: -0.5 },
        { token: 'not', weight: 0.7 },
      ],
      5
    );
    expect(top.map((t) => t.token)).toEqual(['not', 'bad']);
  });
});

describe('formatScore', () => {
  it('uses a typographic minus and a plus sign', () => {
    expect(formatScore(-0.071)).toBe('−0.07');
    expect(formatScore(0.42)).toBe('+0.42');
    expect(formatScore(-0.001)).toBe('0.00');
  });
});

describe('hash routes', () => {
  it('round-trips a page and its parameters', () => {
    const hash = buildHash('compare', { topic: 3, a: 'vader', b: undefined });
    expect(hash).toBe('#/compare?topic=3&a=vader');
    const route = parseHash(hash);
    expect(route.page).toBe('compare');
    expect(route.params.get('topic')).toBe('3');
  });

  it('falls back to the headlines page for unknown paths', () => {
    expect(parseHash('#/nope').page).toBe('headlines');
    expect(parseHash('').page).toBe('headlines');
  });
});
