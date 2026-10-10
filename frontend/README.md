# News Sentiment Analyzer — Frontend Dashboard

Interactive React dashboard for the News Sentiment Analyzer system, built with Vite, React 19, TypeScript, Vanilla CSS, and Recharts.

---

## Architecture & Features

1. **Topic Dashboard (`#topic`)**
   - KPI metrics: total tracked headlines, positive/neutral/negative volumes, and average net sentiment score.
   - Dual-axis time-series trend chart combining daily sentiment scores and headline volume using Recharts.
   - Sentiment distribution donut chart.
   - Multi-parameter filterable headline table (date range, outlet/source, sentiment label, model filter).
   - Per-model toggle selector and new topic creation modal.

2. **Headline Detail (`#detail`)**
   - Direct inspection of stored headlines with multi-model prediction score cards and confidence distributions.
   - Interactive token-highlighted explanation view with signed attributions (green positive, red negative, normalized by relative weight with hover tooltips).
   - Method selector supporting Occlusion, Integrated Gradients, and SHAP.
   - Top-token attribution importance bar chart.

3. **Try It Live (`#try-it`)**
   - Ad-hoc headline input with fast pre-filled news headline presets.
   - Simultaneous side-by-side inference across all registered models (VADER, RoBERTa, FinBERT).
   - Real-time token attribution visualization with method toggle.

4. **Model Comparison (`#comparison`)**
   - Pairwise discrete label agreement matrix heatmap across all models.
   - Model disagreement explorer highlighting headlines where models diverge, with maximum absolute score delta calculations.

5. **Research Results (`#results`)**
   - Full evaluation benchmark comparisons on Financial PhraseBank (accuracy, Macro-F1, bootstrap 95% CIs).
   - In-domain general headline test set evaluation and domain gap ($\Delta_{\text{domain}}$) quantification.
   - Explanation faithfulness metrics (AOPC token deletion and insertion curves vs random baselines).
   - Human rationale plausibility (Precision, Recall, token F1 on 100 annotated headlines).
   - Benchmark contamination status and disclosures.

---

## Development Scripts

From the `frontend/` directory:

```bash
# Install dependencies
npm install

# Start Vite development server with proxy to backend (http://localhost:8000)
npm run dev

# Run Vitest test suites
npm test

# Run ESLint check
npm run lint

# Format code with Prettier
npm run format

# Type-check and build production bundle
npm run build

# Regenerate API client types from backend OpenAPI schema
npm run codegen:api
```

---

## Design System

- **Vanilla CSS**: Bespoke dark-mode design system with glassmorphism cards, glowing cyan accents, and CSS variables defined in `src/index.css`.
- **Typography**: Inter (body), Outfit (headings), and JetBrains Mono (monospaced metrics and tokens).
- **Responsive & Resilient**: Flexbox and grid layouts, shimmer loading skeletons (`LoadingSkeleton`), empty states (`EmptyState`), and retryable error alerts (`ErrorAlert`).
