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
  competitor_feeds: AnalystFeed[];
  news_feeds: AnalystFeed[];
  presets: Record<string, unknown>;
}

export interface OutputType {
  id: string;
  icon: string;
  name: string;
  desc: string;
}

export interface SocialPlatform {
  id: string;
  name: string;
}

export interface InputMode {
  id: string;
  icon: string;
  name: string;
  desc: string;
}

export interface PovOption {
  id: string;
  name: string;
  desc: string;
}

export interface Persona {
  id: string;
  name: string;
  archetype: string;
  description: string;
  painPoints: string[];
  tone: string;
  formatPref: string;
  platform: string;
  ctaType: string;
  custom: boolean;
}

export interface AppSettings {
  lenses: Lens[];
  frameworks: Framework[];
  output_types: OutputType[];
  social_platforms: SocialPlatform[];
  input_modes: InputMode[];
  personas: Persona[];
  pov_options: PovOption[];
}

export interface ConferenceEntry {
  name: string;
  start: [number, number];
  end: [number, number];
  topics: string[];
}

export interface ThoughtLeaderTier {
  weight: number;
  names: string[];
  handles?: string[];
  domains?: string[];
}

export interface EngineConfig {
  scoring_weights: Record<string, number>;
  routing_thresholds: Record<string, number>;
  queue_threshold: number;
  domain_terms: string[];
  thought_leaders: { tier0: ThoughtLeaderTier; tier1: ThoughtLeaderTier };
  competitors: string[];
  source_initial_trust: Record<string, number>;
  conference_calendar: ConferenceEntry[];
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
