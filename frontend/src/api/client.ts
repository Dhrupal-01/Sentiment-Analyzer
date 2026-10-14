/**
 * Strongly-typed API client communicating with the News Sentiment Analyzer backend.
 */

import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ExplainRequest,
  ExplainResponse,
  HealthResponse,
  JobCollectAndAnalyzeRequest,
  JobCollectAndAnalyzeResponse,
  ModelsRegistryResponse,
  PaginatedHeadlinesResponse,
  TopicCreateRequest,
  TopicResponse,
  TopicsListResponse,
  TopicSummaryResponse,
  TopicTrendResponse,
} from './types';

export class ApiError extends Error {
  code: string;
  statusCode: number;
  details?: unknown;

  constructor(code: string, message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}

export interface HeadlineFilterParams {
  page?: number;
  pageSize?: number;
  startDate?: string;
  endDate?: string;
  source?: string;
  label?: string;
  model?: string;
}

export interface SummaryFilterParams {
  model?: string;
  startDate?: string;
  endDate?: string;
}

export interface TrendFilterParams {
  model?: string;
  startDate?: string;
  endDate?: string;
}

export class NewsSentimentApiClient {
  private baseUrl: string;

  constructor(baseUrl = '') {
    // Empty baseUrl defaults to origin, using Vite dev reverse proxy
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    };

    let response: Response;
    try {
      response = await fetch(url, { ...options, headers });
    } catch (err: unknown) {
      throw new ApiError(
        'NETWORK_ERROR',
        `Network request failed: ${err instanceof Error ? err.message : String(err)}`,
        0
      );
    }

    if (!response.ok) {
      let errorPayload: { error?: { code?: string; message?: string; details?: unknown } } | null =
        null;
      try {
        errorPayload = await response.json();
      } catch {
        // Fall back to status text
      }

      const code = errorPayload?.error?.code || `HTTP_${response.status}`;
      const message =
        errorPayload?.error?.message ||
        `Request to ${path} failed with status ${response.status} (${response.statusText})`;
      const details = errorPayload?.error?.details ?? null;

      throw new ApiError(code, message, response.status, details);
    }

    return (await response.json()) as T;
  }

  /**
   * Health and service liveness check.
   */
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/v1/health');
  }

  /**
   * List all registered sentiment models with metadata and evaluation metrics.
   */
  async listModels(): Promise<ModelsRegistryResponse> {
    return this.request<ModelsRegistryResponse>('/api/v1/models');
  }

  /**
   * List news tracking topics with ingested article counts.
   */
  async listTopics(activeOnly = false): Promise<TopicsListResponse> {
    const query = activeOnly ? '?active_only=true' : '';
    return this.request<TopicsListResponse>(`/api/v1/topics${query}`);
  }

  /**
   * Create or update a news tracking topic.
   */
  async createTopic(payload: TopicCreateRequest): Promise<TopicResponse> {
    return this.request<TopicResponse>('/api/v1/topics', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Retrieve paginated headlines for a topic with optional filters.
   */
  async getTopicHeadlines(
    topicId: number,
    params: HeadlineFilterParams = {}
  ): Promise<PaginatedHeadlinesResponse> {
    const sp = new URLSearchParams();
    if (params.page !== undefined) sp.append('page', String(params.page));
    if (params.pageSize !== undefined) sp.append('page_size', String(params.pageSize));
    if (params.startDate) sp.append('start_date', params.startDate);
    if (params.endDate) sp.append('end_date', params.endDate);
    if (params.source) sp.append('source', params.source);
    if (params.label) sp.append('label', params.label);
    if (params.model) sp.append('model', params.model);

    const query = sp.toString() ? `?${sp.toString()}` : '';
    return this.request<PaginatedHeadlinesResponse>(`/api/v1/topics/${topicId}/headlines${query}`);
  }

  /**
   * Retrieve aggregate sentiment statistics (counts, percentages, average score) for a topic.
   */
  async getTopicSummary(
    topicId: number,
    params: SummaryFilterParams = {}
  ): Promise<TopicSummaryResponse> {
    const sp = new URLSearchParams();
    if (params.model) sp.append('model', params.model);
    if (params.startDate) sp.append('start_date', params.startDate);
    if (params.endDate) sp.append('end_date', params.endDate);

    const query = sp.toString() ? `?${sp.toString()}` : '';
    return this.request<TopicSummaryResponse>(`/api/v1/topics/${topicId}/summary${query}`);
  }

  /**
   * Retrieve daily sentiment trend time series and headline volume for a topic.
   */
  async getTopicTrend(
    topicId: number,
    params: TrendFilterParams = {}
  ): Promise<TopicTrendResponse> {
    const sp = new URLSearchParams();
    if (params.model) sp.append('model', params.model);
    if (params.startDate) sp.append('start_date', params.startDate);
    if (params.endDate) sp.append('end_date', params.endDate);

    const query = sp.toString() ? `?${sp.toString()}` : '';
    return this.request<TopicTrendResponse>(`/api/v1/topics/${topicId}/trend${query}`);
  }

  /**
   * Run real-time sentiment inference across one or more text headlines.
   */
  async analyze(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
    return this.request<AnalyzeResponse>('/api/v1/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Generate token attributions explaining a model's prediction score.
   */
  async explain(payload: ExplainRequest): Promise<ExplainResponse> {
    return this.request<ExplainResponse>('/api/v1/explain', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Trigger scheduled background headline collection and model inference job.
   */
  async triggerCollectAndAnalyzeJob(
    payload: Partial<JobCollectAndAnalyzeRequest> = {},
    apiKey?: string
  ): Promise<JobCollectAndAnalyzeResponse> {
    const headers: Record<string, string> = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    return this.request<JobCollectAndAnalyzeResponse>('/api/v1/jobs/collect-and-analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
  }
}

/**
 * Base URL of the backend. Leave VITE_API_BASE_URL unset when the frontend is served from the same
 * origin as the API (Vite dev proxy or the nginx container). Set it to the backend's public URL when
 * the frontend is hosted separately, for example on Vercel or Netlify.
 */
const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

export const apiClient = new NewsSentimentApiClient(configuredBaseUrl.replace(/\/+$/, ''));
