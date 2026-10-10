import React, { useState } from 'react';
import { Zap, Play, RotateCcw, Sparkles } from 'lucide-react';
import { apiClient } from '../api/client';
import type { AnalyzeResponse, ExplainResponse } from '../api/types';
import { ErrorAlert } from '../components/ErrorAlert';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { SentimentBadge } from '../components/SentimentBadge';
import { TokenHighlight } from '../components/TokenHighlight';

const PRESET_HEADLINES = [
  'Wall Street rallies sharply as chipmaker reports blowout quarterly earnings and raises full-year guidance',
  'Retailer files for Chapter 11 bankruptcy following catastrophic supply chain shutdown',
  'Federal Reserve holds interest rates steady as policymakers assess stubborn core inflation trends',
  'Quarterly dividend returns were not good despite aggressive corporate restructuring',
  'Global leaders gather in Geneva for bilateral negotiations on cross-border emissions standards',
];

export const TryIt: React.FC = () => {
  const [inputText, setInputText] = useState<string>(PRESET_HEADLINES[0]);
  const [selectedMethod, setSelectedMethod] = useState<
    'occlusion' | 'integrated_gradients' | 'shap'
  >('occlusion');
  const [activeExplainModel, setActiveExplainModel] = useState<string>('vader');

  // Analysis & Explanation state
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isExplaining, setIsExplaining] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunAnalysis = async () => {
    if (!inputText.trim()) return;

    setIsAnalyzing(true);
    setError(null);
    setAnalysis(null);
    setExplanation(null);

    try {
      // 1. Analyze with all models
      const analyzeResult = await apiClient.analyze({
        texts: [inputText.trim()],
      });
      setAnalysis(analyzeResult);

      // Default active model for explanation
      const firstModel = analyzeResult.models[0] || 'vader';
      setActiveExplainModel(firstModel);

      // 2. Fetch initial explanation
      setIsExplaining(true);
      const explainResult = await apiClient.explain({
        text: inputText.trim(),
        model: firstModel,
        method: selectedMethod,
      });
      setExplanation(explainResult);
    } catch (err: any) {
      setError(err.message || 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
      setIsExplaining(false);
    }
  };

  const handleSwitchExplainModelOrMethod = async (
    modelName: string,
    method: 'occlusion' | 'integrated_gradients' | 'shap'
  ) => {
    setActiveExplainModel(modelName);
    setSelectedMethod(method);
    if (!inputText.trim()) return;

    setIsExplaining(true);
    try {
      const explainResult = await apiClient.explain({
        text: inputText.trim(),
        model: modelName,
        method,
      });
      setExplanation(explainResult);
    } catch (err: any) {
      setError(err.message || 'Failed to generate token attribution');
    } finally {
      setIsExplaining(false);
    }
  };

  const currentResult = analysis?.results[0];

  return (
    <div style={{ padding: '32px 24px', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
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
          <Zap size={28} color="var(--accent-cyan)" />
          Try It Live: Multi-Model Inference & Token Attribution
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Test any custom news headline in real-time. Compare off-the-shelf and fine-tuned models
          side-by-side, and inspect which specific words drive each model&apos;s score.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Input Box & Presets */}
      <div className="glass-card" style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ marginBottom: '14px' }}>
          <label
            style={{
              display: 'block',
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '8px',
            }}
          >
            ENTER OR PASTE A NEWS HEADLINE:
          </label>
          <textarea
            className="textarea"
            rows={3}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type or paste any financial or general news headline..."
            maxLength={1000}
            style={{ fontSize: '16px', lineHeight: '1.5' }}
          />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: '6px',
              fontSize: '12px',
              color: 'var(--text-muted)',
            }}
          >
            <span>Max 1,000 characters</span>
            <span>{inputText.length} / 1000</span>
          </div>
        </div>

        {/* Preset Selector */}
        <div style={{ marginBottom: '20px' }}>
          <span
            style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              display: 'block',
              marginBottom: '8px',
            }}
          >
            OR SELECT A TEST BENCHMARK PRESET:
          </span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {PRESET_HEADLINES.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                className="btn btn-secondary"
                style={{
                  fontSize: '11px',
                  padding: '5px 10px',
                  maxWidth: '340px',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                }}
                onClick={() => setInputText(preset)}
              >
                Preset #{idx + 1}: {preset.slice(0, 36)}...
              </button>
            ))}
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setInputText('');
              setAnalysis(null);
              setExplanation(null);
            }}
          >
            <RotateCcw size={14} /> Clear
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!inputText.trim() || isAnalyzing}
            onClick={handleRunAnalysis}
            style={{ padding: '10px 24px', fontSize: '15px' }}
          >
            <Play size={16} />
            {isAnalyzing ? 'Classifying All Models...' : 'Analyze Headline'}
          </button>
        </div>
      </div>

      {/* Results Section */}
      {isAnalyzing && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
          }}
        >
          <LoadingSkeleton height="180px" count={3} />
        </div>
      )}

      {currentResult && (
        <div>
          {/* Side-by-Side Model Predictions Grid */}
          <div style={{ marginBottom: '32px' }}>
            <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>
              Side-by-Side Model Predictions
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '16px',
              }}
            >
              {Object.entries(currentResult.predictions).map(([modelName, p]) => {
                const isSelected = activeExplainModel === modelName;
                return (
                  <div
                    key={modelName}
                    className="glass-card"
                    onClick={() => handleSwitchExplainModelOrMethod(modelName, selectedMethod)}
                    style={{
                      padding: '20px',
                      cursor: 'pointer',
                      borderColor: isSelected ? 'var(--accent-cyan)' : 'var(--border-card)',
                      boxShadow: isSelected ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
                      position: 'relative',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '12px',
                      }}
                    >
                      <span style={{ fontWeight: 700, fontSize: '15px', color: '#ffffff' }}>
                        {modelName}
                      </span>
                      <SentimentBadge label={p.label} score={p.score} />
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'baseline',
                        gap: '8px',
                        marginBottom: '14px',
                      }}
                    >
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Continuous Score:
                      </span>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '18px',
                          fontWeight: 700,
                          color:
                            p.score > 0
                              ? 'var(--sentiment-pos)'
                              : p.score < 0
                                ? 'var(--sentiment-neg)'
                                : 'var(--sentiment-neu)',
                        }}
                      >
                        {p.score > 0 ? `+${p.score.toFixed(4)}` : p.score.toFixed(4)}
                      </span>
                    </div>

                    {/* Class probabilities */}
                    <div
                      style={{
                        fontSize: '11px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          color: 'var(--text-muted)',
                        }}
                      >
                        <span>Pos: {(p.probabilities.positive * 100).toFixed(1)}%</span>
                        <span>Neu: {(p.probabilities.neutral * 100).toFixed(1)}%</span>
                        <span>Neg: {(p.probabilities.negative * 100).toFixed(1)}%</span>
                      </div>
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
                            width: `${p.probabilities.positive * 100}%`,
                            backgroundColor: 'var(--sentiment-pos)',
                          }}
                        />
                        <div
                          style={{
                            width: `${p.probabilities.neutral * 100}%`,
                            backgroundColor: 'var(--sentiment-neu)',
                          }}
                        />
                        <div
                          style={{
                            width: `${p.probabilities.negative * 100}%`,
                            backgroundColor: 'var(--sentiment-neg)',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Explanation Section */}
          <div className="glass-card" style={{ padding: '28px' }}>
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
                  Token Attribution Breakdown
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  Viewing explanation for <strong>{activeExplainModel}</strong> using{' '}
                  <strong>{selectedMethod}</strong>.
                </p>
              </div>

              {/* Method Switcher */}
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
                    onClick={() =>
                      handleSwitchExplainModelOrMethod(activeExplainModel, 'occlusion')
                    }
                  >
                    Occlusion
                  </button>
                  <button
                    type="button"
                    className={`btn ${selectedMethod === 'integrated_gradients' ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ padding: '5px 12px', fontSize: '12px' }}
                    onClick={() =>
                      handleSwitchExplainModelOrMethod(activeExplainModel, 'integrated_gradients')
                    }
                  >
                    Integrated Gradients
                  </button>
                  <button
                    type="button"
                    className={`btn ${selectedMethod === 'shap' ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ padding: '5px 12px', fontSize: '12px' }}
                    onClick={() => handleSwitchExplainModelOrMethod(activeExplainModel, 'shap')}
                  >
                    SHAP
                  </button>
                </div>
              </div>
            </div>

            {isExplaining ? (
              <LoadingSkeleton height="120px" />
            ) : explanation ? (
              <TokenHighlight
                tokens={explanation.attributions}
                modelName={explanation.model_name}
                method={explanation.method}
                score={explanation.prediction_score}
              />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
