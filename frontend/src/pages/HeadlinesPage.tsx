import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { apiClient } from '../api/client';
import type { HeadlineItem, TopicResponse } from '../api/types';
import { HeadlineDrawer } from '../components/HeadlineDrawer';
import { NewTopicDialog } from '../components/NewTopicDialog';
import {
  DistributionBar,
  Notice,
  Segmented,
  SentimentLabel,
  Skeleton,
  ValenceMarker,
} from '../components/primitives';
import { StripPlot, type StripPoint } from '../components/StripPlot';
import { TrendChart } from '../components/TrendChart';
import { HEADLINE_CAP, fetchTopicHeadlines, useAsync } from '../lib/data';
import {
  asLabel,
  formatDate,
  formatScore,
  modelDisplayName,
  modelsWithPredictions,
  predictionFor,
  type Label,
} from '../lib/sentiment';

type Params = Record<string, string | number | undefined>;
type LabelFilter = 'all' | Label;
type SortOrder = 'newest' | 'negative' | 'positive';

const PAGE_SIZE = 20;

function pickDefaultTopic(topics: TopicResponse[]): TopicResponse | undefined {
  return [...topics].sort((a, b) => (b.article_count ?? 0) - (a.article_count ?? 0))[0];
}

export default function HeadlinesPage({
  params,
  replaceParams,
  registeredModels,
}: {
  params: URLSearchParams;
  replaceParams: (params: Params) => void;
  registeredModels: string[];
}) {
  const [topicsNonce, setTopicsNonce] = useState(0);
  const topics = useAsync(() => apiClient.listTopics(), [topicsNonce]);
  const [addingTopic, setAddingTopic] = useState(false);

  const topicList = useMemo(() => topics.data?.topics ?? [], [topics.data]);
  const requestedTopic = Number(params.get('topic'));
  const topic =
    topicList.find((t) => t.id === requestedTopic) ?? pickDefaultTopic(topicList) ?? undefined;
  const model =
    params.get('model') ??
    (registeredModels.includes('vader') ? 'vader' : registeredModels[0]) ??
    'vader';

  const topicId = topic?.id;
  const summary = useAsync(topicId ? () => apiClient.getTopicSummary(topicId, { model }) : null, [
    topicId,
    model,
  ]);
  const trend = useAsync(topicId ? () => apiClient.getTopicTrend(topicId, { model }) : null, [
    topicId,
    model,
  ]);
  const headlines = useAsync(
    topicId && (topic?.article_count ?? 0) > 0 ? () => fetchTopicHeadlines(topicId) : null,
    [topicId, topic?.article_count]
  );

  const allItems = useMemo(() => headlines.data?.items ?? [], [headlines.data]);
  const scored = useMemo(() => allItems.filter((h) => predictionFor(h, model)), [allItems, model]);

  const modelOptions = useMemo(() => {
    const names = new Set([...registeredModels, ...modelsWithPredictions(allItems), model]);
    return [...names].sort();
  }, [registeredModels, allItems, model]);

  const [labelFilter, setLabelFilter] = useState<LabelFilter>('all');
  const [outlet, setOutlet] = useState('all');
  const [sort, setSort] = useState<SortOrder>('newest');
  const [page, setPage] = useState(1);
  const [openId, setOpenId] = useState<number | null>(null);

  useEffect(() => {
    setPage(1);
  }, [topicId, model, labelFilter, outlet, sort]);

  useEffect(() => {
    setOpenId(null);
    setOutlet('all');
  }, [topicId]);

  const outlets = useMemo(
    () => [...new Set(scored.map((h) => h.outlet ?? 'Unknown outlet'))].sort(),
    [scored]
  );

  const visible = useMemo(() => {
    const rows = scored.filter((h) => {
      const prediction = predictionFor(h, model);
      if (labelFilter !== 'all' && asLabel(prediction?.label) !== labelFilter) return false;
      if (outlet !== 'all' && (h.outlet ?? 'Unknown outlet') !== outlet) return false;
      return true;
    });
    if (sort === 'newest') return rows;
    const score = (h: HeadlineItem) => predictionFor(h, model)?.score ?? 0;
    return [...rows].sort((a, b) =>
      sort === 'negative' ? score(a) - score(b) : score(b) - score(a)
    );
  }, [scored, model, labelFilter, outlet, sort]);

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const pageRows = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const points: StripPoint[] = useMemo(
    () =>
      scored.map((h) => {
        const prediction = predictionFor(h, model);
        return {
          id: h.id,
          score: prediction?.score ?? 0,
          label: asLabel(prediction?.label),
          title: h.title,
          outlet: h.outlet ?? 'Unknown outlet',
        };
      }),
    [scored, model]
  );

  const openHeadline = allItems.find((h) => h.id === openId) ?? null;
  const closeDrawer = useCallback(() => setOpenId(null), []);

  if (topics.loading && !topics.data) {
    return (
      <div className="page">
        <div style={{ marginTop: 40, display: 'grid', gap: 16 }}>
          <Skeleton height={40} width="40%" />
          <Skeleton height={280} />
        </div>
      </div>
    );
  }

  if (topics.error) {
    return (
      <div className="page" style={{ paddingTop: 40 }}>
        <Notice
          tone="error"
          title="Topics could not be loaded"
          actions={
            <button type="button" className="button" onClick={topics.reload}>
              Try again
            </button>
          }
        >
          {topics.error}
        </Notice>
      </div>
    );
  }

  return (
    <div className="page">
      {topicList.length === 0 ? (
        <div style={{ paddingTop: 40 }}>
          <Notice
            title="No topics yet"
            actions={
              <button
                type="button"
                className="button button--primary"
                onClick={() => setAddingTopic(true)}
              >
                <Plus size={16} aria-hidden="true" />
                Add topic
              </button>
            }
          >
            A topic is a set of search words, such as “markets” or “climate policy”. Headlines are
            collected and scored for each topic you add.
          </Notice>
        </div>
      ) : (
        <>
          <div className="sections" role="tablist" aria-label="Topics">
            {topicList.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                className="sections__tab"
                aria-selected={t.id === topicId}
                onClick={() => replaceParams({ topic: t.id })}
              >
                {t.name}
                <span className="sections__count num">{t.article_count ?? 0}</span>
              </button>
            ))}
            <button
              type="button"
              className="button button--quiet sections__add"
              onClick={() => setAddingTopic(true)}
            >
              <Plus size={16} aria-hidden="true" />
              Add topic
            </button>
          </div>

          <section className="band" aria-labelledby="band-title">
            <div className="band__head">
              <div>
                <h1 id="band-title" className="band__title">
                  {topic?.name}
                </h1>
                <p className="band__summary">
                  {summary.data && summary.data.total_headlines > 0 ? (
                    <>
                      <strong className="num">{summary.data.total_headlines}</strong> headlines
                      scored by {modelDisplayName(model)}, with an average score of{' '}
                      <strong className="num">{formatScore(summary.data.average_score)}</strong>.
                    </>
                  ) : (
                    <>Search words: {topic?.query}</>
                  )}
                </p>
              </div>
              <label className="field">
                Scored by
                <select
                  className="select"
                  value={model}
                  onChange={(e) => replaceParams({ model: e.target.value })}
                >
                  {modelOptions.map((name) => (
                    <option key={name} value={name}>
                      {modelDisplayName(name)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <BandBody
              topic={topic}
              model={model}
              loading={summary.loading || headlines.loading}
              error={summary.error ?? headlines.error}
              totalScored={summary.data?.total_headlines ?? 0}
              points={points}
              activeId={openId}
              onSelect={setOpenId}
              distribution={summary.data?.sentiment_distribution}
              loadedCount={scored.length}
            />
          </section>

          {summary.data && summary.data.total_headlines > 0 ? (
            <>
              <section className="section" aria-labelledby="trend-title">
                <div className="section__head">
                  <div>
                    <h2 id="trend-title" className="section__title">
                      Day by day
                    </h2>
                    <p className="section__note">
                      Average score of each day’s headlines, with the number of headlines below.
                      Days are taken from the publication date, or the collection date when an
                      outlet does not publish one.
                    </p>
                  </div>
                </div>
                <div className="panel panel--pad">
                  {trend.loading ? (
                    <Skeleton height={260} />
                  ) : trend.error ? (
                    <Notice tone="error" title="The trend could not be loaded">
                      {trend.error}
                    </Notice>
                  ) : trend.data && trend.data.time_series.length > 0 ? (
                    <>
                      <TrendChart series={trend.data.time_series} />
                      {trend.data.time_series.length === 1 ? (
                        <p className="section__note">
                          All scored headlines fall on one day, so there is no trend to draw yet.
                        </p>
                      ) : null}
                    </>
                  ) : null}
                </div>
              </section>

              <section className="section" aria-labelledby="list-title">
                <div className="section__head">
                  <div>
                    <h2 id="list-title" className="section__title">
                      Headlines
                    </h2>
                    <p className="section__note">
                      Open a headline to see every model’s score and which words drove it.
                    </p>
                  </div>
                  <div className="toolbar">
                    <div className="field">
                      Label
                      <Segmented<LabelFilter>
                        label="Filter by label"
                        value={labelFilter}
                        onChange={setLabelFilter}
                        options={[
                          { value: 'all', label: 'All' },
                          { value: 'negative', label: 'Negative' },
                          { value: 'neutral', label: 'Neutral' },
                          { value: 'positive', label: 'Positive' },
                        ]}
                      />
                    </div>
                    <label className="field">
                      Outlet
                      <select
                        className="select"
                        value={outlet}
                        onChange={(e) => setOutlet(e.target.value)}
                      >
                        <option value="all">All outlets</option>
                        {outlets.map((o) => (
                          <option key={o} value={o}>
                            {o}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      Order
                      <select
                        className="select"
                        value={sort}
                        onChange={(e) => setSort(e.target.value as SortOrder)}
                      >
                        <option value="newest">Newest first</option>
                        <option value="negative">Most negative first</option>
                        <option value="positive">Most positive first</option>
                      </select>
                    </label>
                  </div>
                </div>

                <div className="panel">
                  {pageRows.length === 0 ? (
                    <div style={{ padding: 20 }}>
                      <Notice title="No headlines match these filters">
                        Choose a different label or outlet to see more headlines.
                      </Notice>
                    </div>
                  ) : (
                    <ul className="headlines">
                      {pageRows.map((h) => {
                        const prediction = predictionFor(h, model);
                        const label = asLabel(prediction?.label);
                        return (
                          <li key={h.id} className="headline">
                            <button
                              type="button"
                              className="headline__button"
                              onClick={() => setOpenId(h.id)}
                            >
                              <span>
                                <span className="headline__title">{h.title}</span>
                                <span className="headline__meta">
                                  <span>{h.outlet ?? 'Unknown outlet'}</span>
                                  <span>{formatDate(h.published_at)}</span>
                                </span>
                              </span>
                              {prediction ? (
                                <span className="headline__score">
                                  <span className="headline__score-row">
                                    <SentimentLabel label={label} />
                                    <span className="num">{formatScore(prediction.score)}</span>
                                  </span>
                                  <ValenceMarker score={prediction.score} label={label} />
                                </span>
                              ) : null}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                  <div className="list-footer">
                    <span className="num">
                      {visible.length} of {scored.length} loaded headlines
                      {headlines.data && headlines.data.total > allItems.length
                        ? `, latest ${HEADLINE_CAP} of ${headlines.data.total} in this topic`
                        : ''}
                    </span>
                    {pageCount > 1 ? (
                      <div className="list-footer__pager">
                        <button
                          type="button"
                          className="button"
                          disabled={page <= 1}
                          onClick={() => setPage((p) => p - 1)}
                        >
                          Previous
                        </button>
                        <span className="num" style={{ alignSelf: 'center' }}>
                          Page {page} of {pageCount}
                        </span>
                        <button
                          type="button"
                          className="button"
                          disabled={page >= pageCount}
                          onClick={() => setPage((p) => p + 1)}
                        >
                          Next
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </section>
            </>
          ) : null}
        </>
      )}

      {openHeadline ? (
        <HeadlineDrawer
          headline={openHeadline}
          registeredModels={registeredModels}
          preferredModel={model}
          onClose={closeDrawer}
        />
      ) : null}

      {addingTopic ? (
        <NewTopicDialog
          onClose={() => setAddingTopic(false)}
          onCreated={(created) => {
            setAddingTopic(false);
            setTopicsNonce((n) => n + 1);
            replaceParams({ topic: created.id });
          }}
        />
      ) : null}
    </div>
  );
}

function BandBody({
  topic,
  model,
  loading,
  error,
  totalScored,
  points,
  activeId,
  onSelect,
  distribution,
  loadedCount,
}: {
  topic: TopicResponse | undefined;
  model: string;
  loading: boolean;
  error: string | null;
  totalScored: number;
  points: StripPoint[];
  activeId: number | null;
  onSelect: (id: number) => void;
  distribution: { positive: number; neutral: number; negative: number } | undefined;
  loadedCount: number;
}) {
  if (!topic) return null;
  if ((topic.article_count ?? 0) === 0) {
    return (
      <div className="band__plot">
        <Notice title={`No headlines collected for ${topic.name} yet`}>
          Collection runs on a schedule. To collect now, run <code>newsent collect</code> on the
          server, then score the new headlines with <code>newsent analyze --model vader</code>.
        </Notice>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="band__plot" style={{ display: 'grid', gap: 14 }}>
        <Skeleton height={150} />
        <Skeleton height={12} />
      </div>
    );
  }
  if (error) {
    return (
      <div className="band__plot">
        <Notice tone="error" title="This topic could not be loaded">
          {error}
        </Notice>
      </div>
    );
  }
  if (totalScored === 0) {
    return (
      <div className="band__plot">
        <Notice title={`${modelDisplayName(model)} has not scored ${topic.name} yet`}>
          {topic.article_count} headlines are collected but none have {modelDisplayName(model)}{' '}
          scores. Run <code>newsent analyze --model {model}</code>, or choose another model above.
        </Notice>
      </div>
    );
  }
  return (
    <>
      <div className="band__plot">
        <StripPlot points={points} activeId={activeId} onSelect={onSelect} />
        {loadedCount < totalScored ? (
          <p className="band__summary num" style={{ fontSize: 'var(--text-sm)' }}>
            Showing the latest {loadedCount} of {totalScored} scored headlines.
          </p>
        ) : null}
      </div>
      {distribution ? (
        <div className="band__distribution">
          <DistributionBar counts={distribution} />
        </div>
      ) : null}
    </>
  );
}
