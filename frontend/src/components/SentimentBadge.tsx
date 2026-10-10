import React from 'react';

interface SentimentBadgeProps {
  label: string;
  score?: number;
  showScore?: boolean;
}

export const SentimentBadge: React.FC<SentimentBadgeProps> = ({
  label,
  score,
  showScore = true,
}) => {
  const normalized = label.toLowerCase();
  let badgeClass = 'badge-neutral';
  const indicator = '●';

  if (normalized === 'positive') {
    badgeClass = 'badge-positive';
  } else if (normalized === 'negative') {
    badgeClass = 'badge-negative';
  }

  const formattedScore =
    score !== undefined ? (score > 0 ? `+${score.toFixed(2)}` : score.toFixed(2)) : null;

  return (
    <span
      className={`badge ${badgeClass}`}
      title={score !== undefined ? `Score: ${score}` : undefined}
    >
      <span style={{ fontSize: '9px' }}>{indicator}</span>
      <span>{label}</span>
      {showScore && formattedScore !== null && (
        <span
          style={{
            opacity: 0.85,
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            marginLeft: '2px',
          }}
        >
          ({formattedScore})
        </span>
      )}
    </span>
  );
};
