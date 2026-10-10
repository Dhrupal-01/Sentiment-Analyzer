import React, { useEffect, useState, useMemo } from 'react';
import { Scale, AlertTriangle, ArrowRight, ExternalLink } from 'lucide-react';
import { apiClient } from '../api/client';
import type { HeadlineItem, ModelMetadataItem, TopicResponse } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorAlert } from '../components/ErrorAlert';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { SentimentBadge } from '../components/SentimentBadge';

interface ModelComparisonProps {
  onSelectHeadline: (headline: HeadlineItem, modelName: string) => void;
}

export const ModelComparison: React.FC<ModelComparisonProps> = ({ onSelectHeadline }) => {
  const [topics, setTopics] = useState<TopicResponse[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [models, setModels] = useState<ModelMetadataItem[]>([]);

  const [headlines, setHeadlines] = useState<HeadlineItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Model comparison pair
  const [modelA, setModelA] = useState<string>('vader');
  const [modelB, setModelB] = useState<string>('cardiffnlp/twitter-roberta-base-sentiment-latest');

  // Load initial topics and models
  useEffect(() => {
    let isMounted = true;
    const fetchMeta = async () => {
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
          if (modelsData.models.length >= 2) {
            setModelA(modelsData.models[0].name);
            setModelB(modelsData.models[1].name);
          }
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load comparison data');
      }
    };

    fetchMeta();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch a sample of headlines for the topic to compute agreement and find disagreements
  useEffect(() => {
    if (!selectedTopicId) return;

    let isMounted = true;
    const fetchHeadlines = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Fetch up to 100 headlines for comparison
        const data = await apiClient.getTopicHeadlines(selectedTopicId, {
          page: 1,
          pageSize: 100,
        });
        if (isMounted) {
          setHeadlines(data.items);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load headlines for comparison');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchHeadlines();
    return () => {
      isMounted = false;
    };
  }, [selectedTopicId]);

  // Compute Pairwise Agreement Matrix across all registered models
  const agreementMatrix = useMemo(() => {
    const matrix: Record<string, Record<string, { agreementPct: number; totalPairs: number }>> = {};

    const modelNames = models.map((m) => m.name);
    for (const m1 of modelNames) {
      matrix[m1] = {};
      for (const m2 of modelNames) {
        if (m1 === m2) {
          matrix[m1][m2] = { agreementPct: 100, totalPairs: headlines.length };
          continue;
        }

        let agreed = 0;
        let count = 0;
        headlines.forEach((h) => {
          const p1 = h.predictions[m1];
          const p2 = h.predictions[m2];
          if (p1 && p2) {
            count += 1;
            if (p1.label.toLowerCase() === p2.label.toLowerCase()) {
              agreed += 1;
            }
          }
        });

        const pct = count > 0 ? (agreed / count) * 100 : 0;
        matrix[m1][m2] = { agreementPct: Number(pct.toFixed(1)), totalPairs: count };
      }
    }

    return matrix;
  }, [models, headlines]);

  // Identify Disagreement Headlines between Model A and Model B
  const disagreementHeadlines = useMemo(() => {
    const list: {
      headline: HeadlineItem;
      predA: { label: string; score: number };
      predB: { label: string; score: number };
      diffScore: number;
    }[] = [];

    headlines.forEach((h) => {
      const pA = h.predictions[modelA];
      const pB = h.predictions[modelB];
      if (pA && pB && pA.label.toLowerCase() !== pB.label.toLowerCase()) {
        const diff = Math.abs(pA.score - pB.score);
        list.push({
          headline: h,
          predA: pA,
          predB: pB,
          diffScore: Number(diff.toFixed(4)),
        });
      }
    });

    // Sort by largest absolute score discrepancy
    return list.sort((a, b) => b.diffScore - a.diffScore);
  }, [headlines, modelA, modelB]);

  return (
    <div style={{ padding: '32px 24px', maxWidth: '1440px', margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1
          style={{
            fontSize: '28px',
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <Scale size={28} color="var(--accent-cyan)" />
          Model Agreement & Discrepancy Matrix
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Evaluate inter-model consistency across real news headlines. Uncover systematic
          blindspots, lexicon biases, and boundary shifts.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Global Topic Selector */}
      <div
        className="glass-card"
        style={{
          padding: '16px 24px',
          marginBottom: '28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
            EVALUATION TOPIC:
          </span>
          <select
            aria-label="Select Evaluation Topic"
            className="select"
            style={{ width: '220px', padding: '6px 12px' }}
            value={selectedTopicId ?? ''}
            onChange={(e) => setSelectedTopicId(Number(e.target.value))}
          >
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.article_count} articles)
              </option>
            ))}
          </select>
        </div>

        <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Sample size: <strong>{headlines.length}</strong> evaluated headlines
        </div>
      </div>

      {/* 1. Pairwise Agreement Matrix Grid */}
      <div className="glass-card" style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ marginBottom: '18px' }}>
          <h2 style={{ fontSize: '18px', marginBottom: '4px' }}>
            Inter-Model Agreement Heatmap (%)
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Percentage of headlines assigned the identical discrete label (Positive / Neutral /
            Negative)
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton height="160px" />
        ) : models.length < 2 ? (
          <EmptyState
            title="Not enough models"
            description="At least two models must be registered for matrix comparison."
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                textAlign: 'center',
                fontSize: '13px',
              }}
            >
              <thead>
                <tr>
                  <th
                    style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}
                  >
                    MODEL
                  </th>
                  {models.map((m) => (
                    <th key={m.name} style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>
                      {m.name.length > 18 ? `${m.name.slice(0, 16)}...` : m.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {models.map((m1) => (
                  <tr key={m1.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td
                      style={{
                        padding: '10px 14px',
                        textAlign: 'left',
                        fontWeight: 600,
                        color: '#ffffff',
                      }}
                    >
                      {m1.name.length > 22 ? `${m1.name.slice(0, 20)}...` : m1.name}
                    </td>
                    {models.map((m2) => {
                      const item = agreementMatrix[m1.name]?.[m2.name];
                      const pct = item ? item.agreementPct : 0;
                      // Heatmap color
                      let bg = 'rgba(255,255,255,0.03)';
                      let textColor = 'var(--text-secondary)';
                      if (m1.name === m2.name) {
                        bg = 'rgba(56, 189, 248, 0.15)';
                        textColor = '#38bdf8';
                      } else if (pct >= 80) {
                        bg = 'rgba(16, 185, 129, 0.2)';
                        textColor = '#34d399';
                      } else if (pct >= 60) {
                        bg = 'rgba(234, 179, 8, 0.15)';
                        textColor = '#facc15';
                      } else if (pct > 0) {
                        bg = 'rgba(244, 63, 94, 0.15)';
                        textColor = '#fb7185';
                      }

                      return (
                        <td
                          key={m2.name}
                          style={{
                            padding: '12px 14px',
                            backgroundColor: bg,
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 700,
                            color: textColor,
                          }}
                        >
                          {pct > 0 ? `${pct.toFixed(1)}%` : '—'}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 2. Disagreement Headlines Explorer */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
            marginBottom: '20px',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '16px',
          }}
        >
          <div>
            <h2 style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} color="var(--sentiment-neg)" />
              Headlines Models Disagree On ({disagreementHeadlines.length})
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Headlines where the selected pair produced contradictory polarity classifications
            </p>
          </div>

          {/* Pair Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>COMPARING:</span>
            <select
              aria-label="Select Model A for comparison"
              className="select"
              style={{ width: '160px', padding: '6px 10px', fontSize: '12px' }}
              value={modelA}
              onChange={(e) => setModelA(e.target.value)}
            >
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name.length > 18 ? `${m.name.slice(0, 16)}...` : m.name}
                </option>
              ))}
            </select>
            <ArrowRight size={14} color="var(--text-muted)" />
            <select
              aria-label="Select Model B for comparison"
              className="select"
              style={{ width: '160px', padding: '6px 10px', fontSize: '12px' }}
              value={modelB}
              onChange={(e) => setModelB(e.target.value)}
            >
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name.length > 18 ? `${m.name.slice(0, 16)}...` : m.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Disagreement List Table */}
        {isLoading ? (
          <LoadingSkeleton height="50px" count={6} />
        ) : disagreementHeadlines.length === 0 ? (
          <EmptyState
            title="Full Consensus"
            description={`No headlines found where ${modelA} and ${modelB} assigned conflicting polarity labels.`}
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                textAlign: 'left',
                fontSize: '13px',
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
                  <th style={{ padding: '12px 14px', width: '45%' }}>HEADLINE</th>
                  <th style={{ padding: '12px 14px' }}>{modelA.toUpperCase()}</th>
                  <th style={{ padding: '12px 14px' }}>{modelB.toUpperCase()}</th>
                  <th style={{ padding: '12px 14px' }}>SCORE DELTA</th>
                  <th style={{ padding: '12px 14px', textAlign: 'right' }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {disagreementHeadlines.map(({ headline, predA, predB, diffScore }) => (
                  <tr
                    key={headline.id}
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
                    <td style={{ padding: '12px 14px' }}>
                      <div
                        onClick={() => onSelectHeadline(headline, modelA)}
                        style={{
                          cursor: 'pointer',
                          color: '#ffffff',
                          fontWeight: 500,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <span>{headline.title}</span>
                        <ExternalLink
                          size={12}
                          color="var(--accent-cyan)"
                          style={{ opacity: 0.7 }}
                        />
                      </div>
                      <div
                        style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}
                      >
                        {headline.outlet} •{' '}
                        {headline.published_at ? headline.published_at.slice(0, 10) : 'Recent'}
                      </div>
                    </td>

                    <td style={{ padding: '12px 14px' }}>
                      <SentimentBadge label={predA.label} score={predA.score} />
                    </td>

                    <td style={{ padding: '12px 14px' }}>
                      <SentimentBadge label={predB.label} score={predB.score} />
                    </td>

                    <td
                      style={{
                        padding: '12px 14px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color: 'var(--accent-cyan)',
                      }}
                    >
                      Δ {diffScore.toFixed(3)}
                    </td>

                    <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '11px' }}
                        onClick={() => onSelectHeadline(headline, modelA)}
                      >
                        Explain Diff
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
