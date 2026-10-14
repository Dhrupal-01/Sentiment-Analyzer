import type { ModelMetadataItem } from '../api/types';
import { Notice, Skeleton, useElementWidth } from '../components/primitives';
import { modelDisplayName } from '../lib/sentiment';

export default function ResultsPage({
  models,
  loading,
  error,
}: {
  models: ModelMetadataItem[];
  loading: boolean;
  error: string | null;
}) {
  const evaluated = models.filter((m) => m.evaluation_metrics);
  const notEvaluated = models.filter((m) => !m.evaluation_metrics);

  return (
    <div className="page">
      <header className="page-head">
        <h1>Results</h1>
        <p>
          Benchmark scores for each model, read from the evaluation reports in the repository. A
          model without a stored evaluation is listed as not evaluated rather than given a number.
        </p>
      </header>

      {loading ? (
        <div style={{ display: 'grid', gap: 14 }}>
          <Skeleton height={180} />
          <Skeleton height={140} />
        </div>
      ) : error ? (
        <Notice tone="error" title="Model results could not be loaded">
          {error}
        </Notice>
      ) : (
        <>
          <section aria-labelledby="f1-title">
            <div className="section__head">
              <div>
                <h2 id="f1-title" className="section__title">
                  Macro-F1 with 95% confidence intervals
                </h2>
                <p className="section__note">
                  Macro-F1 averages the F1 score of the three labels, so a model cannot do well by
                  predicting the most common label. Whiskers show the bootstrap interval;
                  overlapping intervals mean the difference may not be real.
                </p>
              </div>
            </div>
            <div className="panel panel--pad">
              {evaluated.length === 0 ? (
                <Notice title="No model has a stored evaluation">
                  Run <code>make eval</code> to evaluate the installed models.
                </Notice>
              ) : (
                <IntervalChart models={evaluated} />
              )}
            </div>
          </section>

          <section className="section" aria-labelledby="models-title">
            <div className="section__head">
              <div>
                <h2 id="models-title" className="section__title">
                  Models
                </h2>
                <p className="section__note">
                  Explanation scores are shown only for models that were also benchmarked, so every
                  number on this page comes from a run of that model.
                </p>
              </div>
            </div>
            <div className="model-cards">
              {[...evaluated, ...notEvaluated].map((model) => (
                <ModelCard key={model.name} model={model} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function ModelCard({ model }: { model: ModelMetadataItem }) {
  const evaluation = model.evaluation_metrics;
  const explain = evaluation ? model.explainability_metrics : null;
  return (
    <article className="panel model-card">
      <div>
        <h3 className="model-card__name">{modelDisplayName(model.name)}</h3>
        <div className="model-card__version">{model.version}</div>
        <p className="model-card__domain">{model.domain}</p>
        {model.is_contaminated ? (
          <span className="flag" title={model.contamination_reason ?? undefined}>
            Trained on the benchmark it is scored on
          </span>
        ) : null}
      </div>

      <dl className="stats">
        <dt className="stats__title">Benchmark</dt>
        {evaluation ? (
          <>
            <dt>Accuracy</dt>
            <dd>{(evaluation.accuracy * 100).toFixed(1)}%</dd>
            <dt>Macro-F1</dt>
            <dd>{evaluation.macro_f1.toFixed(3)}</dd>
            <dt>95% interval</dt>
            <dd>
              {evaluation.bootstrap_ci_macro_f1
                ? `${evaluation.bootstrap_ci_macro_f1[0]?.toFixed(3)} to ${evaluation.bootstrap_ci_macro_f1[1]?.toFixed(3)}`
                : 'Not reported'}
            </dd>
            <dt>Test headlines</dt>
            <dd>{evaluation.sample_size}</dd>
          </>
        ) : (
          <dd className="stats__empty">
            Not evaluated. No stored benchmark run exists for this model.
          </dd>
        )}
      </dl>

      <dl className="stats">
        <dt className="stats__title">Explanations</dt>
        {explain ? (
          <>
            <dt>Faithfulness gain</dt>
            <dd>{explain.deletion_aopc_gain.toFixed(3)}</dd>
            <dt>Faithful samples</dt>
            <dd>{explain.pct_faithful.toFixed(1)}%</dd>
            <dt>Top-3 word match</dt>
            <dd>{explain.plausibility_top3_f1.toFixed(3)}</dd>
          </>
        ) : (
          <dd className="stats__empty">
            {evaluation
              ? 'No explanation evaluation stored.'
              : 'Hidden until the model itself is benchmarked.'}
          </dd>
        )}
      </dl>
    </article>
  );
}

function IntervalChart({ models }: { models: ModelMetadataItem[] }) {
  const { ref, width } = useElementWidth<HTMLDivElement>();
  const labelWidth = Math.min(200, Math.max(110, width * 0.22));
  const right = 128;
  const rowHeight = 44;
  const top = 8;
  const height = top + models.length * rowHeight + 30;
  const plot = Math.max(80, width - labelWidth - right);
  const x = (v: number) => labelWidth + Math.max(0, Math.min(1, v)) * plot;
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className="ci-chart" ref={ref}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Macro-F1 and confidence interval for each evaluated model"
      >
        {ticks.map((t) => (
          <g key={t}>
            <line className="ci-chart__grid" x1={x(t)} x2={x(t)} y1={top} y2={height - 24} />
            <text className="ci-chart__tick" x={x(t)} y={height - 6} textAnchor="middle">
              {t.toFixed(2)}
            </text>
          </g>
        ))}
        {models.map((model, i) => {
          const m = model.evaluation_metrics!;
          const cy = top + i * rowHeight + rowHeight / 2;
          const [lo, hi] = m.bootstrap_ci_macro_f1 ?? [m.macro_f1, m.macro_f1];
          return (
            <g key={model.name}>
              <text className="ci-chart__name" x={0} y={cy + 5}>
                {modelDisplayName(model.name)}
              </text>
              <line
                className="ci-chart__whisker"
                x1={x(lo ?? m.macro_f1)}
                x2={x(hi ?? m.macro_f1)}
                y1={cy}
                y2={cy}
              />
              <line
                className="ci-chart__whisker"
                x1={x(lo ?? m.macro_f1)}
                x2={x(lo ?? m.macro_f1)}
                y1={cy - 6}
                y2={cy + 6}
              />
              <line
                className="ci-chart__whisker"
                x1={x(hi ?? m.macro_f1)}
                x2={x(hi ?? m.macro_f1)}
                y1={cy - 6}
                y2={cy + 6}
              />
              <circle className="ci-chart__point" cx={x(m.macro_f1)} cy={cy} r={6} />
              <text className="ci-chart__value" x={x(hi ?? m.macro_f1) + 10} y={cy + 4}>
                {m.macro_f1.toFixed(3)} (n = {m.sample_size})
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
