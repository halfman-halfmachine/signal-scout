export interface QueueView {
  id: string;
  title: string;
  url: string;
  author: string;
  source: string;
  domain: string;
  platform: string;
  score: number;
  tier: string;
  topics: string[];
  text: string;
  talking_points: string;
  layers: Record<string, number | boolean>;
  kept: boolean;
  dismissed: boolean;
  origin: string;
  scores: Record<string, number>;
  timestamp: number;
}

export interface Lens {
  id: string;
  name: string;
  weight: number;
  active: boolean;
  keywords: string[];
}

export interface Framework {
  id: string;
  name: string;
  beats: string[];
  best: string;
}

export interface AnalystFeed {
  name: string;
  domain: string;
  url: string;
}

export interface IngestionConfig {
  hn_queries: string[];
  reddit_subs: string;
  arxiv_feeds: string[];
  analyst_feeds: AnalystFeed[];
  competitor_feeds: string[];
  news_feeds: string[];
  presets: Record<string, unknown>;
}

export interface AppSettings {
  lenses: Lens[];
  frameworks: Framework[];
  output_types: string[];
  social_platforms: string[];
  input_modes: string[];
  personas: string[];
  pov_options: string[];
}

export interface EngineConfig {
  scoring_weights: Record<string, number>;
  routing_thresholds: Record<string, number>;
  queue_threshold: number;
  domain_terms: string[];
  thought_leaders: string[];
  competitors: string[];
  source_initial_trust: Record<string, number>;
  conference_calendar: string[];
}

export interface GenerateOutput {
  id: string;
  output_type: string;
  output_type_name: string;
  framework: string;
  content: string;
  is_live: boolean;
  variant: number;
}

export interface IngestMeta {
  count: number;
  sources: Record<string, number>;
  errors: string[];
  mode: string;
  topic: string;
}

export interface ScorePreview {
  score: number;
  tier: string;
  formula: string;
}

export interface AuthStatus {
  auth_required: boolean;
  authenticated: boolean;
}

export interface HealthStatus {
  status: string;
  name: string;
  version: string;
  auth_required: boolean;
  llm: 'live' | 'template';
}

export interface Topic {
  key: string;
  label: string;
}
