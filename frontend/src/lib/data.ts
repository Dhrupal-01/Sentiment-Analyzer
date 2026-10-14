import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient, ApiError } from '../api/client';
import type { HeadlineItem } from '../api/types';

/** Upper bound on headlines pulled into the browser for plots and client-side lists. */
export const HEADLINE_CAP = 300;

export interface HeadlineSet {
  items: HeadlineItem[];
  /** Total matching headlines on the server, which can exceed what was loaded. */
  total: number;
}

/** Page through /topics/{id}/headlines (100 per request) until the cap or the end. */
export async function fetchTopicHeadlines(
  topicId: number,
  filters: { model?: string } = {},
  cap = HEADLINE_CAP
): Promise<HeadlineSet> {
  const items: HeadlineItem[] = [];
  let page = 1;
  let total = 0;
  while (items.length < cap) {
    const pageSize = Math.min(100, cap - items.length);
    const response = await apiClient.getTopicHeadlines(topicId, {
      page,
      pageSize,
      model: filters.model,
    });
    total = response.total;
    items.push(...response.items);
    if (page >= response.total_pages || response.items.length === 0) break;
    page += 1;
  }
  return { items, total };
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'NETWORK_ERROR') {
      return 'The API could not be reached. Check that the backend is running and that VITE_API_BASE_URL points to it.';
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'Something went wrong while loading this view.';
}

export interface AsyncState<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/**
 * Run an async loader whenever its dependencies change. Results from superseded runs are
 * dropped, so fast switching between topics never shows stale data.
 */
export function useAsync<T>(
  loader: (() => Promise<T>) | null,
  deps: readonly unknown[]
): AsyncState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(loader !== null);
  const [nonce, setNonce] = useState(0);
  const runId = useRef(0);

  useEffect(() => {
    if (!loader) {
      setLoading(false);
      return;
    }
    const id = ++runId.current;
    setLoading(true);
    setError(null);
    loader()
      .then((value) => {
        if (id !== runId.current) return;
        setData(value);
      })
      .catch((err: unknown) => {
        if (id !== runId.current) return;
        setData(undefined);
        setError(errorMessage(err));
      })
      .finally(() => {
        if (id === runId.current) setLoading(false);
      });
    // The loader closes over `deps`; callers list everything it reads.
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, error, loading, reload };
}
