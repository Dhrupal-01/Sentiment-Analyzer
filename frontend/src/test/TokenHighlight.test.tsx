import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TokenHighlight } from '../components/TokenHighlight';

describe('TokenHighlight', () => {
  const sampleTokens = [
    { token: 'Stocks', weight: 0.12 },
    { token: 'surge', weight: 0.85 },
    { token: 'on', weight: 0.01 },
    { token: 'earnings', weight: 0.45 },
    { token: 'drop', weight: -0.72 },
  ];

  it('renders all tokens in sequence', () => {
    render(
      <TokenHighlight tokens={sampleTokens} modelName="vader" method="occlusion" score={0.71} />
    );

    expect(screen.getByText('Stocks')).toBeInTheDocument();
    expect(screen.getByText('surge')).toBeInTheDocument();
    expect(screen.getByText('earnings')).toBeInTheDocument();
    expect(screen.getByText('drop')).toBeInTheDocument();
    expect(screen.getByText('vader')).toBeInTheDocument();
    expect(screen.getByText(/Method: OCCLUSION/i)).toBeInTheDocument();
  });

  it('renders empty fallback when token list is empty', () => {
    render(<TokenHighlight tokens={[]} />);
    expect(screen.getByText(/No token attributions available/i)).toBeInTheDocument();
  });

  it('displays the predicted continuous score banner', () => {
    render(
      <TokenHighlight
        tokens={sampleTokens}
        modelName="finbert"
        method="integrated_gradients"
        score={-0.3412}
      />
    );

    expect(screen.getByText('-0.3412')).toBeInTheDocument();
  });
});
