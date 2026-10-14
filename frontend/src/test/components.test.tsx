import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiClient } from '../api/client';
import { ValenceMarker } from '../components/primitives';
import { TokenMarkup } from '../components/TokenMarkup';
import HeadlinesPage from '../pages/HeadlinesPage';
import TryPage from '../pages/TryPage';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('TokenMarkup', () => {
  it('marks words by the direction they moved the score', () => {
    const { container } = render(
      <TokenMarkup
        text="Not a bad quarter"
        attributions={[
          { token: 'Not', weight: 0.9 },
          { token: 'a', weight: 0 },
          { token: 'bad', weight: -0.3 },
          { token: 'quarter', weight: 0 },
        ]}
      />
    );
    const marked = container.querySelectorAll('.markup__token');
    expect(marked).toHaveLength(2);
    expect(marked[0]).toHaveAttribute('data-sign', 'positive');
    expect(marked[1]).toHaveAttribute('data-sign', 'negative');
    expect(container.textContent).toContain('quarter');
  });
});

describe('ValenceMarker', () => {
  it('describes the score for screen readers', () => {
    render(<ValenceMarker score={-0.45} label="negative" />);
    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      'Score −0.45 on a scale from −1 to +1'
    );
  });
});

describe('TryPage', () => {
  it('shows working models and lists the ones the server cannot run', async () => {
    vi.spyOn(apiClient, 'analyze').mockImplementation(async ({ models }) => {
      const model = models?.[0] ?? 'vader';
      if (model !== 'vader') {
        throw new ApiError('INTERNAL_SERVER_ERROR', 'An unexpected server error occurred.', 500);
      }
      return {
        texts_count: 1,
        models: ['vader'],
        results: [
          {
            text: 'Stocks rally',
            predictions: {
              vader: {
                label: 'positive',
                score: 0.4,
                probabilities: { positive: 0.6, neutral: 0.4, negative: 0 },
                model_version: '3.3.2',
              },
            },
          },
        ],
      };
    });
    vi.spyOn(apiClient, 'explain').mockResolvedValue({
      text: 'Stocks rally',
      model_name: 'vader',
      model_version: '3.3.2',
      method: 'occlusion',
      prediction_label: 'positive',
      prediction_score: 0.4,
      attributions: [
        { token: 'Stocks', weight: 0 },
        { token: 'rally', weight: 0.4 },
      ],
    });

    render(<TryPage registeredModels={['roberta', 'vader']} />);
    await userEvent.type(screen.getByLabelText('Headline'), 'Stocks rally');
    await userEvent.click(screen.getByRole('button', { name: 'Score headline' }));

    expect(await screen.findByText('RoBERTa is not available on this server')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('+0.40')).toBeInTheDocument());
    expect(apiClient.analyze).toHaveBeenCalledWith({ texts: ['Stocks rally'], models: ['vader'] });
    expect(apiClient.analyze).toHaveBeenCalledWith({
      texts: ['Stocks rally'],
      models: ['roberta'],
    });
  });
});

describe('HeadlinesPage', () => {
  it('shows stored labels for list-shaped predictions instead of "unscored"', async () => {
    vi.spyOn(apiClient, 'listTopics').mockResolvedValue({
      total: 1,
      topics: [
        {
          id: 7,
          name: 'markets',
          query: 'stocks',
          is_active: true,
          created_at: '2026-10-01T00:00:00Z',
          article_count: 1,
        },
      ],
    });
    vi.spyOn(apiClient, 'getTopicSummary').mockResolvedValue({
      topic_id: 7,
      topic_name: 'markets',
      model_name: 'vader',
      total_headlines: 1,
      sentiment_distribution: { positive: 0, neutral: 0, negative: 1 },
      sentiment_percentages: { positive: 0, neutral: 0, negative: 100 },
      average_score: -0.6,
      date_range: { start: null, end: null },
    });
    vi.spyOn(apiClient, 'getTopicTrend').mockResolvedValue({
      topic_id: 7,
      topic_name: 'markets',
      model_name: 'vader',
      time_series: [],
    });
    vi.spyOn(apiClient, 'getTopicHeadlines').mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
      items: [
        {
          id: 1,
          title: 'Bank collapses amid fraud probe',
          url: 'https://example.com/1',
          outlet: 'Reuters',
          published_at: '2026-10-02T09:00:00Z',
          topic: 'markets',
          provider: 'gdelt',
          predictions: [
            {
              model_name: 'vader',
              model_version: '3.3.2',
              label: 'negative',
              score: -0.6,
              probabilities: {},
              created_at: '2026-10-02T09:00:00Z',
            },
          ],
        },
      ],
    });

    render(
      <HeadlinesPage
        params={new URLSearchParams()}
        replaceParams={() => undefined}
        registeredModels={['vader']}
      />
    );

    expect(await screen.findByText('Bank collapses amid fraud probe')).toBeInTheDocument();
    const list = within(screen.getByRole('list'));
    expect(list.getByText('\u22120.60')).toBeInTheDocument();
    expect(list.getByText('Negative')).toBeInTheDocument();
  });
});
