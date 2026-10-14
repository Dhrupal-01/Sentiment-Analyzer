import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NewsSentimentApiClient, ApiError } from '../api/client';

describe('NewsSentimentApiClient', () => {
  let client: NewsSentimentApiClient;

  beforeEach(() => {
    client = new NewsSentimentApiClient('http://localhost:8000');
    vi.restoreAllMocks();
  });

  it('successfully retrieves health status', async () => {
    const mockHealth = {
      status: 'healthy',
      app: 'News Sentiment Analyzer',
      version: '0.1.0',
      environment: 'testing',
      database: 'connected',
      models_loaded: ['vader', 'roberta'],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    } as Response);

    const res = await client.getHealth();
    expect(res.status).toBe('healthy');
    expect(res.database).toBe('connected');
    expect(res.models_loaded).toContain('vader');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/health',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );
  });

  it('parses standardized API error envelope on 404 or 400 response', async () => {
    const errorPayload = {
      error: {
        code: 'NOT_FOUND',
        message: 'Topic 999 does not exist',
        details: null,
      },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => errorPayload,
    } as Response);

    await expect(client.getTopicSummary(999)).rejects.toThrow('Topic 999 does not exist');

    try {
      await client.getTopicSummary(999);
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.code).toBe('NOT_FOUND');
      expect(err.statusCode).toBe(404);
    }
  });

  it('wraps fetch network exceptions into NETWORK_ERROR ApiError', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    await expect(client.getHealth()).rejects.toThrow('Network request failed');

    try {
      await client.getHealth();
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.code).toBe('NETWORK_ERROR');
      expect(err.statusCode).toBe(0);
    }
  });

  it('sends analyze request payload properly formatted', async () => {
    const mockAnalyzeResp = {
      texts_count: 1,
      models: ['vader'],
      results: [
        {
          text: 'Tech rally continues',
          predictions: {
            vader: {
              label: 'positive',
              score: 0.65,
              probabilities: { positive: 0.8, neutral: 0.15, negative: 0.05 },
              model_version: '3.3.2',
            },
          },
        },
      ],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockAnalyzeResp,
    } as Response);

    const res = await client.analyze({ texts: ['Tech rally continues'], models: ['vader'] });
    expect(res.texts_count).toBe(1);
    expect(res.results[0]?.predictions.vader?.label).toBe('positive');
  });

  it('triggers collect and analyze background job with api key header', async () => {
    const mockJobResp = {
      status: 'completed',
      topics_processed: 2,
      articles_fetched: 20,
      articles_inserted: 18,
      duplicates_found: 2,
      articles_scored: { vader: 18 },
      elapsed_seconds: 1.42,
    };

    let capturedHeaders: Record<string, string> = {};
    globalThis.fetch = vi.fn().mockImplementation((_url, init) => {
      capturedHeaders = init?.headers || {};
      return Promise.resolve({
        ok: true,
        json: async () => mockJobResp,
      } as Response);
    });

    const res = await client.triggerCollectAndAnalyzeJob(
      { source: 'gdelt', limit_per_topic: 10, models: ['vader'] },
      'test-cron-key-123'
    );
    expect(res.status).toBe('completed');
    expect(res.articles_inserted).toBe(18);
    expect(capturedHeaders['X-API-Key']).toBe('test-cron-key-123');
  });
});
