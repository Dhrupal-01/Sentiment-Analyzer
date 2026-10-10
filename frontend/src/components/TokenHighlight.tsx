import React, { useState } from 'react';
import type { TokenAttributionItem } from '../api/types';

interface TokenHighlightProps {
  tokens: TokenAttributionItem[];
  modelName?: string;
  method?: string;
  score?: number;
}

export const TokenHighlight: React.FC<TokenHighlightProps> = ({
  tokens,
  modelName,
  method,
  score,
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!tokens || tokens.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
        No token attributions available.
      </div>
    );
  }

  // Find max absolute weight for relative color scaling
  const maxAbsWeight = Math.max(...tokens.map((t) => Math.abs(t.weight)), 0.0001);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Explanation Banner Metadata */}
      {(modelName || method || score !== undefined) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '10px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '8px',
          }}
        >
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {modelName && <span className="badge badge-model">{modelName}</span>}
            {method && (
              <span
                style={{
                  textTransform: 'uppercase',
                  fontWeight: 600,
                  color: 'var(--accent-cyan)',
                  fontSize: '11px',
                  letterSpacing: '0.04em',
                }}
              >
                Method: {method.replace('_', ' ')}
              </span>
            )}
          </div>
          {score !== undefined && (
            <div>
              Predicted Score:{' '}
              <strong
                style={{
                  color:
                    score > 0
                      ? 'var(--sentiment-pos)'
                      : score < 0
                        ? 'var(--sentiment-neg)'
                        : 'var(--sentiment-neu)',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {score > 0 ? `+${score.toFixed(4)}` : score.toFixed(4)}
              </strong>
            </div>
          )}
        </div>
      )}

      {/* Interactive Token Highlight Paragraph */}
      <div
        style={{
          lineHeight: '2.4',
          fontSize: '17px',
          fontFamily: 'var(--font-body)',
          padding: '16px 20px',
          backgroundColor: 'rgba(15, 23, 42, 0.85)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-card)',
          minHeight: '80px',
        }}
      >
        {tokens.map((t, idx) => {
          const weight = t.weight;
          const ratio = Math.min(Math.abs(weight) / maxAbsWeight, 1);
          // Scale opacity between 0.15 and 0.85 based on importance
          const alpha = 0.15 + ratio * 0.7;

          let bg = 'transparent';
          let border = '1px solid transparent';
          let textColor = 'var(--text-primary)';

          if (weight > 0.001) {
            bg = `rgba(16, 185, 129, ${alpha.toFixed(2)})`;
            border = `1px solid rgba(52, 211, 153, ${Math.min(alpha + 0.2, 0.9).toFixed(2)})`;
            textColor = '#ecfdf5';
          } else if (weight < -0.001) {
            bg = `rgba(244, 63, 94, ${alpha.toFixed(2)})`;
            border = `1px solid rgba(251, 113, 133, ${Math.min(alpha + 0.2, 0.9).toFixed(2)})`;
            textColor = '#fff1f2';
          }

          const isHovered = hoveredIndex === idx;

          return (
            <span
              key={`${idx}-${t.token}`}
              onMouseEnter={() => setHoveredIndex(idx)}
              onMouseLeave={() => setHoveredIndex(null)}
              style={{
                display: 'inline-block',
                position: 'relative',
                padding: '2px 6px',
                margin: '2px 2px',
                borderRadius: '5px',
                backgroundColor: bg,
                border,
                color: textColor,
                fontWeight: ratio > 0.5 ? 600 : 400,
                cursor: 'pointer',
                transition: 'transform 120ms ease, box-shadow 120ms ease',
                transform: isHovered ? 'scale(1.1) translateY(-2px)' : 'scale(1)',
                zIndex: isHovered ? 10 : 1,
                boxShadow: isHovered ? '0 4px 12px rgba(0,0,0,0.45)' : 'none',
              }}
            >
              {t.token}
              {/* Tooltip on Hover */}
              {isHovered && (
                <span
                  style={{
                    position: 'absolute',
                    bottom: '100%',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    marginBottom: '6px',
                    padding: '4px 8px',
                    backgroundColor: '#0f172a',
                    color: '#f8fafc',
                    border: '1px solid var(--border-card)',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    whiteSpace: 'nowrap',
                    boxShadow: 'var(--shadow-md)',
                    pointerEvents: 'none',
                    zIndex: 20,
                  }}
                >
                  {weight > 0 ? `+${weight.toFixed(4)}` : weight.toFixed(4)} (
                  {weight > 0 ? 'pushes positive' : weight < 0 ? 'pulls negative' : 'neutral'})
                </span>
              )}
            </span>
          );
        })}
      </div>

      {/* Attribution Gradient Legend */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '11px',
          color: 'var(--text-muted)',
          padding: '0 4px',
        }}
      >
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--sentiment-neg)',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '2px',
              backgroundColor: 'var(--sentiment-neg)',
            }}
          />
          Pulls Negative (-1.0)
        </span>
        <span style={{ color: 'var(--text-muted)' }}>Neutral (0.0)</span>
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--sentiment-pos)',
          }}
        >
          Pushes Positive (+1.0)
          <span
            style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '2px',
              backgroundColor: 'var(--sentiment-pos)',
            }}
          />
        </span>
      </div>
    </div>
  );
};
