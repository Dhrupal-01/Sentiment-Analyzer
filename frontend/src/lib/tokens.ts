import type { TokenAttributionItem } from '../api/types';

export interface Segment {
  text: string;
  /** Attribution weight, or null for whitespace and text the explainer did not score. */
  weight: number | null;
}

/**
 * Lay the explainer's tokens back onto the original headline so spacing and punctuation
 * survive. Tokens are matched left to right; a token that cannot be found (for example a
 * sub-word piece the tokenizer rewrote) is appended at the end so no attribution is lost.
 */
export function alignAttributions(text: string, attributions: TokenAttributionItem[]): Segment[] {
  const segments: Segment[] = [];
  const unmatched: TokenAttributionItem[] = [];
  let cursor = 0;

  for (const attribution of attributions) {
    const token = attribution.token;
    if (!token) continue;
    const at = text.indexOf(token, cursor);
    if (at === -1) {
      unmatched.push(attribution);
      continue;
    }
    if (at > cursor) segments.push({ text: text.slice(cursor, at), weight: null });
    segments.push({ text: token, weight: attribution.weight });
    cursor = at + token.length;
  }

  if (cursor < text.length) segments.push({ text: text.slice(cursor), weight: null });
  for (const attribution of unmatched) {
    segments.push({ text: ' ', weight: null });
    segments.push({ text: attribution.token, weight: attribution.weight });
  }
  return segments;
}

export function maxAbsWeight(attributions: TokenAttributionItem[]): number {
  return attributions.reduce((max, a) => Math.max(max, Math.abs(a.weight)), 0);
}

/** The words that moved the score most, strongest first, ignoring zero-weight tokens. */
export function strongestTokens(
  attributions: TokenAttributionItem[],
  count = 5
): TokenAttributionItem[] {
  return attributions
    .filter((a) => Math.abs(a.weight) > 1e-4 && /\w/.test(a.token))
    .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
    .slice(0, count);
}
