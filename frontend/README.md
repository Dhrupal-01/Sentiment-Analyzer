# News Sentiment Analyzer: web app

React 19 + TypeScript + Vite. No chart library: the plots are small hand-written SVG components,
which keeps the main bundle around 75 kB gzipped and lets every chart share one visual language.

## Design

One idea runs through the interface: a sentiment score is a position on a line from −1 to +1.

- **Cold to warm, never red to green.** Negative is indigo, neutral is slate, positive is amber.
  The same scale colours dots, labels, bars, and the highlighted words in explanations, and it
  stays readable for colour-blind viewers. Every coloured mark also has a text label or sign.
- **One bold surface.** The dark band at the top of the Headlines page plots every headline of a
  topic on the −1 … +1 line. Everything else stays quiet.
- **Explanations on the words themselves.** Token attributions are drawn as highlights on the
  headline, with a ranked list of the strongest words underneath.
- **Missing data is stated, never filled.** A model with no stored evaluation is shown as
  "Not evaluated"; a model the server cannot run is listed as unavailable.

Typeface: Schibsted Grotesk (self-hosted through `@fontsource-variable/schibsted-grotesk`), a
grotesk drawn for a news publisher. Light and dark themes follow the system setting and can be
switched from the top bar.

## Pages

Routes use the URL hash, so the app works on any static host without rewrite rules.

| Route                                | What it shows                                                                                                                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `#/?topic=ID&model=NAME`             | Headlines for a topic: every headline on the −1 … +1 line, the label split, a day-by-day trend, and a filterable list. Opening a headline shows every model's score and a word-level explanation. |
| `#/try`                              | Score any headline with each installed model and compare their explanations side by side. Models the server cannot run are reported, not hidden.                                                  |
| `#/compare?topic=ID&a=MODEL&b=MODEL` | Label agreement and Cohen's kappa for every pair of models with stored scores, a score-against-score scatter, and the headlines two models disagree on.                                           |
| `#/results`                          | Macro-F1 with bootstrap intervals and per-model benchmark and explanation metrics, as served by `/api/v1/models`.                                                                                 |

## Configuration

| Variable            | When to set it                                                                                                                                                                                                                                                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `VITE_API_BASE_URL` | Leave unset when the app is served from the same origin as the API (Vite dev proxy, or the nginx container in `docker-compose.yml`). Set it to the backend's public URL, for example `https://newsent-api.example.com`, when the app is hosted separately on Vercel or Netlify. The backend's `CORS_ORIGINS` must then include the app's origin. |
| `BACKEND_PORT`      | Port the Vite dev proxy forwards `/api` to. Defaults to `8000`.                                                                                                                                                                                                                                                                                  |

## Scripts

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to the backend
npm test         # Vitest + Testing Library
npm run lint     # ESLint
npm run format   # Prettier check
npm run build    # Type-check (strict) and build to dist/
npm run codegen  # Regenerate src/api/schema.d.ts from openapi.json
```

## Layout

```
src/
  api/          typed client and OpenAPI types
  lib/          sentiment helpers, agreement and kappa, token alignment, hash router, data hooks
  components/   strip plot, trend chart, token markup, headline drawer, shared primitives
  pages/        one lazily loaded module per route
  test/         unit and component tests
```
