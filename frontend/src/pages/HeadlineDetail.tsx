import React, { useEffect, useState } from 'react';
import { ArrowLeft, ExternalLink, Sparkles, BarChart2 } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { apiClient } from '../api/client';
import type { ExplainResponse, HeadlineItem, ModelMetadataItem } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorAlert } from '../components/ErrorAlert';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { SentimentBadge } from '../components/SentimentBadge';
import { TokenHighlight } from '../components/TokenHighlight';

interface HeadlineDetailProps {
  headline: HeadlineItem | null;
  initialModel?: string;
  onBack: () => void;
}

export const HeadlineDetail: React.FC<HeadlineDetailProps> = ({
  headline,
  initialModel = 'vader',
  onBack,
}) => {
  const [selectedModel, setSelectedModel] = useState<string>(initialModel);
  const [selectedMethod, setSelectedMethod] = useState<
    'occlusion' | 'integrated_gradients' | 'shap'
  >('occlusion');
  const [models, setModels] = useState<ModelMetadataItem[]>([]);

  // Explanation state
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [isLoadingExplanation, setIsLoadingExplanation] = useState<boolean>(false);
  const [explanationError, setExplanationError] = useState<string | null>(null);

  // Fetch model list for tabs
  useEffect(() => {
    let isMounted = true;
    apiClient
      .listModels()
      .then((data) => {
        if (isMounted) setModels(data.models);
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch token attribution explanation whenever headline, model, or method changes
  useEffect(() => {
    if (!headline) return;

    let isMounted = true;
    const fetchExplanation = async () => {
      setIsLoadingExplanation(true);
      setExplanationError(null);
      try {
        const result = await apiClient.explain({
          text: headline.title,
          model: selectedModel,
          method: selectedMethod,
          article_id: headline.id,
        });
        if (isMounted) {
          setExplanation(result);
        }
      } catch (err: any) {
        if (isMounted) {
          setExplanationError(err.message || 'Failed to generate token attribution explanation');
        }
      } finally {
        if (isMounted) setIsLoadingExplanation(false);
      }
    };

    fetchExplanation();
    return () => {
      isMounted = false;
    };
  }, [headline, selectedModel, selectedMethod]);

  if (!headline) {
    return (
      <div style={{ padding: '40px 24px', maxWidth: '1000px', margin: '0 auto' }}>
        <button
          type="button"
          onClick={onBack}
          className="btn btn-secondary"
          style={{ marginBottom: '20px' }}
        >
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <EmptyState
          title="No headline selected"
          description="Select a headline from the Topic Dashboard to inspect multi-model predictions and token attributions."
          actionText="Return to Dashboard"
          onAction={onBack}
        />
      </div>
    );
  }

  // Sorted token weights for chart (top positive and top negative)
  const tokenChartData = explanation
    ? [...explanation.attributions]
        .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
        .slice(0, 10)
        .map((t) => ({
          token: t.token,
          weight: Number(t.weight.toFixed(4)),
        }))
    : [];

  return (
    <div style={{ padding: '32px 24px', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
      {/* Navigation & Header */}
      <div style={{ marginBottom: '24px' }}>
        <button
          type="button"
          onClick={onBack}
          className="btn btn-secondary"
          style={{ marginBottom: '16px', padding: '6px 14px', fontSize: '13px' }}
        >
          <ArrowLeft size={16} /> Back to Headlines
        </button>

        {/* Headline Header Banner */}
        <div className="glass-card" style={{ padding: '24px 28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', color: 'var(--accent-cyan)', fontWeight: 600 }}>
              ARTICLE #{headline.id}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>•</span>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {headline.outlet}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>•</span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {headline.published_at
                ? headline.published_at.slice(0, 16).replace('T', ' ')
                : 'Recent'}
            </span>
          </div>

          <h1
            style={{ fontSize: '24px', lineHeight: '1.4', marginBottom: '16px', color: '#ffffff' }}
          >
            {headline.title}
          </h1>

          {headline.url && (
            <a
              href={headline.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                color: 'var(--accent-cyan)',
              }}
            >
              <span>View Original News Source</span>
              <ExternalLink size={13} />
            </a>
          )}
        </div>
      </div>

      {/* Model Predictions Grid: Compare all models side-by-side */}
      <div style={{ marginBottom: '32px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '16px',
          }}
        >
          <h2 style={{ fontSize: '18px' }}>Model Sentiment Predictions</h2>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Click a card to switch explanation focus
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px',
          }}
        >
          {models.map((m) => {
            const pred = headline.predictions[m.name];
            const isSelected = selectedModel === m.name;

            return (
              <div
                key={m.name}
                className="glass-card"
                onClick={() => setSelectedModel(m.name)}
                style={{
                  padding: '20px',
                  cursor: 'pointer',
                  borderColor: isSelected ? 'var(--accent-cyan)' : 'var(--border-card)',
                  boxShadow: isSelected ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
                  position: 'relative',
                }}
              >
                {isSelected && (
                  <span
                    style={{
                      position: 'absolute',
                      top: '12px',
                      right: '12px',
                      fontSize: '10px',
                      textTransform: 'uppercase',
                      color: 'var(--accent-cyan)',
                      fontWeight: 700,
                      backgroundColor: 'var(--accent-cyan-glow)',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    Active Focus
                  </span>
                )}

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '12px',
                  }}
                >
                  <span style={{ fontWeight: 700, fontSize: '15px', color: '#ffffff' }}>
                    {m.name}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>v{m.version}</span>
                </div>

                {pred ? (
                  <div>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '12px',
                      }}
                    >
                      <SentimentBadge label={pred.label} score={pred.score} />
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '15px',
                          fontWeight: 700,
                          color:
                            pred.score > 0
                              ? 'var(--sentiment-pos)'
                              : pred.score < 0
                                ? 'var(--sentiment-neg)'
                                : 'var(--sentiment-neu)',
                        }}
                      >
                        {pred.score > 0 ? `+${pred.score.toFixed(3)}` : pred.score.toFixed(3)}
                      </span>
                    </div>

                    {/* Class Probability Distribution Bars */}
                    {pred.probabilities && (
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                          fontSize: '11px',
                        }}
                      >
                        <div>
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              marginBottom: '2px',
                              color: 'var(--text-muted)',
                            }}
                          >
                            <span>Pos: {(pred.probabilities.positive * 100).toFixed(1)}%</span>
                            <span>Neu: {(pred.probabilities.neutral * 100).toFixed(1)}%</span>
                            <span>Neg: {(pred.probabilities.negative * 100).toFixed(1)}%</span>
                          </div>
                          {/* Segmented bar */}
                          <div
                            style={{
                              height: '6px',
                              width: '100%',
                              backgroundColor: 'rgba(255,255,255,0.06)',
                              borderRadius: '3px',
                              display: 'flex',
                              overflow: 'hidden',
                            }}
                          >
                            <div
                              style={{
                                width: `${pred.probabilities.positive * 100}%`,
                                backgroundColor: 'var(--sentiment-pos)',
                              }}
                            />
                            <div
                              style={{
                                width: `${pred.probabilities.neutral * 100}%`,
                                backgroundColor: 'var(--sentiment-neu)',
                              }}
                            />
                            <div
                              style={{
                                width: `${pred.probabilities.negative * 100}%`,
                                backgroundColor: 'var(--sentiment-neg)',
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div
                    style={{
                      color: 'var(--text-muted)',
                      fontSize: '13px',
                      fontStyle: 'italic',
                      padding: '12px 0',
                    }}
                  >
                    No prediction stored for this model.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature Attribution Explanation Card */}
      <div className="glass-card" style={{ padding: '28px', marginBottom: '32px' }}>
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
            <h2 style={{ fontSize: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={20} color="var(--accent-cyan)" />
              Token Attribution Explanation
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Explains what specific words drove <strong>{selectedModel}</strong> to predict this
              score.
            </p>
          </div>

          {/* Attribution Method Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>
              Method:
            </span>
            <div
              style={{
                display: 'flex',
                gap: '4px',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                padding: '3px',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <button
                type="button"
                className={`btn ${selectedMethod === 'occlusion' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ padding: '5px 12px', fontSize: '12px' }}
                onClick={() => setSelectedMethod('occlusion')}
              >
                Occlusion
              </button>
              <button
                type="button"
                className={`btn ${selectedMethod === 'integrated_gradients' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ padding: '5px 12px', fontSize: '12px' }}
                onClick={() => setSelectedMethod('integrated_gradients')}
              >
                Integrated Gradients
              </button>
              <button
                type="button"
                className={`btn ${selectedMethod === 'shap' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ padding: '5px 12px', fontSize: '12px' }}
                onClick={() => setSelectedMethod('shap')}
              >
                SHAP
              </button>
            </div>
          </div>
        </div>

        {explanationError && <ErrorAlert message={explanationError} />}

        {isLoadingExplanation ? (
          <LoadingSkeleton height="140px" />
        ) : explanation ? (
          <div>
            <TokenHighlight
              tokens={explanation.attributions}
              modelName={explanation.model_name}
              method={explanation.method}
              score={explanation.prediction_score}
            />

            {/* Token Importance Bar Chart */}
            {tokenChartData.length > 0 && (
              <div
                style={{
                  marginTop: '28px',
                  paddingTop: '20px',
                  borderTop: '1px solid var(--border-subtle)',
                }}
              >
                <h3
                  style={{
                    fontSize: '15px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '14px',
                    color: 'var(--text-secondary)',
                  }}
                >
                  <BarChart2 size={16} /> Top Token Influence Weights
                </h3>
                <div style={{ width: '100%', height: '220px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={tokenChartData}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis
                        type="number"
                        stroke="var(--text-muted)"
                        fontSize={11}
                        domain={['auto', 'auto']}
                      />
                      <YAxis
                        dataKey="token"
                        type="category"
                        stroke="#cbd5e1"
                        fontSize={12}
                        width={70}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(15, 23, 42, 0.95)',
                          borderColor: 'var(--border-card)',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                      <Bar dataKey="weight" name="Attribution Weight" radius={[0, 4, 4, 0]}>
                        {tokenChartData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={
                              entry.weight >= 0 ? 'var(--sentiment-pos)' : 'var(--sentiment-neg)'
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};
