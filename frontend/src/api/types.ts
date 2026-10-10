/**
 * Convenient type aliases re-exported from OpenAPI schema.
 */

import type { components } from './schema';

export type Schemas = components['schemas'];

export type AnalyzeRequest = Schemas['AnalyzeRequest'];
export type AnalyzeResponse = Schemas['AnalyzeResponse'];
export type TextAnalysisResult = Schemas['TextAnalysisResult'];
export type ModelPredictionItem = Schemas['ModelPredictionItem'];

export type ExplainRequest = Schemas['ExplainRequest'];
export type ExplainResponse = Schemas['ExplainResponse'];
export type TokenAttributionItem = Schemas['TokenAttributionItem'];

export type TopicResponse = Schemas['TopicResponse'];
export type TopicsListResponse = Schemas['TopicsListResponse'];
export type TopicCreateRequest = Schemas['TopicCreateRequest'];

export type PaginatedHeadlinesResponse = Schemas['PaginatedHeadlinesResponse'];
export type HeadlineItem = Schemas['HeadlineItem'];
export type HeadlinePredictionItem = Schemas['HeadlinePredictionItem'];

export type TopicSummaryResponse = Schemas['TopicSummaryResponse'];
export type SentimentDistribution = Schemas['SentimentDistribution'];
export type SentimentPercentages = Schemas['SentimentPercentages'];

export type TopicTrendResponse = Schemas['TopicTrendResponse'];
export type DailyTrendItem = Schemas['DailyTrendItem'];

export type ModelsRegistryResponse = Schemas['ModelsRegistryResponse'];
export type ModelMetadataItem = Schemas['ModelMetadataItem'];
export type ModelEvaluationMetrics = Schemas['ModelEvaluationMetrics'];
export type ModelExplainabilityMetrics = Schemas['ModelExplainabilityMetrics'];

export type HealthResponse = Schemas['HealthResponse'];
export type ErrorResponse = Schemas['ErrorResponse'];
export type ErrorDetail = Schemas['ErrorDetail'];

export type JobCollectAndAnalyzeRequest = Schemas['JobCollectAndAnalyzeRequest'];
export type JobCollectAndAnalyzeResponse = Schemas['JobCollectAndAnalyzeResponse'];
