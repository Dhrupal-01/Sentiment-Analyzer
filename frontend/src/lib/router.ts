import { useCallback, useEffect, useState } from 'react';

export type Page = 'headlines' | 'try' | 'compare' | 'results';

export interface Route {
  page: Page;
  params: URLSearchParams;
}

const PAGES: Record<string, Page> = {
  '': 'headlines',
  headlines: 'headlines',
  try: 'try',
  compare: 'compare',
  results: 'results',
};

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#\/?/, '');
  const [path = '', query = ''] = raw.split('?');
  const page = PAGES[path] ?? 'headlines';
  return { page, params: new URLSearchParams(query) };
}

export function buildHash(
  page: Page,
  params?: Record<string, string | number | undefined>
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== '') search.set(key, String(value));
  }
  const query = search.toString();
  const path = page === 'headlines' ? '' : page;
  return `#/${path}${query ? `?${query}` : ''}`;
}

/** Hash routing keeps the app working on any static host without rewrite rules. */
export function useHashRoute(): {
  route: Route;
  navigate: (page: Page, params?: Record<string, string | number | undefined>) => void;
  replaceParams: (params: Record<string, string | number | undefined>) => void;
} {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  const navigate = useCallback(
    (page: Page, params?: Record<string, string | number | undefined>) => {
      window.location.hash = buildHash(page, params);
    },
    []
  );

  const replaceParams = useCallback((params: Record<string, string | number | undefined>) => {
    const current = parseHash(window.location.hash);
    const merged: Record<string, string> = Object.fromEntries(current.params.entries());
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === '') delete merged[key];
      else merged[key] = String(value);
    }
    const next = buildHash(current.page, merged);
    window.history.replaceState(null, '', next);
    setRoute(parseHash(next));
  }, []);

  return { route, navigate, replaceParams };
}
