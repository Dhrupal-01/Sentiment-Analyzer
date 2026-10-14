import { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { apiClient } from './api/client';
import { Skeleton } from './components/primitives';
import { useAsync } from './lib/data';
import { buildHash, useHashRoute, type Page } from './lib/router';

const HeadlinesPage = lazy(() => import('./pages/HeadlinesPage'));
const TryPage = lazy(() => import('./pages/TryPage'));
const ComparePage = lazy(() => import('./pages/ComparePage'));
const ResultsPage = lazy(() => import('./pages/ResultsPage'));

const NAV: { page: Page; label: string }[] = [
  { page: 'headlines', label: 'Headlines' },
  { page: 'try', label: 'Try a headline' },
  { page: 'compare', label: 'Compare models' },
  { page: 'results', label: 'Results' },
];

type Theme = 'light' | 'dark';

function readStoredTheme(): Theme | null {
  try {
    const value = window.localStorage.getItem('theme');
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = readStoredTheme();
    if (stored) return stored;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  const toggle = () =>
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      try {
        window.localStorage.setItem('theme', next);
      } catch {
        // Storage can be unavailable (private mode); the choice then lasts for this visit.
      }
      return next;
    });
  return [theme, toggle];
}

export function App() {
  const { route, replaceParams } = useHashRoute();
  const [theme, toggleTheme] = useTheme();
  const registry = useAsync(() => apiClient.listModels(), []);
  const health = useAsync(() => apiClient.getHealth(), []);
  const registeredModels = useMemo(
    () => (registry.data?.models ?? []).map((m) => m.name),
    [registry.data]
  );

  const apiState = health.loading ? 'checking' : health.error ? 'offline' : 'online';
  const apiText =
    apiState === 'checking'
      ? 'Checking API'
      : apiState === 'offline'
        ? 'API unreachable'
        : 'API online';

  useEffect(() => {
    const titles: Record<Page, string> = {
      headlines: 'Headlines',
      try: 'Try a headline',
      compare: 'Compare models',
      results: 'Results',
    };
    document.title = `${titles[route.page]} | News Sentiment Analyzer`;
  }, [route.page]);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar__inner">
          <a className="wordmark" href={buildHash('headlines')}>
            <span className="wordmark__glyph" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            News Sentiment Analyzer
          </a>
          <nav className="nav" aria-label="Main">
            {NAV.map((item) => (
              <a
                key={item.page}
                className="nav__link"
                href={buildHash(item.page)}
                aria-current={route.page === item.page ? 'page' : undefined}
              >
                {item.label}
              </a>
            ))}
          </nav>
          <div className="topbar__end">
            <span className="api-status" data-state={apiState} title={health.error ?? apiText}>
              <span className="api-status__dot" aria-hidden="true" />
              <span className="api-status__text">{apiText}</span>
            </span>
            <button
              type="button"
              className="icon-button"
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            >
              {theme === 'dark' ? (
                <Sun size={17} aria-hidden="true" />
              ) : (
                <Moon size={17} aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="main" id="main">
        <Suspense
          fallback={
            <div className="page" style={{ paddingTop: 40 }}>
              <Skeleton height={320} />
            </div>
          }
        >
          {route.page === 'headlines' ? (
            <HeadlinesPage
              params={route.params}
              replaceParams={replaceParams}
              registeredModels={registeredModels}
            />
          ) : null}
          {route.page === 'try' ? <TryPage registeredModels={registeredModels} /> : null}
          {route.page === 'compare' ? (
            <ComparePage
              params={route.params}
              replaceParams={replaceParams}
              registeredModels={registeredModels}
            />
          ) : null}
          {route.page === 'results' ? (
            <ResultsPage
              models={registry.data?.models ?? []}
              loading={registry.loading}
              error={registry.error}
            />
          ) : null}
        </Suspense>
      </main>

      <footer className="footer">
        <div className="footer__inner">
          <span>Scores run from −1 (negative) to +1 (positive).</span>
          <span>
            <a href="https://github.com/Dhrupal-01/Sentiment-Analyzer">Source on GitHub</a>
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
