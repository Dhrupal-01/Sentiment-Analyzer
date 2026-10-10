import React, { useEffect, useState, useMemo } from 'react';
import {
  TrendingUp,
  Filter,
  Layers,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Plus,
} from 'lucide-react';
import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { apiClient } from '../api/client';
import type {
  DailyTrendItem,
  HeadlineItem,
  ModelMetadataItem,
  TopicResponse,
  TopicSummaryResponse,
} from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorAlert } from '../components/ErrorAlert';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { SentimentBadge } from '../components/SentimentBadge';

interface TopicDashboardProps {
  onSelectHeadline: (headline: HeadlineItem, modelName: string) => void;
}

export const TopicDashboard: React.FC<TopicDashboardProps> = ({ onSelectHeadline }) => {
  // Topics & Models
  const [topics, setTopics] = useState<TopicResponse[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [models, setModels] = useState<ModelMetadataItem[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('vader');

  // Summary & Trend
  const [summary, setSummary] = useState<TopicSummaryResponse | null>(null);
  const [trend, setTrend] = useState<DailyTrendItem[]>([]);
  const [isSummaryLoading, setIsSummaryLoading] = useState<boolean>(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // Headlines
  const [headlines, setHeadlines] = useState<HeadlineItem[]>([]);
  const [totalHeadlines, setTotalHeadlines] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;
  const [selectedLabel, setSelectedLabel] = useState<string>('all');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [isHeadlinesLoading, setIsHeadlinesLoading] = useState<boolean>(true);
  const [headlinesError, setHeadlinesError] = useState<string | null>(null);

  // New Topic Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [newTopicName, setNewTopicName] = useState<string>('');
  const [newTopicQuery, setNewTopicQuery] = useState<string>('');
  const [isCreatingTopic, setIsCreatingTopic] = useState<boolean>(false);
  const [createTopicError, setCreateTopicError] = useState<string | null>(null);

  // 1. Fetch initial topics and models
  useEffect(() => {
    let isMounted = true;
    const fetchMetadata = async () => {
      try {
        const [topicsData, modelsData] = await Promise.all([
          apiClient.listTopics(),
          apiClient.listModels(),
        ]);
        if (isMounted) {
          setTopics(topicsData.topics);
          if (topicsData.topics.length > 0) {
            setSelectedTopicId(topicsData.topics[0].id);
          }
          setModels(modelsData.models);
          if (modelsData.models.length > 0) {
            setSelectedModel(modelsData.models[0].name);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setSummaryError(err.message || 'Failed to load topics or model registry');
        }
      }
    };
    fetchMetadata();
    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Fetch Summary and Trend whenever selected topic or model changes
  useEffect(() => {
    if (!selectedTopicId) return;

    let isMounted = true;
    const fetchAnalytics = async () => {
      setIsSummaryLoading(true);
      setSummaryError(null);
      try {
        const [summaryData, trendData] = await Promise.all([
          apiClient.getTopicSummary(selectedTopicId, { model: selectedModel }),
          apiClient.getTopicTrend(selectedTopicId, { model: selectedModel }),
        ]);
        if (isMounted) {
          setSummary(summaryData);
          setTrend(trendData.time_series);
        }
      } catch (err: any) {
        if (isMounted) {
          setSummaryError(err.message || 'Failed to load topic sentiment analytics');
        }
      } finally {
        if (isMounted) setIsSummaryLoading(false);
      }
    };

    fetchAnalytics();
    return () => {
      isMounted = false;
    };
  }, [selectedTopicId, selectedModel]);

  // 3. Fetch Headlines when filters or pagination changes
  useEffect(() => {
    if (!selectedTopicId) return;

    let isMounted = true;
    const fetchHeadlines = async () => {
      setIsHeadlinesLoading(true);
      setHeadlinesError(null);
      try {
        const params: any = {
          page,
          pageSize,
          model: selectedModel,
        };
        if (selectedLabel !== 'all') params.label = selectedLabel;
        if (selectedSource !== 'all') params.source = selectedSource;

        const data = await apiClient.getTopicHeadlines(selectedTopicId, params);
        if (isMounted) {
          setHeadlines(data.items);
          setTotalHeadlines(data.total);
        }
      } catch (err: any) {
        if (isMounted) {
          setHeadlinesError(err.message || 'Failed to load topic headlines');
        }
      } finally {
        if (isMounted) setIsHeadlinesLoading(false);
      }
    };

    fetchHeadlines();
    return () => {
      isMounted = false;
    };
  }, [selectedTopicId, selectedModel, page, selectedLabel, selectedSource]);

  // Handle Topic Creation
  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopicName.trim() || !newTopicQuery.trim()) return;

    setIsCreatingTopic(true);
    setCreateTopicError(null);
    try {
      const created = await apiClient.createTopic({
        name: newTopicName.trim(),
        query: newTopicQuery.trim(),
        is_active: true,
      });
      setTopics((prev) => [...prev, created]);
      setSelectedTopicId(created.id);
      setIsCreateModalOpen(false);
      setNewTopicName('');
      setNewTopicQuery('');
    } catch (err: any) {
      setCreateTopicError(err.message || 'Failed to create topic');
    } finally {
      setIsCreatingTopic(false);
    }
  };

  // Pie chart data
  const pieData = useMemo(() => {
    if (!summary) return [];
    return [
      {
        name: 'Positive',
        value: summary.sentiment_distribution.positive,
        color: 'var(--sentiment-pos)',
      },
      {
        name: 'Neutral',
        value: summary.sentiment_distribution.neutral,
        color: 'var(--sentiment-neu)',
      },
      {
        name: 'Negative',
        value: summary.sentiment_distribution.negative,
        color: 'var(--sentiment-neg)',
      },
    ];
  }, [summary]);

  // Distinct outlets/sources from headlines
  const availableOutlets = useMemo(() => {
    const set = new Set<string>();
    headlines.forEach((h) => {
      if (h.outlet) set.add(h.outlet);
    });
    return Array.from(set);
  }, [headlines]);

  const totalPages = Math.max(1, Math.ceil(totalHeadlines / pageSize));

  return (
    <div style={{ padding: '32px 24px', maxWidth: '1440px', margin: '0 auto', width: '100%' }}>
      {/* Page Header & Controls Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '20px',
          marginBottom: '28px',
        }}
      >
        <div>
          <h1 style={{ fontSize: '28px', marginBottom: '6px' }}>Topic Sentiment Intelligence</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Thematic sentiment tracking, daily polarity trend trajectory, and headline
            classification.
          </p>
        </div>

        {/* Global Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Topic Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>
              Topic:
            </span>
            <select
              aria-label="Select Topic"
              className="select"
              style={{ width: '180px', padding: '8px 12px' }}
              value={selectedTopicId ?? ''}
              onChange={(e) => {
                setSelectedTopicId(Number(e.target.value));
                setPage(1);
              }}
            >
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.article_count} articles)
                </option>
              ))}
            </select>
          </div>

          {/* Model Toggle Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>
              Model:
            </span>
            <select
              aria-label="Select Sentiment Model"
              className="select"
              style={{ width: '160px', padding: '8px 12px' }}
              value={selectedModel}
              onChange={(e) => {
                setSelectedModel(e.target.value);
                setPage(1);
              }}
            >
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name.length > 20 ? `${m.name.substring(0, 18)}...` : m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Add Topic Button */}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setIsCreateModalOpen(true)}
            style={{ padding: '8px 14px' }}
          >
            <Plus size={16} />
            <span>New Topic</span>
          </button>
        </div>
      </div>

      {summaryError && (
        <ErrorAlert message={summaryError} onRetry={() => setSelectedTopicId(selectedTopicId)} />
      )}

      {/* KPI Cards Row */}
      {isSummaryLoading ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginBottom: '24px',
          }}
        >
          <LoadingSkeleton height="100px" count={4} />
        </div>
      ) : summary ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginBottom: '24px',
          }}
        >
          {/* Card 1: Total Volume */}
          <div className="glass-card" style={{ padding: '20px' }}>
            <div
              style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                marginBottom: '6px',
              }}
            >
              Total Articles Analyzed
            </div>
            <div
              style={{
                fontSize: '32px',
                fontWeight: 800,
                color: '#ffffff',
                fontFamily: 'var(--font-heading)',
              }}
            >
              {summary.total_headlines.toLocaleString()}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Tracked under topic &apos;{summary.topic_name}&apos;
            </div>
          </div>

          {/* Card 2: Average Score */}
          <div className="glass-card" style={{ padding: '20px' }}>
            <div
              style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                marginBottom: '6px',
              }}
            >
              Average Sentiment Polarity
            </div>
            <div
              style={{
                fontSize: '32px',
                fontWeight: 800,
                fontFamily: 'var(--font-heading)',
                color:
                  summary.average_score > 0.05
                    ? 'var(--sentiment-pos)'
                    : summary.average_score < -0.05
                      ? 'var(--sentiment-neg)'
                      : 'var(--sentiment-neu)',
              }}
            >
              {summary.average_score > 0
                ? `+${summary.average_score.toFixed(3)}`
                : summary.average_score.toFixed(3)}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Continuous scale from -1.0 to +1.0
            </div>
          </div>

          {/* Card 3: Positive Ratio */}
          <div className="glass-card" style={{ padding: '20px' }}>
            <div
              style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                marginBottom: '6px',
              }}
            >
              Positive Headlines
            </div>
            <div
              style={{
                fontSize: '32px',
                fontWeight: 800,
                color: 'var(--sentiment-pos)',
                fontFamily: 'var(--font-heading)',
              }}
            >
              {summary.sentiment_percentages.positive.toFixed(1)}%
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {summary.sentiment_distribution.positive} positive classifications
            </div>
          </div>

          {/* Card 4: Negative Ratio */}
          <div className="glass-card" style={{ padding: '20px' }}>
            <div
              style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                marginBottom: '6px',
              }}
            >
              Negative Headlines
            </div>
            <div
              style={{
                fontSize: '32px',
                fontWeight: 800,
                color: 'var(--sentiment-neg)',
                fontFamily: 'var(--font-heading)',
              }}
            >
              {summary.sentiment_percentages.negative.toFixed(1)}%
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {summary.sentiment_distribution.negative} negative classifications
            </div>
          </div>
        </div>
      ) : null}

      {/* Visual Analytics Grid: Trend Chart & Sentiment Donut */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        {/* Left: Daily Sentiment Trend & Volume Chart */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '16px',
            }}
          >
            <div>
              <h2 style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <TrendingUp size={20} color="var(--accent-cyan)" />
                Sentiment Trajectory & Headline Volume Over Time
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Dual-axis tracking: average daily score (line) vs headline volume (bars)
              </p>
            </div>
            <span className="badge badge-model">{selectedModel}</span>
          </div>

          {isSummaryLoading ? (
            <LoadingSkeleton height="280px" />
          ) : trend.length === 0 ? (
            <EmptyState
              title="No trend data recorded"
              description="Ingested headlines for this topic lack daily chronological predictions."
            />
          ) : (
            <div style={{ width: '100%', height: '280px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis
                    dataKey="date"
                    stroke="var(--text-muted)"
                    fontSize={11}
                    tickFormatter={(val) => val.slice(5)}
                  />
                  <YAxis
                    yAxisId="score"
                    domain={[-1, 1]}
                    stroke="var(--text-muted)"
                    fontSize={11}
                    tickFormatter={(v) => v.toFixed(1)}
                  />
                  <YAxis
                    yAxisId="vol"
                    orientation="right"
                    stroke="var(--text-muted)"
                    fontSize={11}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      borderColor: 'var(--border-card)',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#f8fafc',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Bar
                    yAxisId="vol"
                    dataKey="headline_volume"
                    name="Headline Volume"
                    fill="rgba(56, 189, 248, 0.3)"
                    radius={[4, 4, 0, 0]}
                  />
                  <Area
                    yAxisId="score"
                    type="monotone"
                    dataKey="average_score"
                    name="Avg Sentiment Score"
                    stroke="var(--accent-cyan)"
                    strokeWidth={2.5}
                    fill="url(#trendGradient)"
                  />
                  <defs>
                    <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent-cyan)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Right: Sentiment Breakdown Donut */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ marginBottom: '16px' }}>
            <h2 style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={20} color="var(--accent-cyan)" />
              Sentiment Distribution
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Proportions across positive, neutral, and negative
            </p>
          </div>

          {isSummaryLoading ? (
            <LoadingSkeleton height="280px" />
          ) : !summary || summary.total_headlines === 0 ? (
            <EmptyState title="No headlines scored" description="No sentiment scores available." />
          ) : (
            <div style={{ width: '100%', height: '240px', position: 'relative' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      borderColor: 'var(--border-card)',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* Legend List */}
              <div
                style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '4px' }}
              >
                <span
                  style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <span
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--sentiment-pos)',
                    }}
                  />
                  Pos ({summary.sentiment_percentages.positive.toFixed(1)}%)
                </span>
                <span
                  style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <span
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--sentiment-neu)',
                    }}
                  />
                  Neu ({summary.sentiment_percentages.neutral.toFixed(1)}%)
                </span>
                <span
                  style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <span
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--sentiment-neg)',
                    }}
                  />
                  Neg ({summary.sentiment_percentages.negative.toFixed(1)}%)
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filterable Headline Table Section */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
            marginBottom: '20px',
          }}
        >
          <div>
            <h2 style={{ fontSize: '18px' }}>Headlines ({totalHeadlines.toLocaleString()})</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Click any headline to inspect full multi-model token explanations
            </p>
          </div>

          {/* Table Filter Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Filter size={14} color="var(--text-muted)" />
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Label:</span>
              <select
                aria-label="Filter by Sentiment Label"
                className="select"
                style={{ width: '110px', padding: '6px 10px', fontSize: '13px' }}
                value={selectedLabel}
                onChange={(e) => {
                  setSelectedLabel(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Labels</option>
                <option value="positive">Positive</option>
                <option value="neutral">Neutral</option>
                <option value="negative">Negative</option>
              </select>
            </div>

            {availableOutlets.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Outlet:</span>
                <select
                  aria-label="Filter by News Outlet"
                  className="select"
                  style={{ width: '130px', padding: '6px 10px', fontSize: '13px' }}
                  value={selectedSource}
                  onChange={(e) => {
                    setSelectedSource(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="all">All Outlets</option>
                  {availableOutlets.map((out) => (
                    <option key={out} value={out}>
                      {out}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {headlinesError && <ErrorAlert message={headlinesError} />}

        {/* Headlines Table */}
        {isHeadlinesLoading ? (
          <LoadingSkeleton height="50px" count={8} />
        ) : headlines.length === 0 ? (
          <EmptyState
            title="No headlines found"
            description="No articles match the current filter criteria."
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                textAlign: 'left',
                fontSize: '14px',
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    color: 'var(--text-muted)',
                    fontSize: '12px',
                  }}
                >
                  <th style={{ padding: '12px 14px', width: '55%' }}>HEADLINE</th>
                  <th style={{ padding: '12px 14px' }}>OUTLET</th>
                  <th style={{ padding: '12px 14px' }}>DATE</th>
                  <th style={{ padding: '12px 14px' }}>SENTIMENT</th>
                  <th style={{ padding: '12px 14px', textAlign: 'right' }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {headlines.map((item) => {
                  const pred = item.predictions[selectedModel];
                  return (
                    <tr
                      key={item.id}
                      style={{
                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                        transition: 'background-color 150ms ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.03)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      {/* Title */}
                      <td style={{ padding: '12px 14px' }}>
                        <div
                          onClick={() => onSelectHeadline(item, selectedModel)}
                          style={{
                            cursor: 'pointer',
                            color: '#ffffff',
                            fontWeight: 500,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                          }}
                        >
                          <span>{item.title}</span>
                          <ExternalLink
                            size={12}
                            color="var(--accent-cyan)"
                            style={{ opacity: 0.7 }}
                          />
                        </div>
                      </td>

                      {/* Outlet */}
                      <td
                        style={{
                          padding: '12px 14px',
                          color: 'var(--text-secondary)',
                          fontSize: '13px',
                        }}
                      >
                        {item.outlet || 'Unknown'}
                      </td>

                      {/* Published Date */}
                      <td
                        style={{
                          padding: '12px 14px',
                          color: 'var(--text-muted)',
                          fontSize: '12px',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {item.published_at ? item.published_at.slice(0, 10) : 'Recent'}
                      </td>

                      {/* Sentiment */}
                      <td style={{ padding: '12px 14px' }}>
                        {pred ? (
                          <SentimentBadge label={pred.label} score={pred.score} />
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                            Unscored
                          </span>
                        )}
                      </td>

                      {/* Action */}
                      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: '4px 10px', fontSize: '12px' }}
                          onClick={() => onSelectHeadline(item, selectedModel)}
                        >
                          Explain
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '18px',
              borderTop: '1px solid var(--border-subtle)',
              marginTop: '12px',
            }}
          >
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Page {page} of {totalPages} ({totalHeadlines} items)
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                style={{ padding: '6px 12px' }}
              >
                <ChevronLeft size={14} /> Previous
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                style={{ padding: '6px 12px' }}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Topic Modal */}
      {isCreateModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <div className="glass-card" style={{ maxWidth: '480px', width: '100%', padding: '28px' }}>
            <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Create News Tracking Topic</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Define a thematic beat and search query for headline ingestion.
            </p>

            {createTopicError && <ErrorAlert message={createTopicError} />}

            <form onSubmit={handleCreateTopic}>
              <div style={{ marginBottom: '16px' }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                  }}
                >
                  Topic Name
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g. Artificial Intelligence"
                  value={newTopicName}
                  onChange={(e) => setNewTopicName(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                  }}
                >
                  Search Query
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g. artificial intelligence OR LLM OR OpenAI"
                  value={newTopicQuery}
                  onChange={(e) => setNewTopicQuery(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={isCreatingTopic}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isCreatingTopic}>
                  {isCreatingTopic ? 'Creating...' : 'Create Topic'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
