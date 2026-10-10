import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { SentimentBadge } from '../components/SentimentBadge';

describe('SentimentBadge', () => {
  it('renders positive label with positive styling and score', () => {
    const { container } = render(<SentimentBadge label="positive" score={0.75} />);
    expect(screen.getByText('positive')).toBeInTheDocument();
    expect(screen.getByText('(+0.75)')).toBeInTheDocument();
    expect(container.querySelector('.badge-positive')).toBeInTheDocument();
  });

  it('renders negative label with negative styling', () => {
    const { container } = render(<SentimentBadge label="negative" score={-0.42} />);
    expect(screen.getByText('negative')).toBeInTheDocument();
    expect(screen.getByText('(-0.42)')).toBeInTheDocument();
    expect(container.querySelector('.badge-negative')).toBeInTheDocument();
  });

  it('renders neutral label when score is neutral', () => {
    const { container } = render(<SentimentBadge label="neutral" score={0.0} />);
    expect(screen.getByText('neutral')).toBeInTheDocument();
    expect(container.querySelector('.badge-neutral')).toBeInTheDocument();
  });
});
