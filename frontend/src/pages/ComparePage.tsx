import { useCallback, useMemo, useState, type CSSProperties } from 'react';
import { apiClient } from '../api/client';
import type { HeadlineItem, TopicResponse } from '../api/types';
import { HeadlineDrawer } from '../components/HeadlineDrawer';
import { Notice, SentimentLabel, Skeleton, useElementWidth } from '../components/primitives';
import { disagreements, pairAgreement, type Disagreement } from '../lib/agreement';
import { fetchTopicHeadlines, useAsync } from '../lib/data';
import {
  formatScore,
  modelDisplayName,
  modelsWithPredictions,
  predictionFor,
} from '../lib/sentiment';

type Params = Record<string, string | number | undefined>;

export default function ComparePage({
  params,
  replaceParams,
  registeredModels,
}: {
  params: URLSearchParams;
  replaceParams: (params: Params) => void;
  registeredModels: string[];
}) {
  const topics = useAsync(() => apiClient.listTopics(), []);
  const topicList = useMemo(() => topics.data?.topics ?? [], [topics.data]);
  const requested = Number(params.get('topic'));
  const topic: TopicResponse | undefined =
    topicList.find((t) => t.id === requested) ??
    [...topicList].sort((a, b) => (b.article_count ?? 0) - (a.article_count ?? 0))[0];
  const topicId = topic?.id;

  const headlines = useAsync(topicId ? () => fetchTopicHeadlines(topicId) : null, [topicId]);
  const items = useMemo(() => headlines.data?.items ?? [], [headlines.data]);
  const present = useMemo(() => modelsWithPredictions(items), [items]);
  const missing = registeredModels.filter((m) => !present.includes(m));

  const modelA = present.includes(params.get('a') ?? '') ? (params.get('a') as string) : present[0];
  const modelB = present.includes(params.get('b') ?? '')
    ? (params.get('b') as string)
    : present.find((m) => m !== modelA);

  const [openId, setOpenId] = useState<number | null>(null);
  const [limit, setLimit] = useState(12);
  const closeDrawer = useCallback(() => setOpenId(null), []);

  const pair = modelA && modelB ? pairAgreement(items, modelA, modelB) : null;
  const rows = useMemo(
    () => (modelA && modelB ? disagreements(items, modelA, modelB) : []),
    [items, modelA, modelB]
  );
  const openHeadline = items.find((h) => h.id === openId) ?? null;

  return (
    <div className="page">
      <header className="page-head">
        <h1>Compare models</h1>
        <p>
          How often two models give the same label to the same headlines, and which headlines they
          read differently.
        </p>
      </header>

      {topics.error ? (
        <Notice tone="error" title="Topics could not be loaded">
          {topics.error}
        </Notice>
      ) : (
        <div className="toolbar">
          <label className="field">
            Topic
            <select
              className="select"
              value={topicId ?? ''}
              onChange={(e) => replaceParams({ topic: e.target.value, a: undefined, b: undefined })}
            >
              {topicList.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.article_count ?? 0})
                </option>
              ))}
            </select>
          </label>
          {present.length >= 2 ? (
            <>
              <label className="field">
                Model A
                <select
                  className="select"
                  value={modelA}
                  onChange={(e) => replaceParams({ a: e.target.value, b: modelB })}
                >
                  {present.map((m) => (
                    <option key={m} value={m} disabled={m === modelB}>
                      {modelDisplayName(m)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Model B
                <select
                  className="select"
                  value={modelB}
                  onChange={(e) => replaceParams({ a: modelA, b: e.target.value })}
                >
                  {present.map((m) => (
                    <option key={m} value={m} disabled={m === modelA}>
                      {modelDisplayName(m)}
                    </option>
                  ))}
                </select>
              </label>
            </>
          ) : null}
        </div>
      )}

      {topics.loading || headlines.loading ? (
        <div style={{ marginTop: 28, display: 'grid', gap: 14 }}>
          <Skeleton height={140} />
          <Skeleton height={320} />
        </div>
      ) : headlines.error ? (
        <div className="section">
          <Notice tone="error" title="Headlines could not be loaded">
            {headlines.error}
          </Notice>
        </div>
      ) : topic && present.length < 2 ? (
        <div className="section">
          <Notice title="Two models are needed to compare">
            {present.length === 0
              ? `No headlines in ${topic.name} have been scored yet.`
              : `Only ${modelDisplayName(present[0] ?? '')} has scored headlines in ${topic.name}.`}{' '}
            Score them with a second model, for example <code>newsent analyze --model roberta</code>
            , then come back here.
          </Notice>
        </div>
      ) : topic && modelA && modelB && pair ? (
        <>
          <section className="section" aria-labelledby="matrix-title">
            <div className="section__head">
              <div>
                <h2 id="matrix-title" className="section__title">
                  Agreement
                </h2>
                <p className="section__note">
                  Share of headlines both models scored that got the same label. Cohen’s kappa
                  discounts the agreement expected by chance: 0 is chance level, 1 is perfect.
                  Select a cell to compare that pair.
                </p>
              </div>
            </div>
            <div className="panel panel--pad matrix-wrap">
              <table className="matrix num">
                <thead>
                  <tr>
                    <th scope="col">
                      <span className="visually-hidden">Model</span>
                    </th>
                    {present.map((m) => (
                      <th key={m} scope="col">
                        {modelDisplayName(m)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {present.map((row) => (
                    <tr key={row}>
                      <th scope="row">{modelDisplayName(row)}</th>
                      {present.map((col) => {
                        if (row === col) {
                          return (
                            <td key={col}>
                              <button type="button" className="matrix__cell" disabled>
                                <span className="matrix__rate">Same model</span>
                              </button>
                            </td>
                          );
                        }
                        const cell = pairAgreement(items, row, col);
                        const isActive =
                          (row === modelA && col === modelB) || (row === modelB && col === modelA);
                        return (
                          <td key={col}>
                            <button
                              type="button"
                              className="matrix__cell"
                              aria-pressed={isActive}
                              disabled={cell.overlap === 0}
                              style={{ '--rate': cell.rate ?? 0 } as CSSProperties}
                              onClick={() => replaceParams({ a: row, b: col })}
                            >
                              <span className="matrix__rate">
                                {cell.rate === null
                                  ? 'No overlap'
                                  : `${(cell.rate * 100).toFixed(0)}%`}
                              </span>
                              <span className="matrix__kappa">
                                {cell.kappa === null
                                  ? `n = ${cell.overlap}`
                                  : `κ ${cell.kappa.toFixed(2)}, n = ${cell.overlap}`}
                              </span>
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              {missing.length > 0 ? (
                <p className="section__note" style={{ marginTop: 12 }}>
                  Not shown, because they have no stored scores for {topic.name}:{' '}
                  {missing.map(modelDisplayName).join(', ')}.
                </p>
              ) : null}
            </div>
          </section>

          <section className="section" aria-labelledby="pair-title">
            <div className="section__head">
              <div>
                <h2 id="pair-title" className="section__title">
                  {modelDisplayName(modelA)} against {modelDisplayName(modelB)}
                </h2>
                <p className="section__note num">
                  They agree on {pair.agreed} of {pair.overlap} headlines
                  {pair.rate !== null ? ` (${(pair.rate * 100).toFixed(0)}%)` : ''}
                  {pair.kappa !== null ? `, kappa ${pair.kappa.toFixed(2)}` : ''}. Each dot is a
                  headline; highlighted dots got different labels.
                </p>
              </div>
            </div>
            <div className="compare-grid">
              <div className="panel panel--pad">
                <Scatter items={items} modelA={modelA} modelB={modelB} onSelect={setOpenId} />
              </div>
              <div className="panel">
                {rows.length === 0 ? (
                  <div style={{ padding: 20 }}>
                    <Notice title="No disagreements">
                      Both models gave every shared headline the same label.
                    </Notice>
                  </div>
                ) : (
                  <>
                    <ul className="headlines">
                      {rows.slice(0, limit).map((row) => (
                        <DisagreementRow
                          key={row.headline.id}
                          row={row}
                          modelA={modelA}
                          modelB={modelB}
                          onOpen={setOpenId}
                        />
                      ))}
                    </ul>
                    <div className="list-footer">
                      <span className="num">
                        {Math.min(limit, rows.length)} of {rows.length} disagreements, largest score
                        gap first
                      </span>
                      {limit < rows.length ? (
                        <button
                          type="button"
                          className="button"
                          onClick={() => setLimit((l) => l + 12)}
                        >
                          Show more
                        </button>
                      ) : null}
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>
        </>
      ) : null}

      {openHeadline ? (
        <HeadlineDrawer
          headline={openHeadline}
          registeredModels={registeredModels}
          preferredModel={modelA}
          onClose={closeDrawer}
        />
      ) : null}
    </div>
  );
}

function DisagreementRow({
  row,
  modelA,
  modelB,
  onOpen,
}: {
  row: Disagreement;
  modelA: string;
  modelB: string;
  onOpen: (id: number) => void;
}) {
  return (
    <li className="headline">
      <button
        type="button"
        className="headline__button disagree-row"
        onClick={() => onOpen(row.headline.id)}
      >
        <span className="headline__title" style={{ fontSize: 'var(--text-md)' }}>
          {row.headline.title}
        </span>
        <span className="disagree-row__cell">
          {modelDisplayName(modelA)}
          <SentimentLabel label={row.labelA} />
          <span className="num">{formatScore(row.scoreA)}</span>
        </span>
        <span className="disagree-row__cell">
          {modelDisplayName(modelB)}
          <SentimentLabel label={row.labelB} />
          <span className="num">{formatScore(row.scoreB)}</span>
        </span>
      </button>
    </li>
  );
}

function Scatter({
  items,
  modelA,
  modelB,
  onSelect,
}: {
  items: HeadlineItem[];
  modelA: string;
  modelB: string;
  onSelect: (id: number) => void;
}) {
  const { ref, width } = useElementWidth<HTMLDivElement>(420);
  const size = Math.max(220, Math.min(width, 460));
  const pad = 34;
  const inner = size - pad * 2;
  const x = (s: number) => pad + ((s + 1) / 2) * inner;
  const y = (s: number) => pad + ((1 - s) / 2) * inner;
  const points = items
    .map((h) => ({ h, a: predictionFor(h, modelA), b: predictionFor(h, modelB) }))
    .filter((p) => p.a && p.b);

  return (
    <div className="scatter" ref={ref}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`Scores from ${modelDisplayName(modelA)} plotted against ${modelDisplayName(modelB)} for ${points.length} headlines`}
      >
        <rect className="scatter__frame" x={pad} y={pad} width={inner} height={inner} rx={6} />
        <line className="scatter__diag" x1={x(-1)} y1={y(-1)} x2={x(1)} y2={y(1)} />
        <line className="scatter__diag" x1={x(0)} y1={pad} x2={x(0)} y2={pad + inner} />
        <line className="scatter__diag" x1={pad} y1={y(0)} x2={pad + inner} y2={y(0)} />
        {points.map(({ h, a, b }) => (
          <circle
            key={h.id}
            className="scatter__dot"
            data-disagree={a!.label !== b!.label}
            cx={x(a!.score)}
            cy={y(b!.score)}
            r={4.5}
            onClick={() => onSelect(h.id)}
          >
            <title>{`${h.title} (${formatScore(a!.score)}, ${formatScore(b!.score)})`}</title>
          </circle>
        ))}
        {[-1, 0, 1].map((t) => (
          <g key={t}>
            <text className="scatter__tick" x={x(t)} y={size - pad + 16} textAnchor="middle">
              {t === 0 ? '0' : formatScore(t, 0)}
            </text>
            <text className="scatter__tick" x={pad - 8} y={y(t) + 4} textAnchor="end">
              {t === 0 ? '0' : formatScore(t, 0)}
            </text>
          </g>
        ))}
        <text className="scatter__label" x={pad + inner / 2} y={size - 4} textAnchor="middle">
          {modelDisplayName(modelA)} score
        </text>
        <text
          className="scatter__label"
          x={12}
          y={pad + inner / 2}
          textAnchor="middle"
          transform={`rotate(-90 12 ${pad + inner / 2})`}
        >
          {modelDisplayName(modelB)} score
        </text>
      </svg>
    </div>
  );
}
