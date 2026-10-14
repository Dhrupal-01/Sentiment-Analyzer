import type { HeadlineItem } from '../api/types';
import { LABELS, asLabel, predictionFor, type Label } from './sentiment';

export interface PairAgreement {
  modelA: string;
  modelB: string;
  /** Headlines that both models have scored. */
  overlap: number;
  agreed: number;
  /** Share of overlapping headlines with the same label, 0–1, or null without overlap. */
  rate: number | null;
  /** Cohen's kappa, or null when it is undefined (no overlap or a single shared label). */
  kappa: number | null;
}

export function pairAgreement(
  headlines: HeadlineItem[],
  modelA: string,
  modelB: string
): PairAgreement {
  const countsA: Record<Label, number> = { negative: 0, neutral: 0, positive: 0 };
  const countsB: Record<Label, number> = { negative: 0, neutral: 0, positive: 0 };
  let overlap = 0;
  let agreed = 0;

  for (const headline of headlines) {
    const a = predictionFor(headline, modelA);
    const b = predictionFor(headline, modelB);
    if (!a || !b) continue;
    const la = asLabel(a.label);
    const lb = asLabel(b.label);
    overlap += 1;
    countsA[la] += 1;
    countsB[lb] += 1;
    if (la === lb) agreed += 1;
  }

  if (overlap === 0) return { modelA, modelB, overlap, agreed, rate: null, kappa: null };

  const observed = agreed / overlap;
  const expected = LABELS.reduce(
    (sum, label) => sum + (countsA[label] / overlap) * (countsB[label] / overlap),
    0
  );
  const kappa = expected >= 1 ? null : (observed - expected) / (1 - expected);
  return { modelA, modelB, overlap, agreed, rate: observed, kappa };
}

export interface Disagreement {
  headline: HeadlineItem;
  labelA: Label;
  labelB: Label;
  scoreA: number;
  scoreB: number;
}

/** Headlines the two models label differently, largest score gap first. */
export function disagreements(
  headlines: HeadlineItem[],
  modelA: string,
  modelB: string
): Disagreement[] {
  const rows: Disagreement[] = [];
  for (const headline of headlines) {
    const a = predictionFor(headline, modelA);
    const b = predictionFor(headline, modelB);
    if (!a || !b) continue;
    const labelA = asLabel(a.label);
    const labelB = asLabel(b.label);
    if (labelA === labelB) continue;
    rows.push({ headline, labelA, labelB, scoreA: a.score, scoreB: b.score });
  }
  return rows.sort((x, y) => Math.abs(y.scoreA - y.scoreB) - Math.abs(x.scoreA - x.scoreB));
}
