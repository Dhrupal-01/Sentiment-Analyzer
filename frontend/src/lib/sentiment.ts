import type { HeadlineItem, HeadlinePredictionItem } from '../api/types';

export type Label = 'negative' | 'neutral' | 'positive';

/** Order used everywhere a distribution is drawn: cold to warm, left to right. */
export const LABELS: readonly Label[] = ['negative', 'neutral', 'positive'];

export const LABEL_TEXT: Record<Label, string> = {
  negative: 'Negative',
  neutral: 'Neutral',
  positive: 'Positive',
};

export function asLabel(raw: string | null | undefined): Label {
  const value = (raw ?? '').trim().toLowerCase();
  if (value === 'positive' || value === 'negative') return value;
  return 'neutral';
}

/**
 * The API returns a headline's stored predictions as a list, one entry per model.
 * Look a model up by name instead of indexing the list like a dictionary.
 */
export function predictionFor(
  headline: HeadlineItem,
  model: string
): HeadlinePredictionItem | undefined {
  return (headline.predictions ?? []).find((p) => p.model_name === model);
}

/** Model names that appear in a set of headlines' stored predictions. */
export function modelsWithPredictions(headlines: HeadlineItem[]): string[] {
  const names = new Set<string>();
  for (const h of headlines) for (const p of h.predictions ?? []) names.add(p.model_name);
  return [...names].sort();
}

const MINUS = '−';

/** Signed score with a typographic minus, e.g. "+0.42", "−0.07", "0.00". */
export function formatScore(score: number, digits = 2): string {
  const rounded = Number(score.toFixed(digits));
  if (rounded === 0) return (0).toFixed(digits);
  const body = Math.abs(rounded).toFixed(digits);
  return rounded > 0 ? `+${body}` : `${MINUS}${body}`;
}

export function formatPercent(value: number, digits = 0): string {
  return `${value.toFixed(digits)}%`;
}

const MODEL_DISPLAY: Record<string, string> = {
  vader: 'VADER',
  roberta: 'RoBERTa',
  finbert: 'FinBERT',
  fine_tuned: 'Fine-tuned DistilRoBERTa',
};

export function modelDisplayName(model: string): string {
  return MODEL_DISPLAY[model] ?? model;
}

export function compareByScore(a: number, b: number): number {
  return a - b;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return 'Date unknown';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Date unknown';
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatShortDate(day: string): string {
  const date = new Date(`${day}T00:00:00`);
  if (Number.isNaN(date.getTime())) return day;
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}
