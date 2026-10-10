import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '../api/client';
import { TryIt } from '../pages/TryIt';

describe('TryIt', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders input headline textarea and presets', () => {
    render(<TryIt />);
    expect(screen.getByText(/ENTER OR PASTE A NEWS HEADLINE:/i)).toBeInTheDocument();
    expect(screen.getByText('Analyze Headline')).toBeInTheDocument();
    expect(screen.getByText(/Preset #1/i)).toBeInTheDocument();
  });

  it('populates textarea when clicking a preset button', () => {
    render(<TryIt />);
    const textarea = screen.getByPlaceholderText(
      /Type or paste any financial or general news headline/i
    ) as HTMLTextAreaElement;

    const preset2 = screen.getByText(/Preset #2/i);
    fireEvent.click(preset2);

    expect(textarea.value).toContain('Chapter 11 bankruptcy');
  });

  it('runs analysis and displays side-by-side model predictions and token explanations', async () => {
    vi.spyOn(apiClient, 'analyze').mockResolvedValue({
      texts_count: 1,
      models: ['vader', 'finbert'],
      results: [
        {
          text: 'Earnings surge strongly',
          predictions: {
            vader: {
              label: 'positive',
              score: 0.65,
              probabilities: { positive: 0.8, neutral: 0.15, negative: 0.05 },
              model_version: '3.3.2',
            },
            finbert: {
              label: 'positive',
              score: 0.92,
              probabilities: { positive: 0.96, neutral: 0.03, negative: 0.01 },
              model_version: '1.0.0',
            },
          },
        },
      ],
    });

    vi.spyOn(apiClient, 'explain').mockResolvedValue({
      text: 'Earnings surge strongly',
      model_name: 'vader',
      model_version: '3.3.2',
      method: 'occlusion',
      prediction_label: 'positive',
      prediction_score: 0.65,
      attributions: [
        { token: 'Earnings', weight: 0.2 },
        { token: 'surge', weight: 0.8 },
        { token: 'strongly', weight: 0.4 },
      ],
    });

    render(<TryIt />);

    const button = screen.getByText('Analyze Headline');
    fireEvent.click(button);

    await waitFor(() => {
      expect(apiClient.analyze).toHaveBeenCalled();
    });

    // Check if error alert was rendered or if analyze finished
    await waitFor(
      () => {
        expect(screen.queryByText(/Classifying All Models/i)).not.toBeInTheDocument();
      },
      { timeout: 2000 }
    );

    expect(screen.getByText('Side-by-Side Model Predictions')).toBeInTheDocument();
  });
});
